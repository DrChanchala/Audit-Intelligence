import os
import psycopg2
import sqlite3
import bcrypt
from datetime import datetime

# Initialize default organizations & verified enterprise users
DEFAULT_ORGS = [
    ("org-psv", "Purvanchal Group · Skyline Vista Infrastructure", "PSV-INFRA", "purvanchal.com", "Commercial & Luxury Residential", "Noida Sector 94, Uttar Pradesh"),
    ("org-lct", "Lumos Commercial Asset Management", "LCT-ASSET", "lumosgroup.com", "Commercial & Retail Towers", "Sector 65, Gurugram, Haryana"),
    ("org-t117", "NCR Telecom Infrastructure Consortium", "NCR-TEL", "ncrtelecom.in", "Telecom Towers & Power Infrastructure", "Sector 150, Noida"),
    ("org-nlp", "Ecotech Logistics & Industrial Parks", "ECO-LOG", "ecotechparks.com", "Industrial Logistics & Cold Chain", "Ecotech VI, Greater Noida"),
    ("org-rvv", "Riverside Luxury Developments", "RVV-DEV", "riversidedev.com", "Residential Townships & Villas", "Greater Noida West"),
    ("org-apex", "Apex Quality Assurance & Civil Engineering", "APEX-QA", "apexqc.com", "Independent Third-Party Quality Audit", "Barakhamba Road, Connaught Place, New Delhi")
]

# Map existing projects to organizations
PROJECT_ORG_MAPPING = {
    "psv": "org-psv",
    "lct": "org-lct",
    "t117": "org-t117",
    "t109": "org-t117",
    "t124": "org-t117",
    "nlp": "org-nlp",
    "rvv": "org-rvv",
    "s108": "org-rvv",
    "s62": "org-nlp",
    "yem": "org-lct"
}

def get_hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')

def init_postgres(pg_url: str):
    print(f"Connecting to PostgreSQL: {pg_url[:35]}...")
    conn = psycopg2.connect(pg_url)
    cur = conn.cursor()

    # 1. Run migration SQL
    with open("migrations/002_add_auth_and_multitenancy.sql", "r", encoding="utf-8") as f:
        sql = f.read()
    cur.execute(sql)
    conn.commit()
    print("PostgreSQL migration 002 applied successfully.")

    # 2. Insert organizations
    for org in DEFAULT_ORGS:
        cur.execute("""
            INSERT INTO organizations (id, name, code, domain, industry, address)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET 
                name = EXCLUDED.name,
                code = EXCLUDED.code,
                domain = EXCLUDED.domain,
                industry = EXCLUDED.industry;
        """, org)
    conn.commit()
    print(f"Inserted/updated {len(DEFAULT_ORGS)} organizations in PostgreSQL.")

    # 3. Insert verified users
    users = [
        # Purvanchal Group Users
        ("usr-priya-01", "org-psv", "priya.deshmukh@purvanchal.com", get_hash("Lead@123"), "Priya Deshmukh", "qc_lead", "EMP-1001", "Quality Assurance & Governance", "PD", "+91 98100 23456"),
        ("usr-anjali-01", "org-psv", "anjali.rao@purvanchal.com", get_hash("Engineer@123"), "Anjali Rao", "engineer", "EMP-1004", "Finishes & Waterproofing", "AR", "+91 98110 34567"),
        ("usr-rohit-01", "org-psv", "rohit.kale@purvanchal.com", get_hash("Engineer@123"), "Rohit Kale", "engineer", "EMP-1002", "RCC & Structural", "RK", "+91 98120 45678"),
        ("usr-admin-01", "org-psv", "admin@purvanchal.com", get_hash("Admin@123"), "Platform Administrator", "admin", "ADM-001", "Platform Systems & Multi-Tenant", "PA", "+91 98000 11111"),

        # Lumos Commercial Users
        ("usr-meera-01", "org-lct", "meera.iyer@lumosgroup.com", get_hash("Engineer@123"), "Meera Iyer", "engineer", "EMP-1005", "Façade & MEP", "MI", "+91 98130 56789"),
        ("usr-lead-lct", "org-lct", "lead@lumosgroup.com", get_hash("Lead@123"), "Sunil Verma", "qc_lead", "EMP-2001", "Commercial QC Lead", "SV", "+91 98140 67890"),

        # NCR Telecom Users
        ("usr-vikram-01", "org-t117", "vikram.singh@ncrtelecom.in", get_hash("Engineer@123"), "Vikram Singh", "engineer", "EMP-1003", "Steel & Telecom", "VS", "+91 98150 78901"),
        ("usr-arjun-01", "org-nlp", "arjun.mehta@ecotechparks.com", get_hash("Engineer@123"), "Arjun Mehta", "engineer", "EMP-1006", "Industrial & PEB", "AM", "+91 98160 89012")
    ]

    for u in users:
        cur.execute("""
            INSERT INTO users (id, org_id, email, password_hash, full_name, role, employee_id, specialization, avatar_initials, phone)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                password_hash = EXCLUDED.password_hash,
                role = EXCLUDED.role,
                full_name = EXCLUDED.full_name,
                employee_id = EXCLUDED.employee_id;
        """, u)
    conn.commit()
    print(f"Inserted/updated {len(users)} users in PostgreSQL.")

    # 4. Map projects to their org_id
    for proj_id, org_id in PROJECT_ORG_MAPPING.items():
        cur.execute("UPDATE projects SET org_id = %s WHERE id = %s;", (org_id, proj_id))
    conn.commit()
    print("Mapped all existing projects to their respective organization IDs in PostgreSQL.")

    conn.close()

