"""Page routing, server-side guards, security headers, and template integrity tests (spec §8 item 8)."""
from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.security import Role


def test_landing_page_anonymous(anon_client: TestClient):
    """Assert / and /login return HTML for anonymous users with security and no-store headers."""
    for path in ("/", "/login"):
        resp = anon_client.get(path)
        assert resp.status_code == 200, f"Failed for {path}"
        assert "text/html" in resp.headers.get("content-type", "")
        # Security headers
        assert "no-store" in resp.headers.get("cache-control", "").lower()
        assert resp.headers.get("x-frame-options") == "DENY"
        assert resp.headers.get("x-content-type-options") == "nosniff"
        assert "content-security-policy" in resp.headers
        assert "script-src 'self'" in resp.headers["content-security-policy"]


def test_page_role_guards_anonymous_redirects(anon_client: TestClient):
    """Assert unauthenticated visits to role consoles redirect to /login?next=..."""
    for path in ("/admin", "/admin-dashboard", "/qc", "/qc-lead", "/engineer", "/engineer-dashboard"):
        resp = anon_client.get(path, follow_redirects=False)
        assert resp.status_code == 302, f"Expected 302 for {path}, got {resp.status_code}"
        location = resp.headers.get("location", "")
        assert location.startswith("/login?next="), f"Invalid location {location} for {path}"


def test_authenticated_user_login_redirect(
    admin_a_client: TestClient,
    qc_a_client: TestClient,
    eng_a_client: TestClient,
):
    """Assert logged-in users hitting /login or / are redirected to their home dashboard."""
    assert admin_a_client.get("/login", follow_redirects=False).headers.get("location") == Role.ADMIN.home
    assert qc_a_client.get("/login", follow_redirects=False).headers.get("location") == Role.QC_LEAD.home
    assert eng_a_client.get("/login", follow_redirects=False).headers.get("location") == Role.ENGINEER.home

    assert admin_a_client.get("/", follow_redirects=False).headers.get("location") == Role.ADMIN.home
    assert qc_a_client.get("/", follow_redirects=False).headers.get("location") == Role.QC_LEAD.home
    assert eng_a_client.get("/", follow_redirects=False).headers.get("location") == Role.ENGINEER.home


def test_cross_role_page_access_redirects_to_own_home(
    admin_a_client: TestClient,
    qc_a_client: TestClient,
    eng_a_client: TestClient,
):
    """Assert users navigating to a console outside their role are redirected to their own home."""
    # Admin navigating to QC or Engineer
    assert admin_a_client.get("/qc", follow_redirects=False).headers.get("location") == Role.ADMIN.home
    assert admin_a_client.get("/engineer", follow_redirects=False).headers.get("location") == Role.ADMIN.home

    # QC Lead navigating to Admin or Engineer
    assert qc_a_client.get("/admin", follow_redirects=False).headers.get("location") == Role.QC_LEAD.home
    assert qc_a_client.get("/engineer", follow_redirects=False).headers.get("location") == Role.QC_LEAD.home

    # Engineer navigating to Admin or QC
    assert eng_a_client.get("/admin", follow_redirects=False).headers.get("location") == Role.ENGINEER.home
    assert eng_a_client.get("/qc", follow_redirects=False).headers.get("location") == Role.ENGINEER.home


def test_role_page_aliases(
    admin_a_client: TestClient,
    qc_a_client: TestClient,
    eng_a_client: TestClient,
    anon_client: TestClient,
):
    """Assert page aliases redirect appropriately."""
    for alias in ("/dashboard", "/inspections", "/allocations"):
        assert anon_client.get(alias, follow_redirects=False).status_code == 302
        assert admin_a_client.get(alias, follow_redirects=False).headers.get("location") == Role.ADMIN.home
        assert qc_a_client.get(alias, follow_redirects=False).headers.get("location") == Role.QC_LEAD.home
        assert eng_a_client.get(alias, follow_redirects=False).headers.get("location") == Role.ENGINEER.home


def test_admin_console_page_renders_html(admin_a_client: TestClient):
    """Assert admin console serves HTML with admin template elements."""
    resp = admin_a_client.get("/admin")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    content = resp.text
    assert "Organization Console" in content
    assert "Projects" in content
    assert "Team &amp; Provisioning" in content or "Team & Provisioning" in content


def test_static_asset_caching_policy(anon_client: TestClient):
    """Assert static files have no-cache without query param and immutable max-age with ?v=."""
    # Without version: no-cache
    resp_unversioned = anon_client.get("/static/css/app.css")
    assert resp_unversioned.status_code == 200
    assert "no-cache" in resp_unversioned.headers.get("cache-control", "")

    # With version ?v=...: public, max-age=31536000, immutable
    resp_versioned = anon_client.get("/static/css/app.css?v=2.0.0")
    assert resp_versioned.status_code == 200
    cc = resp_versioned.headers.get("cache-control", "")
    assert "immutable" in cc
    assert "max-age=31536000" in cc


def test_templates_contain_no_inline_scripts():
    """Verify that every template strictly avoids inline script tags (mandated by CSP script-src 'self')."""
    templates_dir = Path(__file__).resolve().parent.parent / "templates"
    template_files = list(templates_dir.glob("*.html"))
    assert len(template_files) >= 3, f"Expected at least 3 templates, found {len(template_files)}"

    script_pattern = re.compile(r"<script\b([^>]*)>(.*?)</script>", re.DOTALL | re.IGNORECASE)

    for template_file in template_files:
        content = template_file.read_text(encoding="utf-8")
        matches = script_pattern.findall(content)
        for attrs, body in matches:
            assert 'src="' in attrs or "src='" in attrs, (
                f"Template {template_file.name} contains inline <script> without src attribute: {attrs}"
            )
            # Body between <script src="..."> and </script> must be empty or only whitespace
            assert not body.strip(), (
                f"Template {template_file.name} contains inline code inside <script src=...>: {body.strip()}"
            )
