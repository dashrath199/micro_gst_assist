# Copyright (c) 2026, Bizaxl and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate, fmt_money


def execute(filters=None):
    """
    Daily GST Summary Report.
    
    Provides a quick snapshot of today's GST compliance status:
    - Number of invoices created today
    - GST validation status breakdown
    - Missing fields vs valid invoices
    - Total taxable value and GST amounts
    """
    columns = get_columns()
    data = get_data(filters)
    
    return columns, data


def get_columns():
    return [
        {
            "label": _("Metric"),
            "fieldname": "metric",
            "fieldtype": "Data",
            "width": 200
        },
        {
            "label": _("Value"),
            "fieldname": "value",
            "fieldtype": "Data",
            "width": 150
        }
    ]


def get_data(filters):
    today = nowdate()
    conditions = {"audit_date": ["between", [today + " 00:00:00", today + " 23:59:59"]]}
    
    if filters and filters.get("company"):
        conditions["company"] = filters["company"]
    
    total_audits = frappe.db.count("GST Invoice Audit Log", conditions)
    valid_count = frappe.db.count("GST Invoice Audit Log", dict(conditions, gst_status="Valid"))
    mismatches = frappe.db.count("GST Invoice Audit Log", dict(conditions, gst_status="Mismatch"))
    missing_hsn = frappe.db.count("GST Invoice Audit Log", dict(conditions, gst_status="Missing HSN"))
    missing_rate = frappe.db.count("GST Invoice Audit Log", dict(conditions, gst_status="Missing GST Rate"))
    
    # Total values
    tax_values = frappe.db.sql("""
        SELECT
            COALESCE(SUM(taxable_value), 0) as total_taxable,
            COALESCE(SUM(cgst), 0) as total_cgst,
            COALESCE(SUM(sgst), 0) as total_sgst,
            COALESCE(SUM(igst), 0) as total_igst
        FROM `tabGST Invoice Audit Log`
        WHERE audit_date BETWEEN %s AND %s
    """, [today + " 00:00:00", today + " 23:59:59"], as_dict=True)[0]
    
    data = [
        {"metric": _("📊 Invoices Audited Today"), "value": str(total_audits)},
        {"metric": _("✅ Valid Invoices"), "value": str(valid_count)},
        {"metric": _("❌ Mismatches Found"), "value": str(mismatches)},
        {"metric": _("⚠️ Missing HSN Codes"), "value": str(missing_hsn)},
        {"metric": _("⚠️ Missing GST Rates"), "value": str(missing_rate)},
        {"metric": _("💰 Total Taxable Value"), "value": fmt_money(tax_values.total_taxable, currency="INR")},
        {"metric": _("🧾 Total CGST"), "value": fmt_money(tax_values.total_cgst, currency="INR")},
        {"metric": _("🧾 Total SGST"), "value": fmt_money(tax_values.total_sgst, currency="INR")},
        {"metric": _("🧾 Total IGST"), "value": fmt_money(tax_values.total_igst, currency="INR")},
    ]
    
    return data
