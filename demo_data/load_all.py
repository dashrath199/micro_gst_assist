# micro_gst_assist - Demo Data Loader
# Run this via bench console or command line to load demo data:
#   bench --site yoursite.local execute micro_gst_assist.demo_data.load_all.run

import frappe
from frappe import _
from frappe.utils import nowdate
import json
import os


def run():
    """
    Main entry point. Loads all demo data for testing the GST Filing Assistant.
    
    Usage:
        bench --site yoursite.local execute micro_gst_assist.demo_data.load_all.run
    """
    print("=" * 60)
    print("Loading Demo Data for Micro GST Assist")
    print("=" * 60)
    
    # Step 1: Create Shop Owner (GST) role
    create_role()
    
    # Step 2: Create demo company if not exists
    company = create_company()
    
    # Step 3: Create demo customers
    create_customers()
    
    # Step 4: Create demo items
    create_items()
    
    # Step 5: Create demo GST Filing Checklists
    create_checklists()
    
    # Step 6: Create demo GST Invoice Audit Logs
    create_audit_logs()
    
    # Step 7: Create demo reminder logs
    create_reminder_logs()
    
    # Step 8: Create demo invoices (if needed for audit logs)
    create_demo_invoices(company)
    
    print("=" * 60)
    print("Demo data loading completed successfully!")
    print("=" * 60)


def create_role():
    """Create the Shop Owner (GST) role if it doesn't exist."""
    if not frappe.db.exists("Role", "Shop Owner (GST)"):
        role = frappe.get_doc({
            "doctype": "Role",
            "role_name": "Shop Owner (GST)",
            "desk_access": 1,
            "is_custom": 0,
            "is_system_role": 0,
            "home_page": "/app/gst-filing-assistant"
        })
        role.insert(ignore_permissions=True)
        print("✅ Created role: Shop Owner (GST)")
    else:
        print("⏭️  Role already exists: Shop Owner (GST)")


def create_company():
    """Create demo company."""
    company_name = "Sharma Kirana Store (GST)"
    
    if frappe.db.exists("Company", company_name):
        print("⏭️  Company already exists:", company_name)
        return frappe.get_doc("Company", company_name)
    
    company = frappe.get_doc({
        "doctype": "Company",
        "company_name": company_name,
        "abbr": "SKS",
        "default_currency": "INR",
        "country": "India",
        "gstin": "27AABCU1234D1Z5",
        "pan": "AABCU1234D",
        "gst_category": "Regular",
        "domain": "Retail",
        "date_of_incorporation": "2019-04-01",
        "enable_perpetual_inventory": 0,
    })
    company.insert(ignore_permissions=True)
    print("✅ Created company:", company_name)
    return company


def create_customers():
    """Create demo customers with various GST profiles."""
    customers = [
        {
            "customer_name": "Priya Electronics (B2B)",
            "customer_type": "Company",
            "gst_category": "Registered Regular",
            "gstin": "27AAPFP1234E1Z1",
            "pan": "AAPFP1234E",
        },
        {
            "customer_name": "Ramesh General Store (B2C)",
            "customer_type": "Individual",
            "gst_category": "Unregistered",
            "gstin": "",
            "pan": "",
        },
        {
            "customer_name": "Gupta Wholesale Traders (B2B)",
            "customer_type": "Company",
            "gst_category": "Registered Regular",
            "gstin": "07AABCU1234H1Z1",
            "pan": "AABCU1234H",
        },
        {
            "customer_name": "Verma Stationery (B2C)",
            "customer_type": "Individual",
            "gst_category": "Consumer",
            "gstin": "",
            "pan": "",
        },
        {
            "customer_name": "Desi Foods Restaurant (B2B)",
            "customer_type": "Company",
            "gst_category": "Registered Regular",
            "gstin": "27AAFFD1234G1Z1",
            "pan": "AAFFD1234G",
        },
    ]
    
    for c in customers:
        if frappe.db.exists("Customer", c["customer_name"]):
            print("⏭️  Customer already exists:", c["customer_name"])
            continue
        
        doc = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": c["customer_name"],
            "customer_type": c["customer_type"],
            "customer_group": "All Customer Groups",
            "territory": "India",
            "gst_category": c["gst_category"],
            "gstin": c["gstin"],
            "pan": c.get("pan", ""),
            "default_currency": "INR",
            "default_price_list": "Standard Selling",
        })
        doc.insert(ignore_permissions=True)
        print("✅ Created customer:", c["customer_name"])


