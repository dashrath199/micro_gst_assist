app_name = "micro_gst_assist"
app_title = "GST Filing Assistant"
app_publisher = "Bizaxl"
app_description = "GST Compliance Automation for Micro-Enterprises (Sub-10-Employee)"
app_email = "info@bizaxl.com"
app_license = "GNU General Public License v3.0"

after_install = "micro_gst_assist.install.after_install"

# Document Events
doc_events = {
    "Sales Invoice": {
        "before_submit": "micro_gst_assist.gst_compliance.doctype.event_handlers.validate_gst_fields",
        "on_submit": "micro_gst_assist.gst_compliance.doctype.event_handlers.on_sales_invoice_submit",
    },
    "GST Filing Checklist": {
        "before_save": "micro_gst_assist.gst_compliance.doctype.event_handlers.update_checklist_counts",
    },
}

# Scheduled Tasks
scheduler_events = {
    "daily": [
        "micro_gst_assist.gst_compliance.notifications.send_filing_reminders",
    ],
    "hourly": [
        "micro_gst_assist.gst_compliance.notifications.send_mismatch_alerts",
    ],
    "daily_long": [
        "micro_gst_assist.gst_compliance.tasks.generate_readiness_scores",
    ],
}

# Permission query conditions
permission_query_conditions = {
    "GST Filing Checklist": "micro_gst_assist.gst_compliance.doctype.event_handlers.get_permission_query_conditions",
}

# Permissions
has_permission = {
    "GST Filing Checklist": "micro_gst_assist.gst_compliance.doctype.event_handlers.has_permission",
}
