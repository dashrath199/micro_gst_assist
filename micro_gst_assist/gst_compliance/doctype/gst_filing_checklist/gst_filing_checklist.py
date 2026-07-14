# Copyright (c) 2026, Bizaxl and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import nowdate, getdate, date_diff
from frappe.model.naming import make_autoname


class GSTFilingChecklist(Document):
    """
    GST Filing Checklist DocType.
    
    Tracks the status of all tasks required for a complete GST filing
    for a given filing period. Distinguishes between monthly and 
    quarterly (QRMP) filing schemes.
    """
    
    def before_save(self):
        """Auto-populate derived fields before saving."""
        if not self.filing_period and self.due_date:
            self.filing_period = self._generate_filing_period()
        
        self._update_item_counts()
        self._update_status_from_items()
    
    def after_insert(self):
        """Auto-populate default checklist items based on filing frequency."""
        self._populate_default_items()
    
    def validate(self):
        """Validate the checklist data."""
        if self.due_date and getdate(self.due_date) < getdate(nowdate()):
            frappe.msgprint(
                _("Warning: The due date for this filing period has passed."),
                indicator="red"
            )
        
        if self.composition_scheme and self.filing_frequency != "Quarterly (QRMP)":
            frappe.msgprint(
                _("Composition dealers are typically on Quarterly (QRMP) filing. "
                  "Please verify your filing frequency."),
                indicator="orange"
            )
    
    def _generate_filing_period(self):
        """Generate a filing period label from the due date."""
        month_names = {
            1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
            7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
        }
        due = getdate(self.due_date)
        # GST due dates are typically 20th of the next month
        # Return the previous month as the filing period
        prev_month = due.month - 1 if due.month > 1 else 12
        prev_year = due.year if due.month > 1 else due.year - 1
        return "{0} {1}".format(month_names.get(prev_month, "Jan"), prev_year)
    
    def _update_item_counts(self):
        """Update total and completed item counts."""
        if self.get("items"):
            self.total_items = len(self.items)
            self.completed_items = len([i for i in self.items if i.status == "Completed"])
        else:
            self.total_items = 0
            self.completed_items = 0
    
    def _update_status_from_items(self):
        """Auto-update the checklist header status based on child items."""
        if not self.get("items"):
            return
        
        all_completed = all(i.status == "Completed" for i in self.items)
        any_in_progress = any(i.status == "In Progress" for i in self.items)
        
        if all_completed:
            self.status = "Completed"
        elif any_in_progress:
            self.status = "In Progress"
        
        # Check if overdue
        if self.due_date and getdate(self.due_date) < getdate(nowdate()):
            if self.status != "Completed":
                self.status = "Overdue"
    
    def _populate_default_items(self):
        """
        Auto-populate standard checklist items based on the filing scheme.
        Different sets of tasks for monthly vs quarterly (QRMP) filers.
        """
        if self.get("items") and len(self.items) > 0:
            return  # Don't override existing items
        
        items = []
        
        # Common items for all filers
        common_items = [
            _("Reconcile sales invoices with GSTR-1"),
            _("Verify all B2B e-Invoices generated"),
            _("Reconcile purchase register with vendor invoices"),
            _("Verify HSN codes on all invoice items"),
            _("Reconcile GSTR-2B with purchase register"),
            _("Check ITC eligibility for all purchases"),
            _("Match payment vouchers with ITC claims"),
            _("Review GST rate applicability for all items"),
            _("Verify e-Way bills for all inter-state transactions"),
        ]
        
        for task in common_items:
            items.append({
                "task": task,
                "status": "Pending",
                "due_date": self.due_date,
            })
        
        # QRMP-specific items
        if self.filing_frequency == "Quarterly (QRMP)":
            items.extend([
                {"task": _("Pay monthly PMT-06 challan (first 2 months of quarter)"), 
                 "status": "Pending", "due_date": self.due_date},
                {"task": _("File quarterly GSTR-3B"), 
                 "status": "Pending", "due_date": self.due_date},
                {"task": _("File quarterly GSTR-1"), 
                 "status": "Pending", "due_date": self.due_date},
            ])
        else:
            items.extend([
                {"task": _("File monthly GSTR-3B"), 
                 "status": "Pending", "due_date": self.due_date},
                {"task": _("File monthly GSTR-1"), 
                 "status": "Pending", "due_date": self.due_date},
            ])
        
        # Composition scheme items
        if self.composition_scheme:
            items.extend([
                {"task": _("File quarterly GSTR-4 (Composition)"),
                 "status": "Pending", "due_date": self.due_date},
                {"task": _("Pay composition tax liability"),
                 "status": "Pending", "due_date": self.due_date},
            ])
        else:
            items.extend([
                {"task": _("Make GST payment (Cash ledger)"),
                 "status": "Pending", "due_date": self.due_date},
                {"task": _("Claim ITC in GSTR-3B"),
                 "status": "Pending", "due_date": self.due_date},
            ])
        
        for item_data in items:
            self.append("items", item_data)


def get_filing_readiness_score(checklist_name):
    """
    Utility function to get a checklist's readiness score.
    Used by reports and workspace widgets.
    """
    try:
        checklist = frappe.get_doc("GST Filing Checklist", checklist_name)
        total = max(checklist.total_items or 0, 1)
        completed = checklist.completed_items or 0
        score = round((completed / total) * 100)
        return min(score, 100)
    except Exception:
        return 0
