# Copyright (c) 2026, Bizaxl and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class GSTFilingReminderLog(Document):
    """
    GST Filing Reminder Log DocType.
    
    Audit trail for all reminders sent to micro-enterprise shop owners.
    Tracks which reminders were sent, through which channel, and their status.
    Supports monitoring of delivery success across WhatsApp/SMS/System notifications.
    """
    
    def validate(self):
        """Validate the reminder log entry."""
        if self.channel in ("WhatsApp", "SMS") and not self.recipient:
            frappe.throw(_("Recipient is required for WhatsApp/SMS notifications"))
        
        if not self.sent_at:
            self.sent_at = frappe.utils.now()
    
    def mark_delivered(self):
        """Mark this reminder as delivered successfully."""
        self.status = "Delivered"
        self.save(ignore_permissions=True)
    
    def mark_failed(self, error_log=None):
        """Mark this reminder as failed with an error log."""
        self.status = "Failed"
        if error_log:
            self.error_log = str(error_log)
        self.save(ignore_permissions=True)