def create_items():
    """Create demo items with GST HSN codes and rates."""
    items = [
        {"item_code": "WHEAT-FLOUR-1KG", "item_name": "Wheat Flour (Atta) - 1kg Pack",
         "gst_hsn_code": "1101", "gst_rate": 0, "item_group": "Grocery", "rate": 35.00},
        {"item_code": "SUGAR-1KG", "item_name": "Refined Sugar - 1kg Pack",
         "gst_hsn_code": "1701", "gst_rate": 5, "item_group": "Grocery", "rate": 42.00},
        {"item_code": "COOKING-OIL-1L", "item_name": "Mustard Cooking Oil - 1L",
         "gst_hsn_code": "1514", "gst_rate": 5, "item_group": "Grocery", "rate": 185.00},
        {"item_code": "RICE-BASMATI-5KG", "item_name": "Basmati Rice - 5kg Bag",
         "gst_hsn_code": "1006", "gst_rate": 5, "item_group": "Grocery", "rate": 525.00},
        {"item_code": "BISCUITS-200G", "item_name": "Assorted Biscuits - 200g",
         "gst_hsn_code": "1905", "gst_rate": 18, "item_group": "Snacks", "rate": 30.00},
        {"item_code": "SOAP-BATH-100G", "item_name": "Bath Soap - 100g Bar",
         "gst_hsn_code": "3401", "gst_rate": 18, "item_group": "Personal Care", "rate": 45.00},
        {"item_code": "COLD-DRINK-250ML", "item_name": "Cold Drink - 250ml Can",
         "gst_hsn_code": "2202", "gst_rate": 28, "item_group": "Beverages", "rate": 25.00},
        {"item_code": "NOTEBOOK-172P", "item_name": "Notebook - 172 Pages (A4)",
         "gst_hsn_code": "4820", "gst_rate": 12, "item_group": "Stationery", "rate": 85.00},
    ]
    
    for item in items:
        if frappe.db.exists("Item", item["item_code"]):
            print("⏭️  Item already exists:", item["item_code"])
            continue
        
        doc = frappe.get_doc({
            "doctype": "Item",
            "item_code": item["item_code"],
            "item_name": item["item_name"],
            "item_group": item["item_group"],
            "stock_uom": "Nos",
            "gst_hsn_code": item["gst_hsn_code"],
            "gst_rate": item["gst_rate"],
            "is_stock_item": 1,
            "has_variants": 0,
            "disabled": 0,
            "valuation_method": "FIFO",
            "opening_stock": 50,
            "standard_rate": item["rate"],
        })
        doc.insert(ignore_permissions=True)
        print("✅ Created item:", item["item_code"])


def create_checklists():
    """Create demo GST Filing Checklists with full item data."""
    # Checklist 1: Monthly, Regular scheme
    checklist1_name = "Jul 2026 - Sharma Kirana Store (GST)"
    
    if not frappe.db.exists("GST Filing Checklist", checklist1_name):
        checklist1 = frappe.get_doc({
            "doctype": "GST Filing Checklist",
            "gst_filing_checklist_name": checklist1_name,
            "filing_period": "Jul 2026",
            "filing_frequency": "Monthly",
            "composition_scheme": 0,
            "company": "Sharma Kirana Store (GST)",
            "due_date": "2026-08-20",
            "status": "In Progress",
            "remarks": "Waiting for 3 vendor invoices to be reconciled.",
            "items": [
                {"task": "Reconcile sales invoices with GSTR-1",
                 "status": "Completed", "due_date": "2026-08-18",
                 "completed_on": "2026-08-15", "completed_by": "Owner",
                 "notes": "All 15 invoices matched."},
                {"task": "Verify all B2B e-Invoices generated",
                 "status": "Completed", "due_date": "2026-08-18",
                 "completed_on": "2026-08-16", "completed_by": "Owner",
                 "notes": "12 e-Invoices generated."},
                {"task": "Reconcile GSTR-2B with purchase register",
                 "status": "In Progress", "due_date": "2026-08-19",
                 "notes": "3 mismatches with supplier invoices."},
                {"task": "Check ITC eligibility for all purchases",
                 "status": "Pending", "due_date": "2026-08-19"},
                {"task": "File monthly GSTR-3B",
                 "status": "Pending", "due_date": "2026-08-20"},
                {"task": "File monthly GSTR-1",
                 "status": "Pending", "due_date": "2026-08-20"},
                {"task": "Make GST payment (Cash ledger)",
                 "status": "Pending", "due_date": "2026-08-20",
                 "notes": "Estimated: ₹12,500"},
                {"task": "Claim ITC in GSTR-3B",
                 "status": "Pending", "due_date": "2026-08-20",
                 "notes": "ITC eligible: ~₹8,200"},
            ]
        })
        checklist1.insert(ignore_permissions=True)
        print("✅ Created checklist:", checklist1_name)
    else:
        print("⏭️  Checklist already exists:", checklist1_name)
    
    # Checklist 2: Quarterly, Composition scheme
    checklist2_name = "Q2 2026 (Jul-Sep) - Sharma Kirana Store (GST)"
    
    if not frappe.db.exists("GST Filing Checklist", checklist2_name):
        checklist2 = frappe.get_doc({
            "doctype": "GST Filing Checklist",
            "gst_filing_checklist_name": checklist2_name,
            "filing_period": "Q2 2026 (Jul-Sep)",
            "filing_frequency": "Quarterly (QRMP)",
            "composition_scheme": 1,
            "company": "Sharma Kirana Store (GST)",
            "due_date": "2026-10-20",
            "status": "Draft",
            "remarks": "First quarter under composition scheme.",
            "items": [
                {"task": "Reconcile sales invoices with GSTR-1",
                 "status": "Pending", "due_date": "2026-10-18"},
                {"task": "Pay monthly PMT-06 challan (July)",
                 "status": "Completed", "due_date": "2026-08-20",
                 "completed_on": "2026-08-19", "completed_by": "Owner",
                 "notes": "Paid ₹4,200"},
                {"task": "Pay monthly PMT-06 challan (August)",
                 "status": "Completed", "due_date": "2026-09-20",
                 "completed_on": "2026-09-18", "completed_by": "Owner",
                 "notes": "Paid ₹3,800"},
                {"task": "Pay monthly PMT-06 challan (September)",
                 "status": "Pending", "due_date": "2026-10-20"},
                {"task": "File quarterly GSTR-4 (Composition)",
                 "status": "Pending", "due_date": "2026-10-20",
                 "notes": "First-time filing under composition."},
                {"task": "Pay composition tax liability",
                 "status": "Pending", "due_date": "2026-10-20",
                 "notes": "Estimated: 1% of turnover ≈ ₹4,500"},
            ]
        })
        checklist2.insert(ignore_permissions=True)
        print("✅ Created checklist:", checklist2_name)
    else:
        print("⏭️  Checklist already exists:", checklist2_name)


