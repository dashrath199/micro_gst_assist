# Copyright (c) 2026, Bizaxl and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate, getdate, date_diff, fmt_date


def execute(filters=None):
    """
    Upcoming Filing Deadlines Report.
    
    Simple query report showing all open GST Filing Checklists
    sorted by due date. Provides a quick overview of what deadlines
    are approaching and what still needs to be done.
    """
    columns = get_columns()
    data = get_data(filters)
    
    return columns, data


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
            "label": _("Frequency"),
            "fieldname": "filing_frequency",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Due Date"),
            "fieldname": "due_date",
            "fieldtype": "Date",
            "width": 100
        },
        {
            "label": _("Days Left"),
            "fieldname": "days_remaining",
            "fieldtype": "Int",
            "width": 80
        },
        {
            "label": _("Total Tasks"),
            "fieldname": "total_items",
            "fieldtype": "Int",
            "width": 80
        },
        {
            "label": _("Completed"),
            "fieldname": "completed_items",
            "fieldtype": "Int",
            "width": 80
        },
        {
            "label": _("Pending"),
            "fieldname": "pending_items",
            "fieldtype": "Int",
            "width": 80
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Urgency"),
            "fieldname": "urgency",
            "fieldtype": "Data",
            "width": 100
        }
    ]


def get_data(filters):
    """Fetch checklist data from the database."""
    conditions = "1=1"
    values = {}
    
    if filters and filters.get("company"):
        conditions += " AND company = %(company)s"
        values["company"] = filters["company"]
    
    if filters and filters.get("status"):
        conditions += " AND status = %(status)s"
        values["status"] = filters["status"]
    
    # Only show active (non-completed) checklists by default
    conditions += " AND status != 'Completed'"
    
    query = """
        SELECT
            name,
            filing_period,
            company,
            filing_frequency,
            due_date,
            total_items,
            completed_items,
            status,
            custom_readiness_score
        FROM
            `tabGST Filing Checklist`
        WHERE
            {conditions}
        ORDER BY
            due_date ASC
    """.format(conditions=conditions)
    
    results = frappe.db.sql(query, values, as_dict=True)
    
    today = getdate(nowdate())
    data = []
    
    for r in results:
        days_remaining = date_diff(getdate(r.due_date), today) if r.due_date else 0
        pending = (r.total_items or 0) - (r.completed_items or 0)
        
        # Determine urgency
        if days_remaining < 0:
            urgency = "🔴 OVERDUE"
        elif days_remaining <= 1:
            urgency = "🔴 Due Tomorrow"
        elif days_remaining <= 3:
            urgency = "🟡 Due Soon"
        elif days_remaining <= 7:
            urgency = "🟢 This Week"
        else:
            urgency = "⚪ On Track"
        
        # Status display
        if days_remaining < 0:
            status_display = "🔴 Overdue"
        elif r.status == "In Progress":
            status_display = "🟡 In Progress"
        else:
            status_display = "⚪ Draft"
        
        data.append({
            "filing_period": r.filing_period,
            "company": r.company,
            "filing_frequency": r.filing_frequency,
            "due_date": r.due_date,
            "days_remaining": days_remaining,
            "total_items": r.total_items or 0,
            "completed_items": r.completed_items or 0,
            "pending_items": pending,
            "status": status_display,
            "urgency": urgency
        })
    
    return data