def init_sqlite():
    db_path = "audit_intelligence.db"
    if not os.path.exists(db_path):
        return
    print(f"Applying schema & data to local SQLite: {db_path}...")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS organizations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE,
            domain TEXT,
            industry TEXT DEFAULT 'Construction & Real Estate',
            address TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            org_id TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            employee_id TEXT,
            specialization TEXT,
            avatar_initials TEXT,
            phone TEXT,
            status TEXT DEFAULT 'active',
            last_login_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Check if org_id column exists in projects
    cur.execute("PRAGMA table_info(projects);")
    cols = [r[1] for r in cur.fetchall()]
    if "org_id" not in cols:
        cur.execute("ALTER TABLE projects ADD COLUMN org_id TEXT;")

    # Insert default organizations
    for org in DEFAULT_ORGS:
        cur.execute("""
            INSERT OR REPLACE INTO organizations (id, name, code, domain, industry, address)
            VALUES (?, ?, ?, ?, ?, ?);
        """, org)

    # Insert verified users
    users = [
        ("usr-priya-01", "org-psv", "priya.deshmukh@purvanchal.com", get_hash("Lead@123"), "Priya Deshmukh", "qc_lead", "EMP-1001", "Quality Assurance & Governance", "PD", "+91 98100 23456"),
        ("usr-anjali-01", "org-psv", "anjali.rao@purvanchal.com", get_hash("Engineer@123"), "Anjali Rao", "engineer", "EMP-1004", "Finishes & Waterproofing", "AR", "+91 98110 34567"),
        ("usr-rohit-01", "org-psv", "rohit.kale@purvanchal.com", get_hash("Engineer@123"), "Rohit Kale", "engineer", "EMP-1002", "RCC & Structural", "RK", "+91 98120 45678"),
        ("usr-admin-01", "org-psv", "admin@purvanchal.com", get_hash("Admin@123"), "Platform Administrator", "admin", "ADM-001", "Platform Systems & Multi-Tenant", "PA", "+91 98000 11111"),
        ("usr-meera-01", "org-lct", "meera.iyer@lumosgroup.com", get_hash("Engineer@123"), "Meera Iyer", "engineer", "EMP-1005", "Façade & MEP", "MI", "+91 98130 56789"),
        ("usr-lead-lct", "org-lct", "lead@lumosgroup.com", get_hash("Lead@123"), "Sunil Verma", "qc_lead", "EMP-2001", "Commercial QC Lead", "SV", "+91 98140 67890"),
        ("usr-vikram-01", "org-t117", "vikram.singh@ncrtelecom.in", get_hash("Engineer@123"), "Vikram Singh", "engineer", "EMP-1003", "Steel & Telecom", "VS", "+91 98150 78901"),
        ("usr-arjun-01", "org-nlp", "arjun.mehta@ecotechparks.com", get_hash("Engineer@123"), "Arjun Mehta", "engineer", "EMP-1006", "Industrial & PEB", "AM", "+91 98160 89012")
    ]
    for u in users:
        cur.execute("""
            INSERT OR REPLACE INTO users (id, org_id, email, password_hash, full_name, role, employee_id, specialization, avatar_initials, phone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, u)

    for proj_id, org_id in PROJECT_ORG_MAPPING.items():
        cur.execute("UPDATE projects SET org_id = ? WHERE id = ?;", (org_id, proj_id))

    conn.commit()
    conn.close()
    print("Local SQLite synchronized with organizations and users successfully.")

if __name__ == "__main__":
    pg_url = os.environ.get("DATABASE_URL")
    if pg_url:
        init_postgres(pg_url)
    init_sqlite()
    print("Enterprise Auth & Multi-Tenant initialization complete!")
