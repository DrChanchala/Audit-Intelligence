"""Global master checklist (read-only reference data shared by all tenants).

The full tree is loaded in 3 queries and cached in memory; filters are then
applied in Python, so repeated wizard loads cost no database round-trips.
"""
from __future__ import annotations

import copy
import threading

from app.db.connection import Session

_cache: list[dict] | None = None
_lock = threading.Lock()


def _load(db: Session) -> list[dict]:
    stages = [dict(r) for r in db.all("SELECT * FROM master_stages ORDER BY display_order")]
    subs = [dict(r) for r in db.all("SELECT * FROM master_subgroups ORDER BY display_order")]
    chks = [dict(r) for r in db.all("SELECT * FROM master_checkpoints ORDER BY display_order")]
    by_sub: dict[str, list[dict]] = {}
    for c in chks:
        by_sub.setdefault(c["subgroup_id"], []).append(c)
    by_stage: dict[str, list[dict]] = {}
    for s in subs:
        s["checkpoints"] = by_sub.get(s["subgroup_id"], [])
        by_stage.setdefault(s["stage_id"], []).append(s)
    for st in stages:
        st["subgroups"] = by_stage.get(st["stage_id"], [])
    return stages


def tree(db: Session) -> list[dict]:
    global _cache
    if _cache is None:
        with _lock:
            if _cache is None:
                _cache = _load(db)
    return _cache


def invalidate() -> None:
    global _cache
    _cache = None


def filtered(db: Session, stage_id=None, building_type=None, priority=None, search_q=None) -> list[dict]:
    pri = priority.upper()[:1] if priority and priority != "all" else None
    bt = building_type.lower() if building_type and building_type != "all" else None
    q = search_q.lower().strip() if search_q else None
    result = []
    for st in tree(db):
        if stage_id and stage_id not in (st["stage_id"], st["stage_num"]):
            continue
        out_subs = []
        for sub in st["subgroups"]:
            items = [
                c for c in sub["checkpoints"]
                if (not pri or c["priority"] == pri)
                and (not bt or c["applicable_building_types"] == "all" or bt in c["applicable_building_types"].lower())
                and (not q or q in c["checkpoint_description"].lower())
            ]
            if items or not q:
                s = {k: v for k, v in sub.items() if k != "checkpoints"}
                s["checkpoints"] = copy.copy(items)
                s["checkpoint_count"] = len(items)
                out_subs.append(s)
        if out_subs or not q:
            stage = {k: v for k, v in st.items() if k != "subgroups"}
            stage["subgroups"] = out_subs
            stage["total_checkpoints"] = sum(s["checkpoint_count"] for s in out_subs)
            result.append(stage)
    return result


def checkpoints_by_ids(db: Session, ids: list[str]) -> list[dict]:
    wanted = set(ids)
    found = []
    for st in tree(db):
        for sub in st["subgroups"]:
            for c in sub["checkpoints"]:
                if c["checkpoint_id"] in wanted:
                    found.append({**c, "stage_name": st["stage_name"], "subgroup_name": sub["subgroup_name"]})
    return found
