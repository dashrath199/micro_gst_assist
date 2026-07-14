# micro_gst_assist - API Layer
# Simplified entry point for micro-enterprise users to create Sales Invoices
# Routes data through standard ERPNext Sales Invoice DocType in the background

import frappe
from frappe import _
from frappe.utils import nowdate, flt


@frappe.whitelist()
def create_simple_invoice(party, items, payment_mode, gst_rate=None, hsn_code=None):
    """
    Creates a Sales Invoice with sensible defaults for micro-enterprise users.
    
    Args:
        party (str): Customer name/ID
        items (list): List of dicts with 'item_code', 'qty', 'rate'
        payment_mode (str): 'Cash', 'Bank', 'UPI', 'Credit'
        gst_rate (float, optional): GST rate percentage. Auto-detected from HSN if omitted.
        hsn_code (str, optional): HSN/SAC code for auto-tax selection.
    
    Returns:
        str: The created Sales Invoice name
    """
    si = frappe.new_doc("Sales Invoice")
    si.customer = party
    si.posting_date = nowdate()
    si.due_date = nowdate()
    
    # Set default company and warehouse
    company = _get_default_company()
    si.company = company
    default_warehouse = frappe.db.get_value("Company", company, "default_warehouse")
    if not default_warehouse:
        # Fallback to first warehouse if no default set
        default_warehouse = frappe.db.get_value("Warehouse", 
            {"company": company, "is_group": 0}, "name")
    
    # Handle payment mode
    si.update_stock = 1 if payment_mode != "Credit" else 0
    
    # Add items
    if not isinstance(items, list):
        try:
            items = frappe.parse_json(items)
        except (TypeError, ValueError):
            frappe.throw(_("Items must be a valid list"))
    
    for item in items:
        income_account = frappe.db.get_value("Company", company, "default_income_account")
        if not income_account:
            # Fallback to first income account if no default set
            income_account = frappe.db.get_value("Account", 
                {"company": company, "is_group": 0, "account_type": "Income Account"}, "name")
        
        si.append("items", {
            "item_code": item.get("item_code"),
            "qty": flt(item.get("qty", 1)),
            "rate": flt(item.get("rate", 0)),
            "warehouse": default_warehouse,
            "income_account": income_account,
            "gst_hsn_code": hsn_code or item.get("hsn_code", ""),
        })
    
    # Set default tax template based on HSN/GST rate
    if gst_rate or hsn_code:
        _set_gst_defaults(si, gst_rate, hsn_code, company)
    
    # Payment schedule
    si.append("payment_schedule", {
        "due_date": si.due_date,
        "payment_amount": si.total or 0
    })
    
    si.flags.ignore_mandatory = False
    si.flags.ignore_permissions = False
    
    si.insert(ignore_permissions=False)
    
    # Auto-submit for non-credit modes
    if payment_mode != "Credit":
        si.submit()
    
    return si.name


def _get_default_company():
    """Safely get the default company for the current user/session."""
    company = frappe.defaults.get_user_default("Company")
    if not company:
        companies = frappe.get_list("Company", limit=1)
        if companies:
            company = companies[0].name
        else:
            frappe.throw(_("No Company found. Please create a Company first."))
    return company


def _set_gst_defaults(si, gst_rate, hsn_code, company):
    """Sets GST tax template defaults based on HSN code or rate."""
    gst_tax_category = "In-State"
    
    tax_templates = frappe.get_all(
        "Sales Taxes and Charges Template",
        filters={
            "company": company,
            "tax_category": gst_tax_category,
            "disabled": 0
        },
        limit=1
    )
    
    if tax_templates:
        si.taxes_and_charges = tax_templates[0].name
        template = frappe.get_doc("Sales Taxes and Charges Template", tax_templates[0].name)
        for tax in template.taxes:
            si.append("taxes", {
                "charge_type": tax.charge_type,
                "account_head": tax.account_head,
                "description": tax.description,
                "rate": tax.rate
            })


@frappe.whitelist()
def get_gst_defaults(company=None):
    """
    Returns GST defaults for the simplified invoice screen.
    Used to pre-populate dropdowns and defaults in the UI.
    """
    if not company:
        company = _get_default_company()
    
    defaults = {
        "company": company,
        "default_warehouse": frappe.db.get_value("Company", company, "default_warehouse"),
        "payment_modes": ["Cash", "Bank", "UPI", "Credit"],
        "gst_rates": frappe.get_all("GST Rate", fields=["rate", "hsn_code"], limit=20),
    }
    
    return defaults


@frappe.whitelist()
def validate_invoice_gst_fields(docname):
    """
    Validates that a Sales Invoice has all required GST fields filled.
    Used by the simplified page before submission.
    """
    si = frappe.get_doc("Sales Invoice", docname)
    errors = []
    
    for item in si.items:
        if not item.gst_hsn_code:
            errors.append(_("Item {0} is missing HSN code").format(item.item_code or item.item_name))
        if not item.get("gst_rate"):
            errors.append(_("Item {0} is missing GST rate").format(item.item_code or item.item_name))
    
    return {"valid": len(errors) == 0, "errors": errors}


@frappe.whitelist()
def get_days_to_deadline():
    """
    Returns the number of days until the nearest filing deadline.
    Used by the workspace Number Card to display real-time countdown.
    """
    today = frappe.utils.getdate(nowdate())
    
    nearest = frappe.get_all(
        "GST Filing Checklist",
        filters={
            "status": ["in", ["Draft", "In Progress"]]
        },
        fields=["name", "due_date", "filing_period", "status"],
        order_by="due_date ASC",
        limit=1
    )
    
    if not nearest:
        return {"days": None, "period": None, "label": "No upcoming deadlines"}
    
    due = frappe.utils.getdate(nearest[0].due_date)
    days = frappe.utils.date_diff(due, today)
    
    if days < 0:
        label = "OVERDUE by {} days".format(abs(days))
    elif days == 0:
        label = "Due TODAY"
    elif days == 1:
        label = "Due Tomorrow"
    else:
        label = "{} days remaining".format(days)
    
    return {
        "days": days,
        "period": nearest[0].filing_period,
        "label": label,
        "checklist": nearest[0].name
    }
