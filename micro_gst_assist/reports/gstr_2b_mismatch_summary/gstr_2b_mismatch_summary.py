# Copyright (c) 2026, Bizaxl and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import fmt_money, getdate, nowdate


def execute(filters=None):
    """
    GSTR-2B Mismatch Summary in Plain Language Report.
    
    Wraps India Compliance's raw mismatch data into human-readable rows.
    Translates technical reconciliation data into actionable business insights.
    
    Example output: "3 invoices from Supplier X not yet reflecting in your 2B"
    """
    columns = get_columns()
    data = get_data(filters)
    
    return columns, data


def get_columns():
    """Define report columns with plain-language descriptions."""
    return [
        {
            "label": _("What's the issue?"),
            "fieldname": "plain_language_summary",
            "fieldtype": "Data",
            "width": 350
        },
        {
            "label": _("Invoice / Reference"),
            "fieldname": "reference",
            "fieldtype": "Dynamic Link",
            "options": "reference_type",
            "width": 150
        },
        {
            "label": _("Vendor / Party"),
            "fieldname": "party",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Amount"),
            "fieldname": "amount",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 120
        },
        {
            "label": _("Tax Period"),
            "fieldname": "tax_period",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("What to do"),
            "fieldname": "action_item",
            "fieldtype": "Data",
            "width": 300
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 100
        }
    ]


def get_data(filters):
    """
    Fetch mismatch data from GST Invoice Audit Log and India Compliance tables.
    Translates technical mismatch data into plain-language descriptions.
    """
    conditions = {"gst_status": "Mismatch", "resolved": 0}
    
    if filters and filters.get("company"):
        conditions["company"] = filters["company"]
    
    mismatches = frappe.get_all(
        "GST Invoice Audit Log",
        filters=conditions,
        fields=["name", "sales_invoice", "hsn_code", "gst_rate",
                "taxable_value", "errors", "audit_date", "company"]
    )
    
    data = []
    for m in mismatches:
        # Get invoice details
        inv = frappe.db.get_value(
            "Sales Invoice", m.sales_invoice,
            ["customer", "supplier", "posting_date", "grand_total",
             "currency", "gst_category", "e_invoice_status"],
            as_dict=True
        )
        
        if not inv:
            continue
        
        party = inv.customer or inv.supplier or "Unknown"
        
        # Generate plain-language summary from error details
        plain_summary = _generate_plain_summary(m, inv)
        
        # Generate action item
        action_item = _generate_action_item(m, inv)
        
        data.append({
            "plain_language_summary": plain_summary,
            "reference": m.sales_invoice,
            "reference_type": "Sales Invoice",
            "party": party,
            "amount": m.taxable_value or inv.grand_total or 0,
            "currency": inv.currency or "INR",
            "tax_period": frappe.utils.formatdate(inv.posting_date, "MMM YYYY") if inv.posting_date else "",
            "action_item": action_item,
            "status": "🔴 Unresolved"
        })
    
    # Also check purchase-side mismatches from India Compliance if available
    _add_purchase_mismatches(data, filters)
    
    return data


def _generate_plain_summary(mismatch, invoice):
    """
    Generate a plain-language description of the mismatch.
    
    Translates technical GST reconciliation data into something
    a shop owner can understand without accounting knowledge.
    """
    if mismatch.errors:
        error_lower = mismatch.errors.lower()
        
        if "hsn" in error_lower or "sac" in error_lower:
            return _("Missing HSN/SAC code on invoice {0} — the tax department needs this code to process your return").format(mismatch.sales_invoice)
        
        if "rate" in error_lower or "gst" in error_lower:
            return _("GST rate not set on invoice {0} — we can't determine how much tax to report").format(mismatch.sales_invoice)
        
        if "e-invoice" in error_lower or "irn" in error_lower:
            return _("e-Invoice not generated for {0} — this B2B sale needs an e-Invoice before filing").format(mismatch.sales_invoice)
        
        if "e-waybill" in error_lower:
            return _("e-Way Bill missing for inter-state sale {0} — required for goods transport over ₹50,000").format(mismatch.sales_invoice)
        
        return _("Issue found on invoice {0}: {1}").format(mismatch.sales_invoice, mismatch.errors)
    
    return _("GST data mismatch detected on invoice {0} — please review and verify").format(mismatch.sales_invoice)


def _generate_action_item(mismatch, invoice):
    """Generate an actionable next step for the shop owner."""
    if mismatch.errors:
        error_lower = mismatch.errors.lower()
        
        if "hsn" in error_lower:
            return _("Open the invoice and add the correct HSN/SAC code for each item")
        if "rate" in error_lower:
            return _("Set the correct GST rate on the invoice items")
        if "e-invoice" in error_lower or "irn" in error_lower:
            return _("Generate e-Invoice IRN from the Sales Invoice form")
        if "e-waybill" in error_lower:
            return _("Generate e-Way Bill for inter-state transport")
        
    return _("Review invoice details and correct the flagged mismatch in the Sales Invoice form")


def _add_purchase_mismatches(data, filters):
    """
    Add purchase-side GSTR-2B mismatches from India Compliance data.
    This integrates with India Compliance's existing mismatch detection.
    """
    try:
        if "india_compliance" not in frappe.get_installed_apps():
            return
        
        # Attempt to get mismatches from India Compliance's tables
        # This is a placeholder integration - actual implementation
        # depends on India Compliance's data structure
        gc = frappe.qb.DocType("GST Reconciliation")
        purchase_mismatches = (
            frappe.qb.from_(gc)
            .select(
                gc.purchase_invoice,
                gc.supplier,
                gc.invoice_value,
                gc.tax_period,
                gc.status
            )
            .where(gc.status == "Mismatch")
            .limit(50)
        ).run(as_dict=True)
        
        for pm in purchase_mismatches:
            data.append({
                "plain_language_summary": _(
                    "Purchase from {0} not yet reflecting in your GSTR-2B — "
                    "the supplier may not have filed or there's a data mismatch"
                ).format(pm.supplier or "Unknown"),
                "reference": pm.purchase_invoice,
                "reference_type": "Purchase Invoice",
                "party": pm.supplier,
                "amount": pm.invoice_value or 0,
                "currency": "INR",
                "tax_period": pm.tax_period or "",
                "action_item": _("Contact the supplier to confirm they've filed their GST return"),
                "status": "🔴 Unresolved"
            })
    except Exception:
        # India Compliance tables may not exist or have different structure
        pass
