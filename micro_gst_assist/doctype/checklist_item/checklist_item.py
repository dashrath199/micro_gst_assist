# Copyright (c) 2026, Bizaxl and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import nowdate, getdate


class ChecklistItem(Document):
    """
    Child DocType for GST Filing Checklist.
    
    Represents an individual task within a filing checklist.
    Each item has a status, due date, and optional reference
    to an external document (e.g., a Sales Invoice, GSTR-3B).
    """
    
    def validate(self):
        """Validate the checklist item data."""
        if self.status == "Completed" and not self.completed_on:
            self.completed_on = nowdate()
        
        if self.completed_on and self.status != "Completed":
            self.completed_on = None
        
        # Reference validation
        if self.reference_name and not self.reference_type:
            frappe.msgprint(
                _("Please set the Reference Type when providing a Reference Name."),
                indicator="orange"
            )
    
    def mark_completed(self):
        """Helper to mark this item as completed."""
        self.status = "Completed"
        self.completed_on = nowdate()
        self.save()
