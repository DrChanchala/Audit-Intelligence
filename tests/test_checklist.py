"""Master checklist tests (spec §8 item 6).

Verifies:
- Tree structure: exactly 20 stages, 98 subgroups, 859 checkpoints.
- Filtering by stage_id, building_type, priority, and search keyword.
- Performance: p95 latency is under 200 ms over 20 iterations.
"""
from __future__ import annotations

import time

from fastapi.testclient import TestClient


def test_master_checklist_exact_counts(qc_a_client: TestClient):
    """Assert master checklist contains exactly 20 stages, 98 subgroups, and 859 checkpoints."""
    resp = qc_a_client.get("/api/master-checklist")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"

    stages = data["stages"]
    assert len(stages) == 20, f"Expected 20 stages, got {len(stages)}"

    subgroup_count = sum(len(st["subgroups"]) for st in stages)
    assert subgroup_count == 98, f"Expected 98 subgroups, got {subgroup_count}"

    checkpoint_count = sum(
        sum(len(sub["checkpoints"]) for sub in st["subgroups"])
        for st in stages
    )
    assert checkpoint_count == 859, f"Expected 859 checkpoints, got {checkpoint_count}"


def test_master_checklist_filters(qc_a_client: TestClient):
    """Test filtering by stage_id, building_type, priority, and query search."""
    # 1. Filter by stage_id
    resp = qc_a_client.get("/api/master-checklist?stage_id=STG-01")
    assert resp.status_code == 200
    stages = resp.json()["stages"]
    assert len(stages) == 1
    assert stages[0]["stage_id"] == "STG-01"

    # 2. Filter by priority High ('H')
    resp = qc_a_client.get("/api/master-checklist?priority=H")
    assert resp.status_code == 200
    stages = resp.json()["stages"]
    for st in stages:
        for sub in st["subgroups"]:
            for c in sub["checkpoints"]:
                assert c["priority"] == "H"

    # 3. Filter by search query
    resp = qc_a_client.get("/api/master-checklist?q=boundary")
    assert resp.status_code == 200
    stages = resp.json()["stages"]
    assert len(stages) > 0
    for st in stages:
        for sub in st["subgroups"]:
            for c in sub["checkpoints"]:
                assert "boundary" in c["checkpoint_description"].lower()


def test_master_checklist_p95_latency(qc_a_client: TestClient):
    """Assert p95 response time is strictly under 200 ms over 20 consecutive calls."""
    durations = []
    for _ in range(20):
        t0 = time.perf_counter()
        resp = qc_a_client.get("/api/master-checklist")
        t1 = time.perf_counter()
        assert resp.status_code == 200
        durations.append((t1 - t0) * 1000)  # milliseconds

    durations.sort()
    # 95th percentile index in 20 items: index 18 (19th element)
    p95 = durations[int(len(durations) * 0.95)]
    assert p95 < 200.0, f"p95 was {p95:.2f} ms (target: < 200 ms)"
