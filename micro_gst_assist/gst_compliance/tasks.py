# -*- coding: utf-8 -*-
"""
Scheduled background tasks for GST readiness scoring.
"""

import frappe
from frappe.utils import getdate, add_days, nowdate, date_diff

from micro_gst_assist.gst_compliance.utils import compute_readiness_score, get_period_dates


def generate_readiness_scores():
    """
    Daily long-running task. Calculates readiness scores for all active checklists.
    """
    checklists = frappe.get_all(
        "GST Filing Checklist",
        filters={"status": ["in", ["Draft", "In Progress"]]},
        fields=["name"],
    )
    for cl in checklists:
        try:
            doc = frappe.get_doc("GST Filing Checklist", cl.name)
            score = compute_readiness_score(doc)
            doc.db_set("custom_readiness_score", score, commit=True)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"GST Assist: scoring {cl.name} failed")
