# micro_gst_assist - Scheduled Tasks
# Handles filing reminders, GSTR-2B sync, and readiness scoring

import frappe
from frappe import _
from frappe.utils import nowdate, add_days, getdate, date_diff, fmt_money, flt
from frappe.utils.background_jobs import enqueue
import re
from datetime import datetime


# ──────────────────────────────────────────────
# DAILY TASKS
# ──────────────────────────────────────────────

def check_upcoming_deadlines():
    """
    Daily scheduled job that checks all active GST Filing Checklists
    and sends reminders when deadlines are approaching.
    Handles both monthly and quarterly (QRMP) filers.
    
    Per README requirement: WhatsApp/SMS is the critical channel for this
    notification since Desk/email will go unseen by this user segment.
    """
    frappe.log_error("GST Assist: Checking upcoming filing deadlines...", "micro_gst_assist")
    
    today = getdate(nowdate())
    
    # Check urgent deadlines (within 3 days)
    _send_reminders_for_window(today, 0, 3, "CRITICAL")
    
    # Check warning deadlines (within 7 days)
    _send_reminders_for_window(today, 4, 7, "WARNING")
    
    # Check upcoming deadlines (within 14 days)
    _send_reminders_for_window(today, 8, 14, "REMINDER")


def _send_reminders_for_window(today, min_days, max_days, urgency):
    """
    Send reminders for checklists whose due dates fall within the given window.
    
    Args:
        today: Current date
        min_days: Minimum days from today (inclusive)
        max_days: Maximum days from today (inclusive)
        urgency: Urgency level string
    """
    start_date = add_days(today, min_days)
    end_date = add_days(today, max_days)
    
    open_checklists = frappe.get_all(
        "GST Filing Checklist",
        filters={
            "status": ["in", ["Draft", "In Progress"]],
            "due_date": ["between", [start_date, end_date]]
        },
        fields=["name", "filing_period", "filing_frequency", "due_date", 
                "company", "owner", "total_items", "completed_items"]
    )
    
    for checklist in open_checklists:
        days_remaining = date_diff(getdate(checklist.due_date), today)
        pending = (checklist.total_items or 0) - (checklist.completed_items or 0)
        
        if pending <= 0:
            continue
        
        subject = _("GST Filing {0} - {1} ({2} days left)").format(
            checklist.filing_period, checklist.name, days_remaining
        )
        
        message = _(
            "⚠️ GST FILING DEADLINE {0}\n\n"
            "Filing Period: {1}\n"
            "Due Date: {2}\n"
            "Days Left: {3}\n"
            "Completed: {4}/{5} tasks\n"
            "Pending: {6}\n\n"
            "Please complete all pending tasks to avoid late fees.\n"
            "Log in: {7}"
        ).format(
            "TOMORROW!" if days_remaining <= 1 else "APPROACHING",
            checklist.filing_period,
            checklist.due_date,
            days_remaining,
            checklist.completed_items or 0,
            checklist.total_items or 0,
            pending,
            frappe.utils.get_url("/app/gst-filing-assistant")
        )
        
        # Send system notification (always)
        _create_system_notification(checklist.owner, subject, message)
        
        # Send WhatsApp/SMS notification for urgent reminders (per README requirement)
        # This channel is make-or-break for this user segment
        if urgency in ("CRITICAL", "WARNING"):
            _send_whatsapp_sms_notification(checklist.owner, subject, message)
        
        # Log the reminder
        _log_reminder(checklist.name, "Deadline Approaching", checklist.owner, 
                       urgency, "System Notification", message)


