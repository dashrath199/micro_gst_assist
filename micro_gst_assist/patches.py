# micro_gst_assist - Patch-based Migrations
# Run via bench migrate to apply these patches

import frappe
from frappe import _
import json
import os


def create_shop_owner_gst_role():
    """
    Pre-model-sync patch: Create the Shop Owner (GST) role.
    This role restricts user access to only the GST Filing Assistant 
    workspace and hides standard ERPNext accounting modules.
    """
    if not frappe.db.exists("Role", "Shop Owner (GST)"):
        role = frappe.get_doc({
            "doctype": "Role",
            "role_name": "Shop Owner (GST)",
            "desk_access": 1,
            "is_custom": 0,
            "is_system_role": 0,
            "home_page": "/app/gst-filing-assistant",
        })
        role.insert(ignore_permissions=True)
        print("✅ Patch: Created 'Shop Owner (GST)' role")
    else:
        print("⏭️ Patch: Role 'Shop Owner (GST)' already exists")


def create_filing_workspace():
    """
    Post-model-sync patch: Create/update the GST Filing Assistant workspace
    and hide standard ERPNext workspaces from Shop Owner role.
    
    Per README requirement: Consider hiding the standard ERPNext 
    Accounting/Selling workspaces from this user's role entirely so they 
    never see the full module complexity.
    """
    workspace_name = "GST Filing Assistant"
    
    # Create the simplified workspace
    _create_gst_workspace(workspace_name)
    
    # Hide standard ERPNext workspaces from Shop Owner role
    _hide_standard_workspaces()


def _create_gst_workspace(workspace_name):
    """Create the simplified GST Filing Assistant workspace."""
    if frappe.db.exists("Workspace", workspace_name):
        existing = frappe.get_doc("Workspace", workspace_name)
        existing.delete(ignore_permissions=True)
    
    workspace_data = {
        "doctype": "Workspace",
        "title": workspace_name,
        "module": "Micro GST Assist",
        "label": workspace_name,
        "category": "Modules",
        "icon": "fa fa-file-text",
        "is_hidden": 0,
        "description": "Your GST filing dashboard — only what you need to file on time",
        "public": 0,
        "sequence_id": 1,
        "roles": [
            {"role": "Shop Owner (GST)"},
            {"role": "System Manager"}
        ],
        "shortcuts": [
            {
                "label": "New Sale",
                "icon": "fa fa-plus-circle",
                "format": "Primary",
                "link_to": "simplified-invoice",
                "link_type": "Page",
                "description": "Create a new simplified invoice"
            },
            {
                "label": "Filing Checklist",
                "icon": "fa fa-check-square-o",
                "format": "Secondary",
                "link_to": "GST Filing Checklist",
                "link_type": "DocType",
                "description": "View current filing period checklist"
            },
            {
                "label": "Readiness Score",
                "icon": "fa fa-dashboard",
                "format": "Secondary",
                "link_to": "Filing Readiness Score",
                "link_type": "Report",
                "description": "Check readiness score"
            }
        ],
        "links": [
            {
                "type": "Link",
                "label": "Transactions",
                "icon": "fa fa-exchange",
                "links": [
                    {
                        "type": "Page",
                        "label": "New Sale (Simplified)",
                        "link_to": "simplified-invoice",
                        "onboard": 1,
                        "description": "Create invoices with only essential fields"
                    }
                ]
            },
            {
                "type": "Link",
                "label": "Filing Preparation",
                "icon": "fa fa-tasks",
                "links": [
                    {
                        "type": "DocType",
                        "label": "GST Filing Checklist",
                        "link_to": "GST Filing Checklist",
                        "onboard": 1,
                        "description": "Track your GST filing tasks and due dates"
                    }
                ]
            },
            {
                "type": "Link",
                "label": "Reports",
                "icon": "fa fa-bar-chart",
                "links": [
                    {
                        "type": "Report",
                        "label": "Filing Readiness Score",
                        "link_to": "Filing Readiness Score",
                        "is_query_report": True,
                        "onboard": 1,
                        "description": "Comprehensive readiness assessment"
                    },
                    {
                        "type": "Report",
                        "label": "GSTR-2B Mismatch Summary",
                        "link_to": "GSTR-2B Mismatch Summary",
                        "is_query_report": True,
                        "onboard": 1,
                        "description": "Vendor invoice mismatches in plain language"
                    },
                    {
                        "type": "Report",
                        "label": "Upcoming Filing Deadlines",
                        "link_to": "Upcoming Filing Deadlines",
                        "is_query_report": True,
                        "onboard": 1,
                        "description": "All upcoming deadlines sorted by due date"
                    }
                ]
            }
        ],
        "number_cards": [
            {
                "label": "Days to Filing Deadline",
                "type": "Number Card",
                "document_type": "GST Filing Checklist",
                "function": "Count",
                "stats_filter": "{\"status\":[\"!=\",\"Completed\"]}",
                "method": "micro_gst_assist.api.get_days_to_deadline",
            },
            {
                "label": "Pending Tasks",
                "type": "Number Card",
                "document_type": "GST Filing Checklist",
                "function": "Sum",
                "aggregate_function_based_on": "total_items",
                "stats_filter": "[]",
            }
        ]
    }
    
    workspace = frappe.get_doc(workspace_data)
    workspace.insert(ignore_permissions=True)
    print("✅ Patch: Created 'GST Filing Assistant' workspace")


