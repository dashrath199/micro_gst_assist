# micro_gst_assist - Desktop Configuration

from frappe import _

def get_data():
    """Returns app-level desktop data for the GST Filing Assistant."""
    return {
        "category": "Modules",
        "label": _("Micro GST Assist"),
        "icon": "octicon octicon-repo",
        "type": "module",
        "name": "Micro GST Assist",
        "description": _("GST Compliance Automation for Micro-Enterprises"),
        "color": "#24963E",
        "_doctype": "Micro GST Assist",
        "module_name": "Micro GST Assist",
        "link_type": "Module",
        "onboard": 1,
        "items": [
            {
                "type": "doctype",
                "name": "GST Filing Checklist",
                "label": _("GST Filing Checklist"),
                "description": _("Manage your GST filing tasks and due dates"),
                "onboard": 1,
                "dependencies": ["India Compliance"]
            },
            {
                "type": "page",
                "name": "simplified-invoice",
                "label": _("New Sale (Simplified)"),
                "description": _("Create a sales invoice with only essential fields"),
                "onboard": 1
            },
            {
                "type": "report",
                "name": "Filing Readiness Score",
                "label": _("Filing Readiness Score"),
                "description": _("Check if your GST data is ready for filing"),
                "onboard": 1,
                "is_query_report": True,
                "doctype": "GST Filing Checklist"
            },
            {
                "type": "report",
                "name": "GSTR-2B Mismatch Summary",
                "label": _("GSTR-2B Mismatch Summary"),
                "description": _("View vendor invoice mismatches in plain language"),
                "onboard": 0,
                "is_query_report": True,
                "doctype": "Sales Invoice"
            },
            {
                "type": "report",
                "name": "Upcoming Filing Deadlines",
                "label": _("Upcoming Filing Deadlines"),
                "description": _("View upcoming GST filing deadlines"),
                "onboard": 1,
                "is_query_report": True,
                "doctype": "GST Filing Checklist"
            }
        ]
    }
