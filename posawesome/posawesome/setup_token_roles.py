# -*- coding: utf-8 -*-
# Copyright (c) 2025, POS Awesome and contributors
# For license information, please see license.txt

"""
Setup script for Token-Based POS System

This script creates:
1. POS Sales Associate Role - For order counter staff
2. POS Cashier Role - For payment counter staff  
3. Role Profiles for easy user assignment
"""

import frappe
from frappe import _


def setup_token_system_roles():
    """Create roles and role profiles for token-based POS system"""
    
    # Create POS Sales Associate Role
    create_role_if_not_exists(
        role_name="POS Sales Associate",
        desk_access=1,
        home_page="/app/pos-awesome"
    )
    
    # Create POS Cashier Role
    create_role_if_not_exists(
        role_name="POS Cashier",
        desk_access=1,
        home_page="/app/pos-awesome"
    )
    
    # Set up permissions for POS Sales Associate
    setup_sales_associate_permissions()
    
    # Set up permissions for POS Cashier
    setup_cashier_permissions()
    
    # Create Role Profiles
    create_role_profile_if_not_exists(
        profile_name="POS Sales Associate Profile",
        roles=["POS Sales Associate"]
    )
    
    create_role_profile_if_not_exists(
        profile_name="POS Cashier Profile",
        roles=["POS Cashier"]
    )
    
    frappe.db.commit()
    print("Token system roles and profiles created successfully!")


def create_role_if_not_exists(role_name, desk_access=1, home_page=""):
    """Create a role if it doesn't exist"""
    if not frappe.db.exists("Role", role_name):
        role = frappe.get_doc({
            "doctype": "Role",
            "role_name": role_name,
            "desk_access": desk_access,
            "home_page": home_page,
            "is_custom": 1
        })
        role.insert(ignore_permissions=True)
        print(f"Created role: {role_name}")
    else:
        print(f"Role already exists: {role_name}")


def create_role_profile_if_not_exists(profile_name, roles):
    """Create a role profile if it doesn't exist"""
    if not frappe.db.exists("Role Profile", profile_name):
        profile = frappe.get_doc({
            "doctype": "Role Profile",
            "role_profile": profile_name
        })
        for role in roles:
            profile.append("roles", {"role": role})
        profile.insert(ignore_permissions=True)
        print(f"Created role profile: {profile_name}")
    else:
        print(f"Role profile already exists: {profile_name}")


