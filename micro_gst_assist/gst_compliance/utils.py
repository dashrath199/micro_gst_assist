# -*- coding: utf-8 -*-
"""
Shared utilities for GST Compliance Assistant.
Provides helper functions used across the module.
"""

import re
import frappe
from frappe import _
from frappe.utils import nowdate, add_days, getdate, date_diff, flt
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════
# FILING PERIOD HELPERS
# ═══════════════════════════════════════════════════════════════════

def get_period_dates(period):
    """
    Parse a filing period like 'Apr 2026' into [start_date, end_date].
    
    Supports:
    - Monthly: 'MMM YYYY' (e.g., 'Apr 2026')
    - Quarterly: 'Q1 2026', 'Q2 2026 (Jul-Sep)' etc.
    
    Returns list of two dates or defaults to last 30 days.
    """
    today = getdate(nowdate())
    
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
        end = getdate(datetime(year + 1, 1, 1)) if month == 12 else getdate(datetime(year, month + 1, 1))
        return [start, end]
    
    return [add_days(today, -30), today]


def get_filing_month_name(month_num):
    """Return short month name from month number (1-12)."""
    names = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
             7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
    return names.get(month_num, "Jan")


def days_until_due(due_date):
    """Return integer days remaining until the due date (negative if overdue)."""
    return date_diff(getdate(due_date), getdate(nowdate()))


# ═══════════════════════════════════════════════════════════════════
# GST CALCULATION HELPERS
# ═══════════════════════════════════════════════════════════════════

def extract_gst_totals(doc):
    """Extract CGST, SGST, IGST totals from a Sales Invoice's tax table."""
    result = {"cgst": 0.0, "sgst": 0.0, "igst": 0.0}
    for tax in doc.get("taxes", []):
        name = (tax.account_head or "").lower()
        amount = flt(tax.tax_amount)
        if "cgst" in name:
            result["cgst"] += amount
        elif "sgst" in name:
            result["sgst"] += amount
        elif "igst" in name:
            result["igst"] += amount
    return result


def auto_populate_gst_rate(item):
    """Try to populate GST rate from HSN code master."""
    if item.get("gst_hsn_code"):
        rate = frappe.db.get_value("GST HSN Code", item.gst_hsn_code, "gst_rate")
        if rate:
            item.gst_rate = rate


# ═══════════════════════════════════════════════════════════════════
# READINESS SCORE COMPUTATION
# ═══════════════════════════════════════════════════════════════════

def compute_readiness_score(checklist):
    """
    Calculate a 0-100 readiness percentage for a filing checklist.
    
    Weight distribution:
    - Checklist completion: 40%
    - Invoice health (no mismatches/missing fields): 30%
    - Days remaining buffer: 30%
    """
    total = checklist.total_items or 1
    completed = checklist.completed_items or 0
    completion_pct = (completed / total) * 100
    
    # Checklist factor (40%)
    checklist_score = completion_pct * 0.4
    
    # Invoice audit factors (30%)
    company = checklist.company
    mismatched = frappe.db.count("GST Invoice Audit Log", {
        "company": company, "gst_status": "Mismatch", "resolved": 0
    })
    missing = frappe.db.count("GST Invoice Audit Log", {
        "company": company,
        "gst_status": ["in", ["Missing HSN", "Missing GST Rate"]],
        "resolved": 0
    })
    penalty = (mismatched * 10) + (missing * 5)
    invoice_score = max(0, 100 - penalty) * 0.3
    
    # Time remaining factor (30%)
    days = days_until_due(checklist.due_date) if checklist.due_date else 0
    time_score = 30 if days >= 14 else (20 if days >= 7 else (10 if days >= 3 else (5 if days >= 1 else 0)))
    
    return min(round(checklist_score + invoice_score + time_score), 100)


# ═══════════════════════════════════════════════════════════════════
# NOTIFICATION HELPERS
# ═══════════════════════════════════════════════════════════════════

def notify_user(user, subject, message, document_type=None, document_name=None):
    """Create a system Notification Log entry for a user."""
    try:
        frappe.get_doc({
            "doctype": "Notification Log",
            "subject": subject,
            "for_user": user,
            "type": "Alert",
            "document_type": document_type or "GST Filing Checklist",
            "document_name": document_name,
            "email_content": message,
        }).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "GST Assist: notification failed")


def get_default_company():
    """Safely get the default company for the current user/session."""
    company = frappe.defaults.get_user_default("Company")
    if not company:
        companies = frappe.get_list("Company", limit=1)
        if companies:
            company = companies[0].name
        else:
            frappe.throw(_("No Company found. Please create a Company first."))
    return company
