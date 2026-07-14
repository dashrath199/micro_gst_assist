# -*- coding: utf-8 -*-
"""
Runs once after `bench install-app micro_gst_assist` (see hooks.py after_install).
Creates custom roles, number cards, and the GST Filing Assistant workspace.
Wrapped defensively — failures here should never block installation.
"""
import frappe


def after_install():
    _create_roles()
    _create_number_cards()
    _create_workspace()
    _hide_standard_workspaces()
    frappe.db.commit()


# ─────────────────────────────────────────────────────────────────
# ROLES
# ─────────────────────────────────────────────────────────────────

def _create_roles():
    for role_name in ["Shop Owner (GST)"]:
        if not frappe.db.exists("Role", role_name):
            try:
                frappe.get_doc({
                    "doctype": "Role",
                    "role_name": role_name,
                    "desk_access": 1,
                    "home_page": "/app/gst-filing-assistant",
                }).insert(ignore_permissions=True)
            except Exception:
                frappe.log_error(frappe.get_traceback(), "GST Assist install: role creation failed")


# ─────────────────────────────────────────────────────────────────
# NUMBER CARDS
# ─────────────────────────────────────────────────────────────────

def _number_card(label, document_type, function="Count", filters_json="[]", color="#24963E"):
    if frappe.db.exists("Number Card", label):
        return
    try:
        frappe.get_doc({
            "doctype": "Number Card",
            "label": label,
            "document_type": document_type,
            "function": function,
            "filters_json": filters_json,
            "is_public": 1,
            "show_percentage_stats": 0,
            "color": color,
            "module": "GST Compliance Assistant",
        }).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"GST Assist install: Number Card '{label}' failed")


def _create_number_cards():
    _number_card("Pending Checklists", "GST Filing Checklist",
                 filters_json='[["GST Filing Checklist","status","!=","Completed"]]')
    _number_card("Overdue Checklists", "GST Filing Checklist",
                 filters_json='[["GST Filing Checklist","status","=","Overdue"]]', color="#FF5858")
    _number_card("Invoices to Audit", "GST Invoice Audit Log",
                 filters_json='[["GST Invoice Audit Log","resolved","=",0]]', color="#FFA00A")
    _number_card("Valid Invoices Today", "GST Invoice Audit Log",
                 filters_json='[["GST Invoice Audit Log","gst_status","=","Valid"],["GST Invoice Audit Log","audit_date","Timespan","today"]]',
                 color="#27AE60")
    _number_card("Pending Reminders", "GST Filing Reminder Log",
                 filters_json='[["GST Filing Reminder Log","status","=","Sent"]]', color="#FFA00A")


# ─────────────────────────────────────────────────────────────────
# WORKSPACE
# ─────────────────────────────────────────────────────────────────

def _create_workspace():
    if frappe.db.exists("Workspace", "GST Filing Assistant"):
        return
    try:
        cards = ["Pending Checklists", "Overdue Checklists", "Invoices to Audit",
                 "Valid Invoices Today", "Pending Reminders"]
        content = [{
            "id": "header",
            "type": "header",
            "data": {"text": '<span class="h4">GST Filing Assistant — Overview</span>', "col": 12},
        }]
        for card in cards:
            content.append({
                "id": card.replace(" ", "_"),
                "type": "number_card",
                "data": {"number_card_name": card, "col": 4},
            })

        shortcuts = [
            {"type": "DocType", "label": "GST Filing Checklist", "link_to": "GST Filing Checklist", "doc_view": "List"},
            {"type": "Page", "label": "New Sale (Simplified)", "link_to": "simplified-invoice"},
            {"type": "Report", "label": "Filing Readiness Score", "link_to": "Filing Readiness Score"},
            {"type": "Report", "label": "Upcoming Filing Deadlines", "link_to": "Upcoming Filing Deadlines"},
        ]

        ws = frappe.get_doc({
            "doctype": "Workspace",
            "name": "GST Filing Assistant",
            "title": "GST Filing Assistant",
            "module": "GST Compliance Assistant",
            "public": 1,
            "is_hidden": 0,
            "icon": "fa fa-file-text",
            "content": frappe.as_json(content),
            "shortcuts": [dict(s, doctype="Workspace Shortcut") for s in shortcuts],
        })
        ws.insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "GST Assist install: workspace creation failed")


# ─────────────────────────────────────────────────────────────────
# HIDE STANDARD WORKSPACES
# ─────────────────────────────────────────────────────────────────

def _hide_standard_workspaces():
    """Remove the Shop Owner (GST) role from standard ERPNext workspaces."""
    hidden = ["Accounts", "Selling", "Buying", "Stock", "CRM", "Manufacturing",
              "HR", "Projects", "Support", "Quality", "Assets", "Payroll",
              "Integrations", "Website", "Settings"]
    role_name = "Shop Owner (GST)"

    for ws_name in hidden:
        if not frappe.db.exists("Workspace", ws_name):
            continue
        try:
            ws = frappe.get_doc("Workspace", ws_name)
            changed = False
            for role_entry in ws.roles:
                if role_entry.role == role_name:
                    ws.roles = [r for r in ws.roles if r.role != role_name]
                    changed = True
                    break
            if changed:
                ws.save(ignore_permissions=True)
        except Exception:
            # Non-critical — just log and continue
            frappe.log_error(frappe.get_traceback(), f"GST Assist install: hiding workspace '{ws_name}' failed")