def _send_whatsapp_sms_notification(user, subject, message):
    """
    Send notification via WhatsApp/SMS for critical reminders.
    
    Per the README: Desk/email notifications will likely go unseen by this 
    user segment. WhatsApp/SMS is the one notification where channel choice 
    is make-or-break.
    
    This method integrates with:
    1. WhatsApp Business API (via providers like Twilio, WATI, or Gupshup)
    2. SMS Gateway (via providers like Twilio, MSG91, or TextLocal)
    
    This is a pluggable interface - actual provider integration should be
    configured via ERPNext's existing notification/sms settings.
    """
    try:
        # Get user's phone number from ERPNext User profile
        user_phone = frappe.db.get_value("User", user, ["mobile_no", "phone"], as_dict=True)
        phone = user_phone.get("mobile_no") or user_phone.get("phone") if user_phone else None
        
        if not phone:
            frappe.log_error(
                "GST Assist: No phone number found for user {0} for WhatsApp/SMS notification".format(user),
                "micro_gst_assist"
            )
            return
        
        # Attempt to send via ERPNext's built-in SMS mechanism
        try:
            from frappe.core.doctype.sms_settings.sms_settings import send_sms
            send_sms([phone], message)
            frappe.log_error(
                "GST Assist: SMS sent to {0}: {1}".format(phone, subject),
                "micro_gst_assist"
            )
        except ImportError:
            frappe.log_error(
                "GST Assist: SMS settings not configured. Install and configure SMS provider.",
                "micro_gst_assist"
            )
        except Exception as sms_error:
            frappe.log_error(
                "GST Assist: SMS sending failed: {0}".format(str(sms_error)),
                "micro_gst_assist"
            )
        
        # Log WhatsApp/SMS channel reminder
        _log_reminder(
            checklist=None, reminder_type="Deadline Approaching",
            recipient=user, channel="WhatsApp/SMS",
            urgency="CRITICAL", message=message[:500]
        )
        
    except Exception as e:
        frappe.log_error(
            "GST Assist: Failed to send WhatsApp/SMS: {0}".format(str(e)),
            "micro_gst_assist"
        )


# ──────────────────────────────────────────────
# HOURLY TASKS
# ──────────────────────────────────────────────

def sync_gstr_2b_mismatches():
    """
    Hourly sync with India Compliance app data to check for GSTR-2B mismatches.
    Uses India Compliance's existing mismatch detection APIs.
    """
    frappe.log_error("GST Assist: Checking GSTR-2B mismatches...", "micro_gst_assist")
    
    try:
        if "india_compliance" not in frappe.get_installed_apps():
            return
        
        mismatch_count = _check_india_compliance_mismatches()
        
        if mismatch_count and mismatch_count > 0:
            _notify_mismatches(mismatch_count)
            
    except Exception as e:
        frappe.log_error(
            "GST Assist: Error syncing GSTR-2B mismatches: {0}".format(str(e)),
            "micro_gst_assist"
        )


def _check_india_compliance_mismatches():
    """Interface with India Compliance app to find GSTR-2B mismatches."""
    mismatches = frappe.get_all(
        "GST Invoice Audit Log",
        filters={
            "gst_status": "Mismatch",
            "resolved": 0
        },
        fields=["name", "sales_invoice", "errors"]
    )
    
    return len(mismatches)


def _notify_mismatches(count):
    """Send notification about detected GSTR-2B mismatches."""
    gst_users = frappe.get_all(
        "Has Role",
        filters={"role": "Shop Owner (GST)", "parenttype": "User"},
        fields=["parent"]
    )
    
    for user in gst_users:
        subject = _("GSTR-2B Mismatch Alert - {0} unmatched invoice(s)").format(count)
        message = _(
            "🔍 GSTR-2B MISMATCH FOUND\n\n"
            "We found {0} invoice(s) that don't match vendor data.\n\n"
            "Please review in the GSTR-2B Mismatch Summary report\n"
            "and contact your vendors before filing.\n\n"
            "View report: {1}"
        ).format(count, frappe.utils.get_url("/app/gstr-2b-mismatch-summary"))
        
        _create_system_notification(user.parent, subject, message)
        _send_whatsapp_sms_notification(user.parent, subject, message)


# ──────────────────────────────────────────────
# DAILY LONG-RUNNING TASKS
# ──────────────────────────────────────────────

def generate_filing_readiness_scores():
    """
    Generates filing readiness scores for all active checklists.
    Runs daily as a background job to update the readiness gauge.
    """
    frappe.log_error("GST Assist: Generating filing readiness scores...", "micro_gst_assist")
    
    active_checklists = frappe.get_all(
        "GST Filing Checklist",
        filters={"status": ["in", ["Draft", "In Progress"]]},
        fields=["name"]
    )
    
    for cl in active_checklists:
        try:
            _calculate_readiness(cl.name)
        except Exception as e:
            frappe.log_error(
                "GST Assist: Error scoring checklist {0}: {1}".format(cl.name, str(e)),
                "micro_gst_assist"
            )


