# Copyright (c) 2026, Bizaxl and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate, getdate, date_diff, flt


def execute(filters=None):
    """
    Filing Readiness Score Report.
    
    Evaluates how prepared the business is for the upcoming GST filing.
    Combines checklist completion, GSTR-2B reconciliation status, and
    invoice audit data into a single readiness percentage.
    
    Columns:
        - Filing Period
        - Company
        - Due Date
        - Days Remaining
        - Checklist Completion %
        - Invoices Audited
        - Mismatches Found
        - Missing GST Fields
        - Overall Readiness Score (%)
        - Status (Green/Yellow/Red)
    """
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    
    return columns, data, None, chart


def get_columns():
    """Define report columns."""
    return [
        {
            "label": _("Filing Period"),
            "fieldname": "filing_period",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Company"),
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 180
        },
        {
            "label": _("Due Date"),
            "fieldname": "due_date",
            "fieldtype": "Date",
            "width": 100
        },
        {
            "label": _("Days Remaining"),
            "fieldname": "days_remaining",
            "fieldtype": "Int",
            "width": 100
        },
        {
            "label": _("Checklist Completion"),
            "fieldname": "checklist_completion",
            "fieldtype": "Percent",
            "width": 120
        },
        {
            "label": _("Invoices Audited"),
            "fieldname": "invoices_audited",
            "fieldtype": "Int",
            "width": 120
        },
        {
            "label": _("Mismatches Found"),
            "fieldname": "mismatches",
            "fieldtype": "Int",
            "width": 120
        },
        {
            "label": _("Missing GST Fields"),
            "fieldname": "missing_fields",
            "fieldtype": "Int",
            "width": 120
        },
        {
            "label": _("Readiness Score"),
            "fieldname": "readiness_score",
            "fieldtype": "Percent",
            "width": 120
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 100
        }
    ]


def get_data(filters):
    """Fetch and compute readiness data for all active checklists."""
    conditions = {"status": ["in", ["Draft", "In Progress"]]}
    
    if filters and filters.get("company"):
        conditions["company"] = filters["company"]
    
    checklists = frappe.get_all(
        "GST Filing Checklist",
        filters=conditions,
        fields=["name", "filing_period", "company", "due_date",
                "total_items", "completed_items", "custom_readiness_score"]
    )
    
    data = []
    today = getdate(nowdate())
    
    for cl in checklists:
        days_remaining = date_diff(getdate(cl.due_date), today) if cl.due_date else 0
        
        # Checklist completion percentage
        total = cl.total_items or 1
        completed = cl.completed_items or 0
        completion_pct = round((completed / total) * 100)
        
        # Invoice audit stats for this company
        invoices_audited = frappe.db.count("GST Invoice Audit Log", {
            "company": cl.company
        })
        
        mismatches = frappe.db.count("GST Invoice Audit Log", {
            "company": cl.company,
            "gst_status": "Mismatch",
            "resolved": 0
        })
        
        missing_fields = frappe.db.count("GST Invoice Audit Log", {
            "company": cl.company,
            "gst_status": ["in", ["Missing HSN", "Missing GST Rate"]],
            "resolved": 0
        })
        
        # Calculate overall readiness score
        score = _compute_score(completion_pct, mismatches, missing_fields, days_remaining)
        
        # Determine status label
        if score >= 80:
            status = "✅ Ready"
        elif score >= 50:
            status = "⚠️ Needs Attention"
        else:
            status = "🔴 At Risk"
        
        data.append({
            "filing_period": cl.filing_period,
            "company": cl.company,
            "due_date": cl.due_date,
            "days_remaining": days_remaining,
            "checklist_completion": completion_pct,
            "invoices_audited": invoices_audited,
            "mismatches": mismatches,
            "missing_fields": missing_fields,
            "readiness_score": score,
            "status": status
        })
    
    return data


def _compute_score(completion_pct, mismatches, missing_fields, days_remaining):
    """
    Compute overall readiness score.
    
    Weight distribution:
    - Checklist completion: 40%
    - Invoice health (no mismatches or missing fields): 30%
    - Time remaining buffer: 30%
    """
    # Checklist factor (40%)
    checklist_score = completion_pct * 0.4
    
    # Invoice health factor (30%)
    invoice_penalty = (mismatches * 10) + (missing_fields * 5)
    invoice_score = max(0, 100 - invoice_penalty) * 0.3
    
    # Time remaining factor (30%)
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
    
    return min(round(checklist_score + invoice_score + time_score), 100)


def get_chart(data):
    """Generate a readiness score distribution chart."""
    if not data:
        return None
    
    labels = [d["filing_period"] for d in data]
    scores = [d["readiness_score"] for d in data]
    
    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": _("Readiness Score"),
                    "values": scores,
                    "chartType": "bar"
                }
            ]
        },
        "type": "bar",
        "height": 250,
        "colors": ["#24963E"],
        "barOptions": {
            "stacked": False
        }
    }
