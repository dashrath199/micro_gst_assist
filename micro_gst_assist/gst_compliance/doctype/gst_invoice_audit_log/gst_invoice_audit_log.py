# Copyright (c) 2026, Bizaxl and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class GSTInvoiceAuditLog(Document):
    """
    GST Invoice Audit Log DocType.
    
    Tracks GST compliance status of each Sales Invoice.
    Stores HSN codes, GST rates, tax breakdown per invoice, and any validation errors.
    Used by the Filing Readiness Score and GSTR-2B Mismatch report.
    """
    
    def validate(self):
        """Validate the audit log data."""
        self._compute_total_tax()
        
        if self.gst_status == "Mismatch" and not self.errors:
            frappe.msgprint(
                _("Please provide error details for mismatch status."),
                indicator="orange"
            )
    
    def _compute_total_tax(self):
        """Auto-compute total tax from CGST + SGST + IGST."""
        self.total_tax = (self.cgst or 0) + (self.sgst or 0) + (self.igst or 0)
    
    def mark_resolved(self, notes=None):
        """Mark this audit log entry as resolved."""
        self.resolved = 1
        self.resolved_on = frappe.utils.now()
        if notes:
            self.resolution_notes = notes
        self.save(ignore_permissions=True)
    
    @staticmethod
    def get_mismatches(company=None, period=None):
        """
        Get all unresolved mismatch audit logs.
        
        Args:
            company (str, optional): Filter by company
            period (str, optional): Filing period filter
        
        Returns:
            list: Mismatch audit log entries with invoice details
        """
        filters = {
            "gst_status": "Mismatch",
            "resolved": 0
        }
        if company:
            filters["company"] = company
        
        mismatches = frappe.get_all(
            "GST Invoice Audit Log",
            filters=filters,
            fields=["name", "sales_invoice", "hsn_code", "gst_rate",
                    "taxable_value", "errors", "audit_date", "company"],
            order_by="audit_date DESC"
        )
        
        # Enrich with customer/supplier info
        for m in mismatches:
            inv = frappe.db.get_value(
                "Sales Invoice", m.sales_invoice,
                ["customer", "posting_date", "grand_total"], as_dict=True
            )
            if inv:
                m.update(inv)
        
        return mismatches
    
    @staticmethod
    def get_daily_summary(company=None, date=None):
        """
        Get a summary of GST audit results for a specific day.
        
        Args:
            company (str, optional): Filter by company
            date (str, optional): Date string; defaults to today
        
        Returns:
            dict: Summary statistics
        """
        from frappe.utils import nowdate, getdate
        
        audit_date = date or nowdate()
        filters = [{"audit_date": ["between", [audit_date + " 00:00:00", audit_date + " 23:59:59"]]}]
        
        if company:
            filters.append({"company": company})
        
        audits = frappe.get_all(
            "GST Invoice Audit Log",
            filters=filters,
            fields=["gst_status", "count(*) as count"],
            group_by="gst_status"
        )
        
        summary = {"Valid": 0, "Missing HSN": 0, "Missing GST Rate": 0, "Mismatch": 0}
        for row in audits:
            summary[row.gst_status] = row.count
        
        return summary
