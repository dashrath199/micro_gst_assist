# micro_gst_assist - Document Event Hooks
# Validates GST fields on Sales Invoice, updates checklist counts

import frappe
from frappe import _


def validate_gst_fields(doc, method):
    """
    Before Submit validation for Sales Invoice.
    Blocks submission if HSN code or GST rate is missing on any item.
    This prevents bad data at the source per the README requirement.
    """
    from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
    
    errors = []
    for item in doc.items:
        if not item.get("gst_hsn_code"):
            errors.append(_("Row #{0}: Item {1} is missing HSN/SAC code").format(
                item.idx, item.item_code or item.item_name
            ))
        if not item.get("gst_rate") and item.get("gst_hsn_code"):
            # If HSN is present but GST rate is missing, try auto-populating it
            _auto_populate_gst_rate(item)
        if not item.get("gst_rate"):
            errors.append(_("Row #{0}: Item {1} is missing GST rate").format(
                item.idx, item.item_code or item.item_name
            ))
    
    if errors:
        frappe.throw(
            _("Cannot submit invoice. Please fix the following GST field issues:<br>{0}").format(
                "<br>".join(errors)
            ),
            title=_("GST Fields Missing")
        )
    
    # Create/update audit log entry
    _update_audit_log(doc, "Valid" if not errors else "Missing Fields")


def _auto_populate_gst_rate(item):
    """Attempt to auto-populate GST rate from HSN code master."""
    if item.get("gst_hsn_code"):
        hsn_data = frappe.db.get_value(
            "GST HSN Code", 
            item.gst_hsn_code, 
            "gst_rate"
        )
        if hsn_data:
            item.gst_rate = hsn_data


def on_sales_invoice_submit(doc, method):
    """
    On Submit handler for Sales Invoice.
    Creates a GST Invoice Audit Log entry and updates filing checklist completion.
    """
    # Create audit log
    audit_status = "Valid"
    errors = []
    
    for item in doc.items:
        if not item.get("gst_hsn_code"):
            audit_status = "Missing HSN"
            errors.append("Item {0} missing HSN".format(item.item_code or item.item_name))
        if not item.get("gst_rate"):
            audit_status = "Missing GST Rate" if audit_status != "Missing HSN" else audit_status
            errors.append("Item {0} missing GST rate".format(item.item_code or item.item_name))
    
    _update_audit_log(doc, audit_status, errors)


def _update_audit_log(doc, status, errors=None):
    """Create or update GST Invoice Audit Log for the given Sales Invoice."""
    existing = frappe.db.get_value(
        "GST Invoice Audit Log",
        {"sales_invoice": doc.name}
    )
    
    gst_details = _get_gst_totals(doc)
    
    audit_data = {
        "doctype": "GST Invoice Audit Log",
        "sales_invoice": doc.name,
        "audit_date": frappe.utils.now(),
        "gst_status": status,
        "hsn_code": doc.items[0].get("gst_hsn_code") if doc.items else "",
        "gst_rate": doc.items[0].get("gst_rate") if doc.items else 0,
        "taxable_value": doc.net_total or 0,
        "cgst": gst_details.get("cgst", 0),
        "sgst": gst_details.get("sgst", 0),
        "igst": gst_details.get("igst", 0),
        "has_e_invoice": bool(doc.get("e_invoice_status")),
        "has_e_waybill": bool(doc.get("e_waybill_status")),
        "errors": ", ".join(errors) if errors else None,
        "resolved": 0 if errors else 1,
    }
    
    if existing:
        audit = frappe.get_doc("GST Invoice Audit Log", existing)
        audit.update(audit_data)
        audit.save(ignore_permissions=True)
    else:
        audit = frappe.get_doc(audit_data)
        audit.insert(ignore_permissions=True)


def _get_gst_totals(doc):
    """Extract CGST, SGST, IGST totals from Sales Invoice taxes."""
    result = {"cgst": 0, "sgst": 0, "igst": 0}
    
    for tax in doc.get("taxes", []):
        account_name = (tax.account_head or "").lower()
        amount = tax.tax_amount or 0
        if "cgst" in account_name:
            result["cgst"] += amount
        elif "sgst" in account_name:
            result["sgst"] += amount
        elif "igst" in account_name:
            result["igst"] += amount
    
    return result


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


# ──────────────────────────────────────────────
# PERMISSION HELPERS
# ──────────────────────────────────────────────

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
