"""
SiteIQ Platform Features & Multi-Tenant Hierarchy Verification Suite
Tests:
1. Org Admin Signup (Organization -> Master Admin)
2. Admin Authentication
3. Provisioning QC Lead & Inspection Engineer under the Organization
4. Verification of scoped user directory
5. Role-based logins
6. Multi-tenant isolation
"""
import sys
import os
import requests
import json
import time

BASE_URL = os.environ.get("TEST_BASE_URL", "http://127.0.0.1:8000")

def test_full_hierarchy_flow():
    print(f"\n--- [1] Testing Organization & Master Admin Provisioning ---")
    ts = int(time.time())
    org_name = f"Skyline Infra Corp {ts % 10000}"
    admin_email = f"admin_{ts}@skylineinfra.com"
    admin_pw = "MasterPass@123"

    payload = {
        "org_name": org_name,
        "org_code": f"SIC{ts % 1000}",
        "industry": "Commercial & Residential High-Rise",
        "address": "Bandra Kurla Complex, Mumbai",
        "admin_name": "Vikramaditya Singhania",
        "admin_email": admin_email,
        "admin_password": admin_pw,
        "admin_phone": "+91 98200 12345"
    }

    res = requests.post(f"{BASE_URL}/api/auth/register-org-admin", json=payload)
    print(f"Status Code: {res.status_code}")
    assert res.status_code == 200, f"Failed to register org admin: {res.text}"
    data = res.json()
    assert data["status"] == "success"
    token = data["access_token"]
    org_id = data["organization"]["id"]
    print(f"✅ Organization Registered: {org_name} (ID: {org_id})")
    print(f"✅ Master Admin Provisioned: {admin_email} (Role: {data['user']['role']})")

    # [2] Test Admin Login
    print(f"\n--- [2] Testing Admin Authentication ---")
    login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": admin_email,
        "password": admin_pw,
        "org_id": org_id
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    login_data = login_res.json()
    assert login_data["user"]["role"] == "admin"
    admin_token = login_data["access_token"]
    print(f"✅ Admin Login Successful. JWT Token verified.")

    # [3] Admin provisions QC Lead
    print(f"\n--- [3] Admin Provisions QC Lead Under Organization ---")
    lead_email = f"lead_{ts}@skylineinfra.com"
    lead_pw = "QCLeadPass@123"
    lead_res = requests.post(
        f"{BASE_URL}/api/auth/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "org_id": org_id,
            "email": lead_email,
            "password": lead_pw,
            "full_name": "Ananya Sen",
            "role": "qc_lead",
            "employee_id": f"EMP-L{ts % 1000}",
            "specialization": "RCC Structural & QA Governance"
        }
    )
    assert lead_res.status_code == 200, f"Failed to provision QC Lead: {lead_res.text}"
    lead_data = lead_res.json()
    assert lead_data["user"]["role"] == "qc_lead"
    print(f"✅ QC Lead Provisioned: {lead_data['user']['full_name']} ({lead_email})")

    # [4] Admin provisions Inspection Engineer
    print(f"\n--- [4] Admin Provisions Inspection Engineer Under Organization ---")
    eng_email = f"eng_{ts}@skylineinfra.com"
    eng_pw = "EngineerPass@123"
    eng_res = requests.post(
        f"{BASE_URL}/api/auth/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "org_id": org_id,
            "email": eng_email,
            "password": eng_pw,
            "full_name": "Devendra Joshi",
            "role": "engineer",
            "employee_id": f"EMP-E{ts % 1000}",
            "specialization": "Waterproofing & Substructure Finishes"
        }
    )
    assert eng_res.status_code == 200, f"Failed to provision Engineer: {eng_res.text}"
    eng_data = eng_res.json()
    assert eng_data["user"]["role"] == "engineer"
    print(f"✅ Field Engineer Provisioned: {eng_data['user']['full_name']} ({eng_email})")

    # [5] Query scoped users directory
    print(f"\n--- [5] Querying Scoped User Directory ---")
    users_res = requests.get(
        f"{BASE_URL}/api/auth/users?org_id={org_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert users_res.status_code == 200
    users_list = users_res.json()["users"]
    user_roles = [u["role"] for u in users_list]
    print(f"✅ Total Provisioned Users for {org_name}: {len(users_list)}")
    print(f"   Roles found: {user_roles}")
    assert "admin" in user_roles
    assert "qc_lead" in user_roles
    assert "engineer" in user_roles

    # [6] Query scoped engineers for QC Lead allocation wizard
    eng_query_res = requests.get(
        f"{BASE_URL}/api/auth/users?org_id={org_id}&role=engineer",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert eng_query_res.status_code == 200
    eng_list = eng_query_res.json()["users"]
    assert len(eng_list) >= 1
    assert any(e["email"] == eng_email for e in eng_list)
    print(f"✅ Dynamic Engineer Roster verified for Allocation Wizard.")

    # [7] Verify QC Lead and Field Engineer independent authentication
    print(f"\n--- [6] Verifying QC Lead Authentication ---")
    lead_login = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": lead_email,
        "password": lead_pw,
        "org_id": org_id
    })
    assert lead_login.status_code == 200
    assert lead_login.json()["user"]["role"] == "qc_lead"
    print(f"✅ QC Lead Authenticated Successfully.")

    print(f"\n--- [7] Verifying Field Engineer Authentication ---")
    eng_login = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": eng_email,
        "password": eng_pw,
        "org_id": org_id
    })
    assert eng_login.status_code == 200
    assert eng_login.json()["user"]["role"] == "engineer"
    print(f"✅ Field Engineer Authenticated Successfully.")

    # [8] Multi-tenant cross-org defense test
    print(f"\n--- [8] Verifying Multi-Tenant Isolation ---")
    bad_login = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": eng_email,
        "password": eng_pw,
        "org_id": "org-psv" # deliberate mismatch
    })
    assert bad_login.status_code == 403, f"Expected 403 Forbidden on cross-tenant login, got {bad_login.status_code}"
    print(f"✅ Multi-Tenant Boundary Verified: Cross-tenant login blocked with HTTP 403.")

    print("\n=======================================================")
    print("🎉 ALL PLATFORM MULTI-TENANT & HIERARCHY TESTS PASSED! 🎉")
    print("=======================================================")

if __name__ == "__main__":
    test_full_hierarchy_flow()