def setup_sales_associate_permissions():
    """
    POS Sales Associate Permissions:
    - Can READ: Customer, Item, POS Profile, Item Group, Item Price, Batch, UOM
    - Can CREATE: Customer (for new walk-in customers), POS Token
    - Can READ/WRITE: POS Token (only their own)
    - CANNOT: Create Sales Invoice, Access Payments
    """
    
    permissions = [
        # Customer - Read and Create (for new customers)
        {"doctype": "Customer", "role": "POS Sales Associate", "permlevel": 0, 
         "read": 1, "write": 0, "create": 1, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 0, "export": 0, "import": 0, "share": 0, "print": 1, "email": 0},
        
        # Item - Read only
        {"doctype": "Item", "role": "POS Sales Associate", "permlevel": 0,
         "read": 1, "write": 0, "create": 0, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 0, "export": 0, "import": 0, "share": 0, "print": 0, "email": 0},
        
        # POS Profile - Read only
        {"doctype": "POS Profile", "role": "POS Sales Associate", "permlevel": 0,
         "read": 1, "write": 0, "create": 0, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 0, "export": 0, "import": 0, "share": 0, "print": 0, "email": 0},
        
        # POS Opening Shift - Read only
        {"doctype": "POS Opening Shift", "role": "POS Sales Associate", "permlevel": 0,
         "read": 1, "write": 0, "create": 0, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 0, "export": 0, "import": 0, "share": 0, "print": 0, "email": 0},
        
        # POS Token - Full access (create, read, write own tokens)
        {"doctype": "POS Token", "role": "POS Sales Associate", "permlevel": 0,
         "read": 1, "write": 1, "create": 1, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 1, "export": 0, "import": 0, "share": 0, "print": 1, "email": 0},
        
        # Item Group - Read only
        {"doctype": "Item Group", "role": "POS Sales Associate", "permlevel": 0,
         "read": 1, "write": 0, "create": 0, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 0, "export": 0, "import": 0, "share": 0, "print": 0, "email": 0},
        
        # Item Price - Read only
        {"doctype": "Item Price", "role": "POS Sales Associate", "permlevel": 0,
         "read": 1, "write": 0, "create": 0, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 0, "export": 0, "import": 0, "share": 0, "print": 0, "email": 0},
        
        # Batch - Read only
        {"doctype": "Batch", "role": "POS Sales Associate", "permlevel": 0,
         "read": 1, "write": 0, "create": 0, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 0, "export": 0, "import": 0, "share": 0, "print": 0, "email": 0},
        
        # UOM - Read only
        {"doctype": "UOM", "role": "POS Sales Associate", "permlevel": 0,
         "read": 1, "write": 0, "create": 0, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 0, "export": 0, "import": 0, "share": 0, "print": 0, "email": 0},
        
        # Brand - Read only
        {"doctype": "Brand", "role": "POS Sales Associate", "permlevel": 0,
         "read": 1, "write": 0, "create": 0, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 0, "export": 0, "import": 0, "share": 0, "print": 0, "email": 0},
        
        # Address - Read and Create
        {"doctype": "Address", "role": "POS Sales Associate", "permlevel": 0,
         "read": 1, "write": 1, "create": 1, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 0, "export": 0, "import": 0, "share": 0, "print": 0, "email": 0},
        
        # Contact - Read and Create
        {"doctype": "Contact", "role": "POS Sales Associate", "permlevel": 0,
         "read": 1, "write": 1, "create": 1, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 0, "export": 0, "import": 0, "share": 0, "print": 0, "email": 0},
        
        # Sales Person - Read only (for commission)
        {"doctype": "Sales Person", "role": "POS Sales Associate", "permlevel": 0,
         "read": 1, "write": 0, "create": 0, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 0, "export": 0, "import": 0, "share": 0, "print": 0, "email": 0},
    ]
    
    create_permissions(permissions)


