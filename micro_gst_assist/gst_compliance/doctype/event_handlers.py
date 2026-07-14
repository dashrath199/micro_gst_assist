# -*- coding: utf-8 -*-
"""
Standalone event handlers for doc_events configured in hooks.py.
Receives (doc, method) from Frappe's document event system.
"""

import frappe
from frappe import _
from micro_gst_assist.gst_compliance.utils import extract_gst_totals, auto_populate_gst_rate


# ─────────────────────────────────────────────────────────────────
# SALES INVOICE EVENTS
# ─────────────────────────────────────────────────────────────────

def validate_gst_fields(doc, method):
    """
    Before Submit validation for Sales Invoice.
    Blocks submission if HSN code or GST rate is missing on any item.
    """
    errors = []
    for item in doc.items:
        if not item.get("gst_hsn_code"):
            errors.append(
                _("Row #{0}: Item {1} is missing HSN/SAC code").format(
                    item.idx, item.item_code or item.item_name
                )
            )
        if not item.get("gst_rate") and item.get("gst_hsn_code"):
            auto_populate_gst_rate(item)
        if not item.get("gst_rate"):
            errors.append(
                _("Row #{0}: Item {1} is missing GST rate").format(
                    item.idx, item.item_code or item.item_name
                )
            )

    if errors:
        frappe.throw(
            _("Cannot submit invoice. Please fix the following GST field issues:<br>{0}").format(
                "<br>".join(errors)
            ),
            title=_("GST Fields Missing"),
        )


def on_sales_invoice_submit(doc, method):
    """
    On Submit handler for Sales Invoice.
    Creates a GST Invoice Audit Log entry.
    """
    audit_status = "Valid"
    errors = []

    for item in doc.items:
        if not item.get("gst_hsn_code"):
            audit_status = "Missing HSN"
            errors.append("Item %s missing HSN" % (item.item_code or item.item_name))
        if not item.get("gst_rate"):
            if audit_status != "Missing HSN":
                audit_status = "Missing GST Rate"
            errors.append("Item %s missing GST rate" % (item.item_code or item.item_name))

    _create_audit_log(doc, audit_status, errors)


def _create_audit_log(doc, status, errors=None):
    """Create or update GST Invoice Audit Log for the given Sales Invoice."""
    existing = frappe.db.get_value("GST Invoice Audit Log", {"sales_invoice": doc.name})
    gst = extract_gst_totals(doc)

    data = {
        "doctype": "GST Invoice Audit Log",
        "sales_invoice": doc.name,
        "audit_date": frappe.utils.now(),
        "gst_status": status,
        "company": doc.company,
        "hsn_code": doc.items[0].get("gst_hsn_code") if doc.items else "",
        "gst_rate": doc.items[0].get("gst_rate") if doc.items else 0,
        "taxable_value": doc.net_total or 0,
        "cgst": gst["cgst"],
        "sgst": gst["sgst"],
        "igst": gst["igst"],
        "has_e_invoice": bool(doc.get("e_invoice_status")),
        "has_e_waybill": bool(doc.get("e_waybill_status")),
        "errors": ", ".join(errors) if errors else None,
        "resolved": 0 if errors else 1,
    }

    if existing:
        audit = frappe.get_doc("GST Invoice Audit Log", existing)
        audit.update(data)
        audit.save(ignore_permissions=True)
    else:
        frappe.get_doc(data).insert(ignore_permissions=True)


# ─────────────────────────────────────────────────────────────────
# GST FILING CHECKLIST EVENTS
# ─────────────────────────────────────────────────────────────────

def update_checklist_counts(doc, method):
    """
    Before Save hook for GST Filing Checklist.
    Auto-calculates total_items and completed_items from child table.
    """
    if doc.get("items"):
        doc.total_items = len(doc.items)
        doc.completed_items = len([i for i in doc.items if i.status == "Completed"])
    else:
        doc.total_items = 0
        doc.completed_items = 0


# ─────────────────────────────────────────────────────────────────
# PERMISSION HELPERS
# ─────────────────────────────────────────────────────────────────

def get_permission_query_conditions(user=None):
    """Restrict GST Filing Checklist visibility to own records for Shop Owner role."""
    if not user:
        user = frappe.session.user
    if "System Manager" in frappe.get_roles(user):
        return ""
    return """(`tabGST Filing Checklist`.owner = {user})""".format(
        user=frappe.db.escape(user)
    )


def has_permission(doc, ptype, user=None):
    """Check if user has permission on the given document."""
    if not user:
        user = frappe.session.user
    if "System Manager" in frappe.get_roles(user):
        return True
    if ptype in ("read", "write", "create"):
        return doc.owner == user
    return False
