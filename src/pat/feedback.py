"""Pat's feedback & correction store — the learning loop's persistence layer.

Self-contained by design: this module OWNS the ``pat_feedback`` table (it runs
``CREATE TABLE IF NOT EXISTS`` lazily on first use) and never edits
``src/core/db.py``. It reuses the project's single SQLite file via ``get_conn()``
so Pat's feedback lives alongside the rest of Hermes' data (one-file
portability), but the schema bootstrap stays local here.

One table serves both arms of "learning" (see ``docs/pat-design-and-improvements.md`` §4):
  - :func:`recent_positive_examples` → confirmed 👍 free-text routings, injected as
    few-shot so the engine learns the user's phrasings (§4.4.2). Deterministic, ₹0.
  - :func:`recent_corrections` → 👎 + "what you expected" — the gold corrective
    signal, and the labeled dataset to later fine-tune an OWNED offline model
    (NOT the borrowed Nous agent, which runs a remote model we can't train).

Nothing here ever raises to the caller: a feedback failure must never break an
answer. Read helpers degrade to ``[]`` / ``{}`` on any error.
"""

from __future__ import annotations

import json

from src.core.db import get_conn

# Own schema — bootstrapped on first touch, idempotent. The CHECK keeps the
# verdict domain closed (only thumbs); every write below binds its values.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS pat_feedback (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    query         TEXT NOT NULL DEFAULT '',
    flow          TEXT,
    params_json   TEXT,
    verdict       TEXT NOT NULL CHECK (verdict IN ('up','down')),
    what_wrong    TEXT,
    expected_text TEXT,
    source        TEXT
);
CREATE INDEX IF NOT EXISTS idx_pat_feedback_created ON pat_feedback(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pat_feedback_verdict ON pat_feedback(verdict, created_at DESC);
"""

_ready = False


def _ensure(conn) -> None:
    """Create the table once per process. Cheap CREATE IF NOT EXISTS otherwise."""
    global _ready
    if not _ready:
        conn.executescript(_SCHEMA)
        _ready = True


def _clip(s, n: int):
    s = (s or "").strip()
    return s[:n] if s else None


def record(verdict: str, query: str = "", flow: str = "", params: dict | None = None,
           what_wrong: str | None = None, expected_text: str | None = None,
           source: str | None = None) -> int | None:
    """Persist one feedback event; returns its row id (or None on failure).

    `verdict` is coerced to 'up'/'down'. `params` is JSON-encoded. All values are
    bound — nothing is string-formatted into SQL.
    """
    v = "up" if str(verdict).strip().lower() in ("up", "1", "true", "yes", "👍") else "down"
    pj = None
    if params:
        try:
            pj = json.dumps(params, separators=(",", ":"), ensure_ascii=False)
        except Exception:
            pj = None
    try:
        with get_conn() as conn:
            _ensure(conn)
            cur = conn.execute(
                "INSERT INTO pat_feedback "
                "(query, flow, params_json, verdict, what_wrong, expected_text, source) "
                "VALUES (?,?,?,?,?,?,?)",
                (_clip(query, 500) or "", _clip(flow, 40), pj, v,
                 _clip(what_wrong, 500), _clip(expected_text, 1000), _clip(source, 40)),
            )
            return int(cur.lastrowid)
    except Exception:
        return None


def update(fid: int, expected_text: str | None = None, what_wrong: str | None = None) -> bool:
    """Attach the 'what you expected' correction to an existing row (the 👎 follow-up).

    Lets the UI record the bare 👎 first (so the negative is never lost) and then
    enrich the SAME row when the analyst types what they wanted — no double rows.
    """
    sets: list[str] = []
    vals: list = []
    if expected_text is not None:
        sets.append("expected_text=?")
        vals.append(_clip(expected_text, 1000))
    if what_wrong is not None:
        sets.append("what_wrong=?")
        vals.append(_clip(what_wrong, 500))
    if not sets:
        return False
    vals.append(int(fid))
    try:
        with get_conn() as conn:
            _ensure(conn)
            cur = conn.execute(
                f"UPDATE pat_feedback SET {', '.join(sets)} WHERE id=?", vals
            )
            return cur.rowcount > 0
    except Exception:
        return False


def recent_positive_examples(limit: int = 8) -> list[dict]:
    """Confirmed 👍 free-text routings as ``{query, flow, params}`` — engine few-shot.

    Only rows with a real typed query AND a routed data/explain flow qualify
    (clarify/empty rows are not routing labels). De-duplicated by (query, flow),
    most recent first.
    """
    limit = max(0, min(int(limit or 0), 25))
    if not limit:
        return []
    out: list[dict] = []
    try:
        with get_conn() as conn:
            _ensure(conn)
            rows = conn.execute(
                "SELECT query, flow, params_json FROM pat_feedback "
                "WHERE verdict='up' AND query<>'' AND flow IS NOT NULL "
                "AND flow NOT IN ('clarify','') "
                "ORDER BY created_at DESC LIMIT ?",
                (limit * 3,),   # over-fetch; we dedupe below then trim to `limit`
            ).fetchall()
    except Exception:
        return []
    seen: set = set()
    for r in rows:
        key = (r["query"].strip().lower(), r["flow"])
        if key in seen:
            continue
        seen.add(key)
        params = {}
        if r["params_json"]:
            try:
                params = json.loads(r["params_json"])
            except Exception:
                params = {}
        out.append({"query": r["query"], "flow": r["flow"], "params": params})
        if len(out) >= limit:
            break
    return out


def recent_corrections(limit: int = 8) -> list[dict]:
    """👎 rows carrying an ``expected_text`` — the corrective signal (§4.4.2).

    These are what the analyst actually wanted when Pat got it wrong: the highest
    value learning signal and the seed of the offline-training dataset.
    """
    limit = max(0, min(int(limit or 0), 25))
    if not limit:
        return []
    try:
        with get_conn() as conn:
            _ensure(conn)
            rows = conn.execute(
                "SELECT query, flow, what_wrong, expected_text FROM pat_feedback "
                "WHERE verdict='down' AND expected_text IS NOT NULL "
                "AND TRIM(expected_text)<>'' AND query<>'' "
                "ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    except Exception:
        return []
    return [
        {"query": r["query"], "flow": r["flow"],
         "what_wrong": r["what_wrong"], "expected_text": r["expected_text"]}
        for r in rows
    ]


def stats() -> dict:
    """Aggregate counts for telemetry / the weekly correction review (§4.5)."""
    try:
        with get_conn() as conn:
            _ensure(conn)
            r = conn.execute(
                "SELECT COUNT(*) n, "
                "SUM(CASE WHEN verdict='up' THEN 1 ELSE 0 END) up, "
                "SUM(CASE WHEN verdict='down' THEN 1 ELSE 0 END) down, "
                "SUM(CASE WHEN expected_text IS NOT NULL AND TRIM(expected_text)<>'' "
                "    THEN 1 ELSE 0 END) corrections "
                "FROM pat_feedback"
            ).fetchone()
            return {"total": r["n"] or 0, "up": r["up"] or 0,
                    "down": r["down"] or 0, "corrections": r["corrections"] or 0}
    except Exception:
        return {"total": 0, "up": 0, "down": 0, "corrections": 0}