def setup_cashier_permissions():
    """
    POS Cashier Permissions:
    - Can READ: Customer, Item, POS Profile, POS Token, Item Group, etc.
    - Can CREATE: Sales Invoice (via POS)
    - Can UPDATE: POS Token (mark as paid)
    - Full payment processing capabilities
    """
    
    permissions = [
        # Customer - Read only
        {"doctype": "Customer", "role": "POS Cashier", "permlevel": 0,
         "read": 1, "write": 0, "create": 0, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 0, "export": 0, "import": 0, "share": 0, "print": 1, "email": 0},
        
        # Item - Read only
        {"doctype": "Item", "role": "POS Cashier", "permlevel": 0,
         "read": 1, "write": 0, "create": 0, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 0, "export": 0, "import": 0, "share": 0, "print": 0, "email": 0},
        
        # POS Profile - Read only
        {"doctype": "POS Profile", "role": "POS Cashier", "permlevel": 0,
         "read": 1, "write": 0, "create": 0, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 0, "export": 0, "import": 0, "share": 0, "print": 0, "email": 0},
        
        # POS Opening Shift - Read and Create (to open their shift)
        {"doctype": "POS Opening Shift", "role": "POS Cashier", "permlevel": 0,
         "read": 1, "write": 1, "create": 1, "delete": 0, "submit": 1, "cancel": 0,
         "amend": 0, "report": 1, "export": 0, "import": 0, "share": 0, "print": 1, "email": 0},
        
        # POS Closing Shift - Read and Create
        {"doctype": "POS Closing Shift", "role": "POS Cashier", "permlevel": 0,
         "read": 1, "write": 1, "create": 1, "delete": 0, "submit": 1, "cancel": 0,
         "amend": 0, "report": 1, "export": 0, "import": 0, "share": 0, "print": 1, "email": 0},
        
        # POS Token - Read and Update (to mark as paid)
        {"doctype": "POS Token", "role": "POS Cashier", "permlevel": 0,
         "read": 1, "write": 1, "create": 0, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 1, "export": 0, "import": 0, "share": 0, "print": 1, "email": 0},
        
        # Sales Invoice - Full POS access
        {"doctype": "Sales Invoice", "role": "POS Cashier", "permlevel": 0,
         "read": 1, "write": 1, "create": 1, "delete": 0, "submit": 1, "cancel": 0,
         "amend": 0, "report": 1, "export": 0, "import": 0, "share": 0, "print": 1, "email": 1},
        
        # Mode of Payment - Read only
        {"doctype": "Mode of Payment", "role": "POS Cashier", "permlevel": 0,
         "read": 1, "write": 0, "create": 0, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 0, "export": 0, "import": 0, "share": 0, "print": 0, "email": 0},
        
        # Item Group - Read only
        {"doctype": "Item Group", "role": "POS Cashier", "permlevel": 0,
         "read": 1, "write": 0, "create": 0, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 0, "export": 0, "import": 0, "share": 0, "print": 0, "email": 0},
        
        # Item Price - Read only
        {"doctype": "Item Price", "role": "POS Cashier", "permlevel": 0,
         "read": 1, "write": 0, "create": 0, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 0, "export": 0, "import": 0, "share": 0, "print": 0, "email": 0},
        
        # Batch - Read only
        {"doctype": "Batch", "role": "POS Cashier", "permlevel": 0,
         "read": 1, "write": 0, "create": 0, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 0, "export": 0, "import": 0, "share": 0, "print": 0, "email": 0},
        
        # UOM - Read only
        {"doctype": "UOM", "role": "POS Cashier", "permlevel": 0,
         "read": 1, "write": 0, "create": 0, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 0, "export": 0, "import": 0, "share": 0, "print": 0, "email": 0},
        
        # Brand - Read only
        {"doctype": "Brand", "role": "POS Cashier", "permlevel": 0,
         "read": 1, "write": 0, "create": 0, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 0, "export": 0, "import": 0, "share": 0, "print": 0, "email": 0},
        
        # Account - Read only (for payment)
        {"doctype": "Account", "role": "POS Cashier", "permlevel": 0,
         "read": 1, "write": 0, "create": 0, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 0, "export": 0, "import": 0, "share": 0, "print": 0, "email": 0},
        
        # Company - Read only
        {"doctype": "Company", "role": "POS Cashier", "permlevel": 0,
         "read": 1, "write": 0, "create": 0, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 0, "export": 0, "import": 0, "share": 0, "print": 0, "email": 0},
         
        # Sales Person - Read only (for commission)
        {"doctype": "Sales Person", "role": "POS Cashier", "permlevel": 0,
         "read": 1, "write": 0, "create": 0, "delete": 0, "submit": 0, "cancel": 0,
         "amend": 0, "report": 0, "export": 0, "import": 0, "share": 0, "print": 0, "email": 0},
    ]
    
    create_permissions(permissions)


def create_permissions(permissions):
    """Create custom docperm entries"""
    for perm in permissions:
        # Check if permission already exists
        existing = frappe.db.exists("Custom DocPerm", {
            "parent": perm["doctype"],
            "role": perm["role"],
            "permlevel": perm.get("permlevel", 0)
        })
        
        if not existing:
            doc = frappe.get_doc({
                "doctype": "Custom DocPerm",
                "parent": perm["doctype"],
                "parenttype": "DocType",
                "parentfield": "permissions",
                "role": perm["role"],
                "permlevel": perm.get("permlevel", 0),
                "read": perm.get("read", 0),
                "write": perm.get("write", 0),
                "create": perm.get("create", 0),
                "delete": perm.get("delete", 0),
                "submit": perm.get("submit", 0),
                "cancel": perm.get("cancel", 0),
                "amend": perm.get("amend", 0),
                "report": perm.get("report", 0),
                "export": perm.get("export", 0),
                "import": perm.get("import", 0),
                "share": perm.get("share", 0),
                "print": perm.get("print", 0),
                "email": perm.get("email", 0)
            })
            doc.insert(ignore_permissions=True)
            print(f"Created permission: {perm['doctype']} for {perm['role']}")


def execute():
    """Entry point for bench execute"""
    setup_token_system_roles()


if __name__ == "__main__":
    execute()
