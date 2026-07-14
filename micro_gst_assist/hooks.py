from . import __version__ as app_version

app_name = "micro_gst_assist"
app_title = "GST Filing Assistant"
app_publisher = "Bizaxl"
app_description = "GST Compliance Automation for Micro-Enterprises (Sub-10-Employee)"
app_email = "info@bizaxl.com"
app_license = "GNU General Public License v3.0"

# -----------------------------------------------
# DocType Classes
# -----------------------------------------------
doctype_js = {}
doctype_python = {
    "gst_filing_checklist": "micro_gst_assist.gst_compliance.doctype.gst_filing_checklist.gst_filing_checklist",
    "checklist_item": "micro_gst_assist.gst_compliance.doctype.checklist_item.checklist_item",
    "gst_filing_reminder_log": "micro_gst_assist.gst_compliance.doctype.gst_filing_reminder_log.gst_filing_reminder_log",
    "gst_invoice_audit_log": "micro_gst_assist.gst_compliance.doctype.gst_invoice_audit_log.gst_invoice_audit_log",
}

after_install = "micro_gst_assist.install.after_install"

# -----------------------------------------------
# Document Events
# -----------------------------------------------
doc_events = {
    "Sales Invoice": {
        "before_submit": "micro_gst_assist.gst_compliance.doctype.event_handlers.validate_gst_fields",
        "on_submit": "micro_gst_assist.gst_compliance.doctype.event_handlers.on_sales_invoice_submit",
    },
    "GST Filing Checklist": {
        "before_save": "micro_gst_assist.gst_compliance.doctype.event_handlers.update_checklist_counts",
    },
}

# -----------------------------------------------
# Scheduled Tasks
# -----------------------------------------------
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

# -----------------------------------------------
# Permissions
# -----------------------------------------------
permission_query_conditions = {
    "GST Filing Checklist": "micro_gst_assist.gst_compliance.doctype.event_handlers.get_permission_query_conditions",
}

has_permission = {
    "GST Filing Checklist": "micro_gst_assist.gst_compliance.doctype.event_handlers.has_permission",
}
