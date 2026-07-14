# -*- coding: utf-8 -*-
"""
Whitelisted API endpoints for the simplified GST invoice entry screen.
Routes through standard Sales Invoice Doctype in the background.
"""

import frappe
from frappe import _
from frappe.utils import nowdate, flt

from micro_gst_assist.gst_compliance.utils import get_default_company


@frappe.whitelist()
def create_simple_invoice(party, items, payment_mode, gst_rate=None, hsn_code=None):
    """
    Creates a Sales Invoice with sensible defaults.
    Only exposes: party, items, amount, GST rate, payment mode.
    """
    si = frappe.new_doc("Sales Invoice")
    si.customer = party
    si.posting_date = nowdate()
    si.due_date = nowdate()

    company = get_default_company()
    si.company = company
    default_warehouse = _get_default_warehouse(company)

    si.update_stock = 1 if payment_mode != "Credit" else 0

    if not isinstance(items, list):
        try:
            items = frappe.parse_json(items)
        except (TypeError, ValueError):
            frappe.throw(_("Items must be a valid list"))

    income_account = _get_default_income_account(company)
    for item in items:
        si.append("items", {
            "item_code": item.get("item_code"),
            "qty": flt(item.get("qty", 1)),
            "rate": flt(item.get("rate", 0)),
            "warehouse": default_warehouse,
            "income_account": income_account,
            "gst_hsn_code": hsn_code or item.get("hsn_code", ""),
        })

    if gst_rate or hsn_code:
        _apply_gst_template(si, company)

    si.append("payment_schedule", {
        "due_date": si.due_date,
        "payment_amount": si.total or 0
    })

    si.flags.ignore_mandatory = False
    si.flags.ignore_permissions = False
    si.insert(ignore_permissions=False)

    if payment_mode != "Credit":
        si.submit()

    return si.name


def _get_default_warehouse(company):
    wh = frappe.db.get_value("Company", company, "default_warehouse")
    if not wh:
        wh = frappe.db.get_value("Warehouse", {"company": company, "is_group": 0}, "name")
    return wh


def _get_default_income_account(company):
    acc = frappe.db.get_value("Company", company, "default_income_account")
    if not acc:
        acc = frappe.db.get_value(
            "Account", {"company": company, "is_group": 0, "account_type": "Income Account"}, "name"
        )
    return acc


def _apply_gst_template(si, company):
    templates = frappe.get_all(
        "Sales Taxes and Charges Template",
        filters={"company": company, "tax_category": "In-State", "disabled": 0},
        limit=1,
    )
    if templates:
        si.taxes_and_charges = templates[0].name
        template = frappe.get_doc("Sales Taxes and Charges Template", templates[0].name)
        for tax in template.taxes:
            si.append("taxes", {
                "charge_type": tax.charge_type,
                "account_head": tax.account_head,
                "description": tax.description,
                "rate": tax.rate,
            })


@frappe.whitelist()
def get_gst_defaults(company=None):
    """Returns GST defaults to pre-populate the simplified invoice UI."""
    company = company or get_default_company()
    return {
        "company": company,
        "default_warehouse": frappe.db.get_value("Company", company, "default_warehouse"),
        "payment_modes": ["Cash", "Bank", "UPI", "Credit"],
        "gst_rates": frappe.get_all("GST Rate", fields=["rate", "hsn_code"], limit=20),
    }


@frappe.whitelist()
def validate_invoice_gst_fields(docname):
    """Validates that a Sales Invoice has all required GST fields."""
    si = frappe.get_doc("Sales Invoice", docname)
    errors = []
    for item in si.items:
        if not item.gst_hsn_code:
            errors.append(_("Item %s is missing HSN code") % (item.item_code or item.item_name))
        if not item.get("gst_rate"):
            errors.append(_("Item %s is missing GST rate") % (item.item_code or item.item_name))
    return {"valid": len(errors) == 0, "errors": errors}


@frappe.whitelist()
def get_days_to_deadline():
    """Returns days until the nearest filing deadline. Used by workspace Number Card."""
    today = frappe.utils.getdate(nowdate())
    nearest = frappe.get_all(
        "GST Filing Checklist",
        filters={"status": ["in", ["Draft", "In Progress"]]},
        fields=["name", "due_date", "filing_period"],
        order_by="due_date ASC",
        limit=1,
    )
    if not nearest:
        return {"days": None, "label": "No upcoming deadlines"}

    due = frappe.utils.getdate(nearest[0].due_date)
    days = frappe.utils.date_diff(due, today)

    if days < 0:
        label = f"OVERDUE by {abs(days)} days"
    elif days == 0:
        label = "Due TODAY"
    elif days == 1:
        label = "Due Tomorrow"
    else:
        label = f"{days} days remaining"

    return {"days": days, "period": nearest[0].filing_period, "label": label, "checklist": nearest[0].name}
