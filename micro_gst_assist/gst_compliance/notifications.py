# -*- coding: utf-8 -*-
"""
Scheduled notifications: filing deadline reminders, GSTR-2B mismatch alerts.
Runs daily via hooks.py scheduler_events. 
WhatsApp/SMS is the critical channel for this user segment per design.
"""

import frappe
from frappe import _
from frappe.utils import nowdate, getdate, today, add_days, date_diff

from micro_gst_assist.utils import notify_user


# ─────────────────────────────────────────────────────────────────
# DAILY REMINDER NOTIFICATIONS
# ─────────────────────────────────────────────────────────────────

def send_filing_reminders():
    """
    Called daily from hooks.py scheduler_events.
    Sends reminders about approaching filing deadlines.
    """
    today_dt = getdate(today())

    _send_reminder_window(today_dt, 0, 3, "CRITICAL")
    _send_reminder_window(today_dt, 4, 7, "WARNING")
    _send_reminder_window(today_dt, 8, 14, "REMINDER")


def _send_reminder_window(today_dt, min_days, max_days, urgency):
    start = add_days(today_dt, min_days)
    end = add_days(today_dt, max_days)

    checklists = frappe.get_all(
        "GST Filing Checklist",
        filters={"status": ["in", ["Draft", "In Progress"]], "due_date": ["between", [start, end]]},
        fields=["name", "filing_period", "due_date", "company", "owner", "total_items", "completed_items"],
    )

    for cl in checklists:
        pending = (cl.total_items or 0) - (cl.completed_items or 0)
        if pending <= 0:
            continue

        days_left = date_diff(getdate(cl.due_date), today_dt)
        subject = _("GST Filing %s — %s (%d days left)") % (cl.filing_period, cl.name, days_left)
        message = _(
            "GST FILING DEADLINE %s\n\n"
            "Period: %s\nDue: %s\nDays Left: %d\n"
            "Completed: %d/%d tasks\nPending: %d\n\n"
            "Please complete pending tasks to avoid late fees.\n"
            "Login: %s"
        ) % (
            "TOMORROW!" if days_left <= 1 else "APPROACHING",
            cl.filing_period, cl.due_date, days_left,
            cl.completed_items or 0, cl.total_items or 0, pending,
            frappe.utils.get_url("/app/gst-filing-assistant"),
        )

        # System notification
        notify_user(cl.owner, subject, message, "GST Filing Checklist", cl.name)

        # WhatsApp/SMS for urgent reminders (critical channel for this segment)
        if urgency in ("CRITICAL", "WARNING"):
            _send_whatsapp_sms(cl.owner, subject, message)

        # Log to reminder log
        _log_reminder(cl.name, "Deadline Approaching", cl.owner, urgency, "System Notification", message)


def _send_whatsapp_sms(user, subject, message):
    """Send via SMS gateway. Uses ERPNext SMS settings if configured."""
    try:
        phone_data = frappe.db.get_value("User", user, ["mobile_no", "phone"], as_dict=True)
        phone = (phone_data.get("mobile_no") or phone_data.get("phone")) if phone_data else None
        if not phone:
            return

        from frappe.core.doctype.sms_settings.sms_settings import send_sms
        send_sms([phone], message[:300])
        _log_reminder(None, "Deadline Approaching", user, "CRITICAL", "WhatsApp/SMS", message[:300])

    except ImportError:
        frappe.log_error("GST Assist: SMS settings not configured", "micro_gst_assist")
    except Exception as e:
        frappe.log_error(f"GST Assist: SMS failed: {e}", "micro_gst_assist")


def _log_reminder(checklist, reminder_type, recipient, urgency, channel, message):
    """Log a reminder event to the audit trail."""
    try:
        doc = {"doctype": "GST Filing Reminder Log",
               "reminder_type": reminder_type, "recipient": recipient,
               "channel": channel, "status": "Sent", "urgency": urgency,
               "message": message[:500], "sent_at": nowdate()}
        if checklist:
            doc["checklist"] = checklist
        frappe.get_doc(doc).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "GST Assist: log reminder failed")


# ─────────────────────────────────────────────────────────────────
# GSTR-2B MISMATCH NOTIFICATIONS
# ─────────────────────────────────────────────────────────────────

def send_mismatch_alerts():
    """
    Called hourly (or as needed) to notify about new GSTR-2B mismatches.
    """
    mismatches = frappe.get_all(
        "GST Invoice Audit Log",
        filters={"gst_status": "Mismatch", "resolved": 0},
        fields=["name", "sales_invoice", "errors", "company"],
    )
    if not mismatches:
        return

    # Notify all Shop Owner (GST) users
    users = frappe.get_all("Has Role", filters={"role": "Shop Owner (GST)", "parenttype": "User"}, pluck="parent")
    for user in set(users):
        subject = _("GSTR-2B Mismatch Alert — %d unmatched invoice(s)") % len(mismatches)
        url = frappe.utils.get_url("/app/gstr-2b-mismatch-summary")
        message = _(
            "GSTR-2B MISMATCH FOUND\n\n"
            "We found %d invoice(s) that don't match vendor data.\n"
            "Review: %s\nContact vendors before filing."
        ) % (len(mismatches), url)

        notify_user(user, subject, message, "GST Filing Checklist")
        _send_whatsapp_sms(user, subject, message)