def create_audit_logs():
    """Create demo GST Invoice Audit Log entries."""
    audit_data = [
        {
            "sales_invoice": "SINV-2026-00001",
            "audit_date": "2026-07-14 10:30:00",
            "gst_status": "Valid",
            "hsn_code": "1101",
            "gst_rate": 0.0,
            "taxable_value": 350.00,
            "cgst": 0.0, "sgst": 0.0, "igst": 0.0,
            "resolved": 1
        },
        {
            "sales_invoice": "SINV-2026-00002",
            "audit_date": "2026-07-14 11:45:00",
            "gst_status": "Valid",
            "hsn_code": "1701",
            "gst_rate": 5.0,
            "taxable_value": 420.00,
            "cgst": 10.50, "sgst": 10.50, "igst": 0.0,
            "resolved": 1
        },
        {
            "sales_invoice": "SINV-2026-00003",
            "audit_date": "2026-07-15 09:15:00",
            "gst_status": "Missing HSN",
            "hsn_code": "",
            "gst_rate": 18.0,
            "taxable_value": 540.00,
            "cgst": 48.60, "sgst": 48.60, "igst": 0.0,
            "errors": "Items missing HSN codes",
            "resolved": 0
        },
        {
            "sales_invoice": "SINV-2026-00004",
            "audit_date": "2026-07-15 14:20:00",
            "gst_status": "Mismatch",
            "hsn_code": "1514",
            "gst_rate": 5.0,
            "taxable_value": 1850.00,
            "cgst": 46.25, "sgst": 46.25, "igst": 0.0,
            "errors": "GSTR-2B shows different taxable value",
            "resolved": 0
        },
        {
            "sales_invoice": "SINV-2026-00005",
            "audit_date": "2026-07-16 10:00:00",
            "gst_status": "Valid",
            "hsn_code": "1905",
            "gst_rate": 18.0,
            "taxable_value": 1500.00,
            "cgst": 135.00, "sgst": 135.00, "igst": 0.0,
            "has_e_invoice": 1,
            "e_invoice_status": "Generated (IRN: 27AABCU1234D1Z5-2026-07-16-001)",
            "resolved": 1
        },
        {
            "sales_invoice": "SINV-2026-00006",
            "audit_date": "2026-07-16 15:30:00",
            "gst_status": "Missing GST Rate",
            "hsn_code": "3401",
            "gst_rate": 0.0,
            "taxable_value": 900.00,
            "cgst": 0.0, "sgst": 0.0, "igst": 0.0,
            "errors": "HSN 3401 expects 18% GST, found 0%",
            "resolved": 0
        },
        {
            "sales_invoice": "SINV-2026-00007",
            "audit_date": "2026-07-17 11:00:00",
            "gst_status": "Valid",
            "hsn_code": "1006",
            "gst_rate": 5.0,
            "taxable_value": 2625.00,
            "cgst": 65.63, "sgst": 65.63, "igst": 0.0,
            "has_e_invoice": 1,
            "e_invoice_status": "Generated (IRN: 27AABCU1234D1Z5-2026-07-17-002)",
            "resolved": 1
        },
        {
            "sales_invoice": "SINV-2026-00008",
            "audit_date": "2026-07-17 16:45:00",
            "gst_status": "Mismatch",
            "hsn_code": "2202",
            "gst_rate": 28.0,
            "taxable_value": 750.00,
            "cgst": 105.00, "sgst": 105.00, "igst": 0.0,
            "errors": "e-Way Bill not generated for inter-state sale",
            "resolved": 0
        },
    ]
    
    for audit in audit_data:
        sales_invoice = audit["sales_invoice"]
        if frappe.db.exists("GST Invoice Audit Log", {"sales_invoice": sales_invoice}):
            print("⏭️  Audit log already exists for:", sales_invoice)
            continue
        
        doc = frappe.get_doc({
            "doctype": "GST Invoice Audit Log",
            "company": "Sharma Kirana Store (GST)",
            **audit
        })
        doc.insert(ignore_permissions=True)
        print("✅ Created audit log for:", sales_invoice)