def _hide_standard_workspaces():
    """
    Hide standard ERPNext Accounting, Selling, and Buying workspaces 
    from the Shop Owner (GST) role.
    
    Per README: "Consider hiding the standard ERPNext Accounting/Selling 
    workspaces from this user's role entirely so they never see the full 
    module complexity that caused the original problem."
    """
    standard_workspaces = [
        "Accounts", "Selling", "Buying", "Stock", 
        "CRM", "Manufacturing", "HR", "Projects",
        "Support", "Quality", "Assets", "Payroll",
        "Integrations", "Website", "Settings"
    ]
    
    shop_owner_role = "Shop Owner (GST)"
    
    for ws_name in standard_workspaces:
        if not frappe.db.exists("Workspace", ws_name):
            continue
        
        workspace = frappe.get_doc("Workspace", ws_name)
        
        # Check if the role is already in the workspace's roles
        role_assigned = False
        for role_entry in workspace.roles:
            if role_entry.role == shop_owner_role:
                role_assigned = True
                break
        
        # If the role is assigned, remove it (hide the workspace)
        if role_assigned:
            workspace.roles = [r for r in workspace.roles if r.role != shop_owner_role]
            workspace.save(ignore_permissions=True)
            print("✅ Patch: Removed '{0}' access to workspace '{1}'".format(
                shop_owner_role, ws_name))
    
    print("✅ Patch: Standard workspaces hidden from Shop Owner (GST) role")


def load_demo_fixtures():
    """
    Post-model-sync patch: Load demo fixtures from the notification directory.
    Creates the Filing Deadline Approaching, GSTR-2B Mismatch Found, 
    and Invoice Missing GST Fields notifications.
    """
    notification_files = [
        "filing_deadline_approaching",
        "gstr_2b_mismatch_found",
        "invoice_missing_gst_fields"
    ]
    
    for nf in notification_files:
        filepath = frappe.get_app_path("micro_gst_assist", "notification", "{0}.json".format(nf))
        if not os.path.exists(filepath):
            print("⚠️ Patch: Notification file not found: {0}".format(filepath))
            continue
        
        with open(filepath) as f:
            data = json.load(f)
            notification_name = data.get("name")
            
            if frappe.db.exists("Notification", notification_name):
                print("⏭️ Patch: Notification '{0}' already exists".format(notification_name))
                continue
            
            doc = frappe.get_doc(data)
            doc.insert(ignore_permissions=True)
            print("✅ Patch: Created notification '{0}'".format(notification_name))
    
    print("✅ Patch: Demo fixtures loaded successfully")