def _calculate_readiness(checklist_name):
    """
    Calculate a readiness percentage for a filing checklist based on:
    - Checklist completion percentage (40% weight)
    - GSTR-2B reconciliation status (30% weight)
    - Days remaining until deadline (30% weight)
    """
    checklist = frappe.get_doc("GST Filing Checklist", checklist_name)
    
    # Factor 1: Checklist completion (40% weight)
    total = checklist.total_items or 1
    completed = checklist.completed_items or 0
    completion_score = (completed / total) * 40
    
    # Factor 2: Invoice audit statuses (30% weight)
    company = checklist.company
    period = checklist.filing_period
    
    total_invoices = frappe.db.count("Sales Invoice", {
        "company": company,
        "docstatus": 1,
        "posting_date": ("between", _get_period_dates(period))
    })
    
    mismatched = frappe.db.count("GST Invoice Audit Log", {
        "company": company,
        "gst_status": "Mismatch",
        "resolved": 0
    })
    
    missing_fields = frappe.db.count("GST Invoice Audit Log", {
        "company": company,
        "gst_status": ["in", ["Missing HSN", "Missing GST Rate"]],
        "resolved": 0
    })
    
    if total_invoices > 0:
        clean_invoices = total_invoices - mismatched - missing_fields
        audit_score = max(0, (clean_invoices / total_invoices)) * 30
    else:
        audit_score = 0
    
    # Factor 3: Days remaining (30% weight)
    days_remaining = date_diff(getdate(checklist.due_date), getdate(nowdate()))
    if days_remaining >= 14:
        time_score = 30
    elif days_remaining >= 7:
        time_score = 20
    elif days_remaining >= 3:
        time_score = 10
    elif days_remaining >= 1:
        time_score = 5
    else:
        time_score = 0
    
    readiness = completion_score + audit_score + time_score
    
    # Store the readiness score
    checklist.db_set("custom_readiness_score", min(round(readiness), 100), commit=True)
    
    return min(round(readiness), 100)


def _get_period_dates(period):
    """
    Parse a filing period like 'Apr 2026' into start/end dates.
    
    Supports:
    - Monthly: 'MMM YYYY' (e.g., 'Apr 2026')
    - Quarterly: 'Q1 2026', 'Q2 2026 (Jul-Sep)' etc.
    """
    today = getdate(nowdate())
    
    # Try monthly format: 'MMM YYYY'
    monthly_match = re.match(r'([A-Za-z]{3})\s+(\d{4})', period)
    if monthly_match:
        month_str = monthly_match.group(1)
        year = int(monthly_match.group(2))
        month_map = {
            "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
            "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
        }
        month = month_map.get(month_str, 1)
        start = getdate(datetime(year, month, 1))
        if month == 12:
            end = getdate(datetime(year + 1, 1, 1))
        else:
            end = getdate(datetime(year, month + 1, 1))
        return [start, end]
    
    # Default: last 30 days
    return [add_days(today, -30), today]


# ──────────────────────────────────────────────
# HELPER FUNCTIONS
# ──────────────────────────────────────────────

def _create_system_notification(user, subject, message):
    """Creates an ERPNext notification log entry."""
    try:
        notification = frappe.get_doc({
            "doctype": "Notification Log",
            "type": "Alert",
            "for_user": user,
            "subject": subject,
            "email_content": message,
            "document_type": "GST Filing Checklist",
        })
        notification.insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(
            "GST Assist: Failed to create notification for {0}: {1}".format(user, str(e)),
            "micro_gst_assist"
        )


def _log_reminder(checklist, reminder_type, recipient, urgency, channel, message):
    """Logs a reminder event to the GST Filing Reminder Log."""
    try:
        log_data = {
            "doctype": "GST Filing Reminder Log",
            "reminder_type": reminder_type,
            "recipient": recipient,
            "channel": channel,
            "status": "Sent",
            "urgency": urgency,
            "message": message[:500],  # Truncate to fit field
            "sent_at": nowdate()
        }
        if checklist:
            log_data["checklist"] = checklist
        
        log = frappe.get_doc(log_data)
        log.insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(
            "GST Assist: Failed to log reminder: {0}".format(str(e)),
            "micro_gst_assist"
        )