def create_reminder_logs():
    """Create demo GST Filing Reminder Log entries."""
    reminders = [
        {
            "checklist": "Jul 2026 - Sharma Kirana Store (GST)",
            "reminder_type": "Deadline Approaching",
            "urgency": "WARNING",
            "recipient": "owner@sharmakirana.in",
            "channel": "System Notification",
            "sent_at": "2026-07-18 08:00:00",
            "delivered_at": "2026-07-18 08:00:05",
            "status": "Delivered",
            "message": "GST Filing Due in 2 Days - Jul 2026. Pending: 7 tasks."
        },
        {
            "checklist": "Jul 2026 - Sharma Kirana Store (GST)",
            "reminder_type": "Mismatch Found",
            "urgency": "CRITICAL",
            "recipient": "owner@sharmakirana.in",
            "channel": "System Notification",
            "sent_at": "2026-07-19 06:00:00",
            "delivered_at": "2026-07-19 06:00:02",
            "status": "Delivered",
            "message": "GSTR-2B Mismatch Alert - 2 unmatched invoices found."
        },
    ]
    
    for r in reminders:
        doc = frappe.get_doc({
            "doctype": "GST Filing Reminder Log",
            **r
        })
        doc.insert(ignore_permissions=True)
        print("✅ Created reminder log:", r["reminder_type"], "-", r["checklist"])


def create_demo_invoices(company):
    """Create demo Sales Invoices for testing."""
    invoices = [
        {
            "customer": "Priya Electronics (B2B)",
            "posting_date": "2026-07-14",
            "items": [{"item_code": "WHEAT-FLOUR-1KG", "qty": 10, "rate": 35.00}],
        },
        {
            "customer": "Gupta Wholesale Traders (B2B)",
            "posting_date": "2026-07-14",
            "items": [
                {"item_code": "SUGAR-1KG", "qty": 20, "rate": 38.00},
                {"item_code": "COOKING-OIL-1L", "qty": 10, "rate": 175.00},
            ],
        },
    ]
    
    company_name = company.company_name if hasattr(company, 'company_name') else "Sharma Kirana Store (GST)"
    
    for i, inv_data in enumerate(invoices, 1):
        inv_name = f"SINV-2026-{i:05d}"
        if frappe.db.exists("Sales Invoice", inv_name):
            print("⏭️  Sales Invoice already exists:", inv_name)
            continue
        
        si = frappe.get_doc({
            "doctype": "Sales Invoice",
            "customer": inv_data["customer"],
            "posting_date": inv_data["posting_date"],
            "due_date": inv_data["posting_date"],
            "company": company_name,
            "currency": "INR",
            "set_warehouse": "Stores - SKS",
        })
        
        for item in inv_data["items"]:
            item_doc = frappe.get_doc("Item", item["item_code"])
            si.append("items", {
                "item_code": item["item_code"],
                "qty": item["qty"],
                "rate": item["rate"],
                "gst_hsn_code": item_doc.gst_hsn_code,
                "gst_rate": item_doc.gst_rate,
            })
        
        si.insert(ignore_permissions=True)
        print("✅ Created Sales Invoice:", inv_name)
