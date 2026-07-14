# micro_gst_assist - GST Compliance Automation for Micro-Enterprises
# ERPNext v15 Custom App - App Configuration

from . import __version__ as app_version

app_name = "micro_gst_assist"
app_title = "GST Filing Assistant"
app_publisher = "Bizaxl"
app_description = "GST Compliance Automation for Micro-Enterprises (Sub-10-Employee)"
app_email = "info@bizaxl.com"
app_license = "GNU General Public License v3.0"

# DocType Class Overrides
app_include_js = [
    "micro_gst_assist.bundle.js"
]

# Fixtures
fixtures = [
    {"dt": "Role", "filters": [["name", "in", ["Shop Owner (GST)"]]]},
    {"dt": "Workspace", "filters": [["name", "in", ["GST Filing Assistant"]]]},
    {"dt": "Notification", "filters": [["name", "in", [
        "Filing Deadline Approaching",
        "GSTR-2B Mismatch Found",
        "Invoice Missing GST Fields"
    ]]]},
]

# DocType definitions
doc_type_list = [
    "GST Filing Checklist",
    "Checklist Item",
    "GST Filing Reminder Log",
    "GST Invoice Audit Log"
]

# Modules
module_def = "Micro GST Assist"

# Document Events / Hooks
doc_events = {
    "Sales Invoice": {
        "before_submit": [
            "micro_gst_assist.hooks.validate_gst_fields"
        ],
        "on_submit": [
            "micro_gst_assist.hooks.on_sales_invoice_submit"
        ]
    },
    "GST Filing Checklist": {
        "before_save": [
            "micro_gst_assist.hooks.update_checklist_counts"
        ]
    }
}

# Scheduled Tasks
scheduler_events = {
    "daily": [
        "micro_gst_assist.tasks.check_upcoming_deadlines"
    ],
    "hourly": [
        "micro_gst_assist.tasks.sync_gstr_2b_mismatches"
    ],
    "daily_long": [
        "micro_gst_assist.tasks.generate_filing_readiness_scores"
    ]
}

# Permissions
permission_query_conditions = {
    "GST Filing Checklist": "micro_gst_assist.hooks.get_permission_query_conditions"
}

# Roles
has_permission = {
    "GST Filing Checklist": "micro_gst_assist.hooks.has_permission"
}
