"""src/web/home/trust_reads.py — the bounded read layer for the Graphite Trust/Proof estate (W5).

Same contract as `reads.py`: this module returns **plain rows/dicts/text only, never HTML**;
`trust_pages.py` renders. Every read is defensive — a Trust page must never 500 and must never
fabricate a number, so an absent source returns an explicit "not present" marker that the page
turns into a TEACHING empty state (`journey.teaching_empty`).

Sourcing rule (SURFACE-PLAYBOOK sister-data check): every page here reads the SAME source the
classic surface reads — never a second copy.

  glossary       -> `src.web.glossary` (the ONE parser of `docs/metrics-glossary.md`; stdlib-only,
                    zero `src.web` view imports, so reusing it couples nothing)
  strategy-ref   -> `docs/strategies/*.md` directly. The classic view hard-codes a 16-entry
                    slug->file map; deriving the list from the directory instead means it can
                    never drift. NOTE: `src.web.strategies_view` is deliberately NOT imported —
                    it imports `src.web.dashboard`, which the Graphite isolation contract exists
                    to keep out of this package.
  coverage       -> `src.automation.provenance.coverage_snapshot` (the automation layer, not the view)
  rule-lab       -> `src.automation.rule_lab` (the ENGINE; the classic page is a second consumer)
  spec-sheets    -> `src.web.spec_sheets` content constants (`_SHEETS` etc. are DATA, not a render
                    engine, and that module imports only stdlib + fastapi — copying them would
                    guarantee drift, which is the thing the parity ledger exists to prevent)
  validation     -> research.db `strategy_registry` / `strategy_runs` / `strategy_holdings`, the
                    same tables `testing_view` reads, via our own bounded SQL
  replay         -> the real `/v1` API in-process (that IS the point-in-time proof)
"""
from __future__ import annotations

import os
import re
import sqlite3

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# research.db lives on the box; a laptop/worktree has none. Both candidates are probed so the page
# is honest about WHICH environment it is in rather than silently rendering an empty table.
_RESEARCH_CANDIDATES = (
    os.environ.get("HERMES_RESEARCH_DB") or "",
    os.path.join(_ROOT, "data", "research.db"),
    "/opt/hermes/data/research.db",
)


# ── glossary (source: docs/metrics-glossary.md via the ONE parser) ───────────────────
def glossary_entries() -> list:
    """[{name, family, body, sources}] — the parsed metric dictionary, in document order.

    Reads `src.web.glossary`'s own parse (the single definition source that also feeds the `?`
    popovers, `/dash/glossary`, and Pat's auto-fold). `_ENTRIES` is module-private by convention
    but is the only accessor for the whole set; the alternative is a second parser, which the
    playbook forbids. Degrades to [] if the file or the module ever moves."""
    try:
        from src.web import glossary as G
        G._load()
        return [dict(e) for e in (G._ENTRIES or [])]
    except Exception:  # noqa: BLE001 — a trust page must never 500
        return []


def glossary_families() -> list:
    """[(family, [entry, …])] in document order — the page's section structure."""
    fams: list = []
    seen: dict = {}
    for e in glossary_entries():
        fam = e.get("family") or "Other"
        if fam not in seen:
            seen[fam] = []
            fams.append((fam, seen[fam]))
        seen[fam].append(e)
    return fams


# ── the public sanitizer (strategy-ref) ──────────────────────────────────────────────
# The classic public sanitizer (`strategies_view._public`) scrubs internal governance tokens before
# a strategy doc is served publicly. Its session/decision regex is `\b[SD]\d{1,3}[a-z]?\b`, which
# does NOT cover multi-letter or hyphenated suffixes (`S164BB`, `S155-e`) or 4-digit ids (`S1234`) —
# those leak verbatim today. Its DATE-ledger regex DOES cover multi-letter (`[A-Za-z]{1,3}`, so
# `2026-07-16BB` is handled). This port widens both and then adds a belt-and-braces LINE DROP: any
# line that still smells internal after substitution is removed entirely, so this renderer can only
# ever leak LESS than the classic one, never more.
_RE_HASH = re.compile(r"`[0-9a-f]{7,40}`")
_RE_ID_PARENS = re.compile(r"\(\s*(?:[SD]\d{1,4}(?:-[a-z0-9]{1,3}|[A-Za-z]{1,3})?[\s,/·;]*)+\)")
_RE_ID = re.compile(r"\b[SD]\d{1,4}(?:-[a-z0-9]{1,3}|[A-Za-z]{1,3})?\b")
_RE_DATE_TAG = re.compile(r"\b(20\d{2}-\d{2}-\d{2})[A-Za-z]{1,4}\b")
_RE_RAMANA = re.compile(r"\bRamana(?:'s)?\b")
# residue that means "this line was written for us, not for a reader"
_RE_RESIDUE = re.compile(r"(PROJECT_STATE|AGENTS\.md|CLAUDE\.md|memory `|session log|carry-?forward"
                         r"|\bS\d{2,4}\b|\bD\d{2,4}\b|[0-9a-f]{7,40})", re.I)
_META_PREFIXES = ("**class:**", "**reconciled:**", "**owner:**", "**maintenance",
                  "**status (internal", "shared template", "> **class:", "**source of truth")
_DROP_SECTIONS = ("maintenance", "shared template", "governance", "session log", "change log")


def public_text(text: str) -> str:
    """Strategy-doc markdown, scrubbed for a public reader. Drops the governance blockquote, the
    meta header lines, whole internal sections, commit hashes and session/decision/ledger ids —
    then drops any surviving line that still matches an internal-residue pattern."""
    out, in_fence, dropping = [], False, False
    started = False
    for raw in (text or "").splitlines():
        line = raw.rstrip()
        low = line.strip().lower()
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        if low.startswith("#"):
            title = low.lstrip("#").strip().strip("*")
            dropping = any(title.startswith(d) for d in _DROP_SECTIONS)
            started = True
            if dropping:
                continue
        if dropping:
            continue
        # the leading governance blockquote: everything quoted BEFORE the first heading
        if not started and low.startswith(">"):
            continue
        if any(low.startswith(p) for p in _META_PREFIXES):
            continue
        s = _RE_HASH.sub("", line)
        s = _RE_ID_PARENS.sub("", s)
        s = _RE_ID.sub("", s)
        s = _RE_DATE_TAG.sub(r"\1", s)
        s = _RE_RAMANA.sub("the desk", s)
        s = re.sub(r"\(\s*[,;·/]*\s*\)", "", s)          # empty parens left behind
        s = re.sub(r"[ \t]{2,}", " ", s).rstrip()
        if s.strip() and _RE_RESIDUE.search(s):
            continue                                      # belt-and-braces: never render residue
        out.append(s)
    # collapse the blank runs the drops leave behind
    clean: list = []
    for line in out:
        if not line.strip() and clean and not clean[-1].strip():
            continue
        clean.append(line)
    return "\n".join(clean).strip()


# ── strategy reference (source: docs/strategies/*.md) ────────────────────────────────
_STRAT_DIR = os.path.join(_ROOT, "docs", "strategies")
_SLUG_OK = re.compile(r"^[a-z0-9][a-z0-9-]{0,48}$")


def strategy_pages() -> list:
    """[{slug, title, file}] — DERIVED from the directory, so a new strategy page appears the day
    it lands (the classic view's 16-entry hardcoded map cannot drift-check itself). README/index
    are excluded: they are the index, not a strategy."""
    out = []
    try:
        names = sorted(os.listdir(_STRAT_DIR))
    except OSError:
        return []
    for fn in names:
        if not fn.lower().endswith(".md") or fn.lower() in ("readme.md", "index.md", "_index.md"):
            continue
        slug = fn[:-3].lower()
        if not _SLUG_OK.match(slug):
            continue
        out.append({"slug": slug, "file": fn, "title": _first_h1(os.path.join(_STRAT_DIR, fn)) or slug})
    return out


def _first_h1(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            for _ in range(80):
                line = fh.readline()
                if not line:
                    break
                if line.startswith("# "):
                    return public_text(line[2:].strip()).strip()
    except OSError:
        return ""
    return ""


def strategy_doc(slug: str) -> dict:
    """{'slug','title','text'} — the sanitized markdown for one page, or {} if unknown. `slug` is
    matched against the DERIVED page list, so a path-traversal string can never reach open()."""
    want = (slug or "").strip().lower()
    for p in strategy_pages():
        if p["slug"] == want:
            try:
                with open(os.path.join(_STRAT_DIR, p["file"]), encoding="utf-8") as fh:
                    return {"slug": p["slug"], "title": p["title"], "text": public_text(fh.read())}
            except OSError:
                return {}
    return {}


# ── coverage (source: src.automation.provenance) ─────────────────────────────────────
def coverage(conn=None) -> dict:
    """The coverage/settlement snapshot: {as_of, build_at, universe, classes, cci, lag_audit}.
    {} when provenance or its tables are unavailable — the page then teaches instead of blanking."""
    try:
        from src.automation import provenance as P
        snap = P.coverage_snapshot(conn)
        return dict(snap) if isinstance(snap, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def provenance_registry() -> list:
    """The declared data-class registry digest (list of dicts) — [] when unavailable."""
    try:
        from src.automation import provenance as P
        return list(P.provenance_registry_digest() or [])
    except Exception:  # noqa: BLE001
        return []


# ── validation record (source: research.db, the tables /dash/testing reads) ──────────
def _research_ro():
    for cand in _RESEARCH_CANDIDATES:
        if not cand or not os.path.exists(cand):
            continue
        try:
            return sqlite3.connect(f"file:{cand}?mode=ro", uri=True), cand
        except Exception:  # noqa: BLE001
            continue
    return None, ""


def validation() -> dict:
    """{'present':bool,'path':str,'rows':[…],'n_runs':int} — the strategy verdict record.

    `sharpe` is the LEGACY COLUMN NAME in research.db; the VALUE is a return/vol ratio (D142) and
    is surfaced under that name only. Never rendered with the word the audit retired."""
    con, path = _research_ro()
    if con is None:
        return {"present": False, "path": "", "rows": [], "n_runs": 0}
    rows, n_runs = [], 0
    try:
        cur = con.execute("""
            SELECT g.name, g.category, g.status,
              (SELECT sharpe       FROM strategy_runs r WHERE r.name=g.name ORDER BY run_ts DESC LIMIT 1),
              (SELECT cagr_pct     FROM strategy_runs r WHERE r.name=g.name ORDER BY run_ts DESC LIMIT 1),
              (SELECT maxdd_pct    FROM strategy_runs r WHERE r.name=g.name ORDER BY run_ts DESC LIMIT 1),
              (SELECT ann_cost_pct FROM strategy_runs r WHERE r.name=g.name ORDER BY run_ts DESC LIMIT 1),
              (SELECT cost_model   FROM strategy_runs r WHERE r.name=g.name ORDER BY run_ts DESC LIMIT 1),
              (SELECT capacity_cr  FROM strategy_runs r WHERE r.name=g.name ORDER BY run_ts DESC LIMIT 1)
            FROM strategy_registry g
            ORDER BY (CASE WHEN (SELECT sharpe FROM strategy_runs r WHERE r.name=g.name
                      ORDER BY run_ts DESC LIMIT 1) IS NULL THEN 1 ELSE 0 END), 4 DESC""")
        keys = ("name", "category", "status", "ret_vol", "cagr_pct", "maxdd_pct",
                "ann_cost_pct", "cost_model", "capacity_cr")
        rows = [dict(zip(keys, r)) for r in cur.fetchall()]
        if rows:
            n_runs = con.execute("SELECT COUNT(*) FROM strategy_runs").fetchone()[0]
    except Exception:  # noqa: BLE001 — a missing table is an honest empty, not a crash
        rows, n_runs = [], 0
    finally:
        con.close()
    return {"present": True, "path": path, "rows": rows, "n_runs": int(n_runs or 0)}


def validation_holdings() -> dict:
    """{strategy_name: (as_of, [symbol, …])} — the current book behind each verdict. {} if absent."""
    con, _p = _research_ro()
    if con is None:
        return {}
    out: dict = {}
    try:
        for nm, asof, sym in con.execute(
                "SELECT name, as_of, symbol FROM strategy_holdings ORDER BY name, rank"):
            out.setdefault(nm, [asof, []])
            out[nm][1].append(sym)
    except Exception:  # noqa: BLE001
        out = {}
    finally:
        con.close()
    return {k: (v[0], v[1]) for k, v in out.items()}


# ── pre-registration ledger (source: src.web.spec_sheets content constants) ──────────
def spec_sheets() -> dict:
    """{'sheets':[…],'hashes':{},'m05':str,'note':str,'placebo':html_or_'','mttr':html_or_''}.

    `_SHEETS` is CONTENT (9 pre-registered studies with their gate + result), not a renderer;
    importing it is the only way to keep one copy. `spec_sheets` imports stdlib + fastapi only —
    no `dashboard`, no preview module — so this does not couple Graphite to the classic chrome.
    The two live boxes (`_placebo_box`, `_mttr_box`) return small HTML fragments; they are passed
    through verbatim only when they are non-empty, and the page teaches instead when they are not."""
    try:
        from src.web import spec_sheets as SS
    except Exception:  # noqa: BLE001
        return {"sheets": [], "hashes": {}, "m05": "", "note": "", "placebo": "", "mttr": ""}
    def _safe(fn):
        try:
            return fn() or ""
        except Exception:  # noqa: BLE001
            return ""
    try:
        hashes = SS._prereg_hashes() or {}
    except Exception:  # noqa: BLE001
        hashes = {}
    return {"sheets": list(getattr(SS, "_SHEETS", []) or []), "hashes": hashes,
            "m05": getattr(SS, "M05_BOX", "") or "", "note": getattr(SS, "NOTE_HTML", "") or "",
            "placebo": _safe(getattr(SS, "_placebo_box", lambda: "")),
            "mttr": _safe(getattr(SS, "_mttr_box", lambda: ""))}


# ── rule lab (source: src.automation.rule_lab — the engine, not the classic view) ────
_RULE_KEYS = ("u", "rank", "n", "hold", "where", "veto")


def rule_vocabulary() -> dict:
    """The closed vocabulary the composer offers. {} if the engine is unavailable."""
    try:
        from src.automation import rule_lab as RL
    except Exception:  # noqa: BLE001
        return {}
    return {"universes": dict(RL.UNIVERSES), "signals": dict(RL.SIGNALS),
            "filters": dict(RL.FILTERS), "vetoes": dict(RL.VETOES),
            "holds": tuple(RL.HOLDS), "take": (RL.TAKE_MIN, RL.TAKE_MAX),
            "verdicts": tuple(RL.VERDICTS), "qualifiers": tuple(RL.QUALIFIERS)}


def rule_query_from_spec(spec) -> dict:
    """RuleSpec -> the URL params that reproduce it. The param NAMES are the shared contract with
    the classic page (`?u=&rank=&n=&hold=&where=&veto=`), so a link pasted from either surface
    opens the same rule on the other. Pinned to the classic mapping by the lane's test."""
    q = {"u": spec.universe, "rank": spec.signal, "n": str(spec.take), "hold": spec.hold}
    if spec.filters:
        q["where"] = ",".join(spec.filters)
    if spec.vetoes:
        q["veto"] = ",".join(spec.vetoes)
    return q


def rule_spec_from_query(params: dict):
    """URL params -> RuleSpec, through the engine's own closed-vocabulary validator. Raises
    `rule_lab.RuleError` (which carries `.citations`) on any token outside the vocabulary."""
    from src.automation.rule_lab import spec_from_params
    def split(v):
        return [p.strip() for p in str(v or "").split(",") if p.strip()]
    return spec_from_params(universe=params.get("u", ""), signal=params.get("rank", ""),
                            take=params.get("n", ""), hold=params.get("hold", ""),
                            filters=split(params.get("where")), vetoes=split(params.get("veto")))


def rule_preview(spec) -> dict:
    """{'citations':[…],'survivor':str} — the KNOWN-DEAD wall for a composed rule, BEFORE any run.
    Both are pure and DB-free: the ledger already answers most rules, and saying so up front is
    the honest product."""
    try:
        from src.automation.rule_lab import survivor_note, trigger_citations
        return {"citations": list(trigger_citations(spec) or []), "survivor": survivor_note(spec) or ""}
    except Exception:  # noqa: BLE001
        return {"citations": [], "survivor": ""}


def rule_demo_verdict() -> dict:
    """A deterministic SYNTHETIC verdict so an anonymous visitor sees the shape of an answer.
    Flagged `sample` everywhere it renders; its own provenance field says so. Mirrors the classic
    demo numbers exactly so the two surfaces cannot tell different stories."""
    try:
        from src.automation.rule_lab import build_verdict, compile_rule
        spec = compile_rule("SELECT liquid500 WHERE not_extended RANK BY mom12 TAKE 25 HOLD quarterly")
        nums = {"net_retvol": 0.61, "gross_retvol": 1.02, "flat_retvol": 0.84,
                "half1": 0.55, "half2": 0.66, "placebo_p95": 0.40, "observed": 0.61,
                "emp_p": 0.02, "bench_net": 0.89, "capacity_inr": None,
                "maxdd": -0.41, "ann_cost_pct": 6.0, "turnover": 0.38}
        return build_verdict(spec, nums, prereg_ref="demo — synthetic numbers, not a real run",
                             provenance={"env": "demo-synthetic"}).to_dict()
    except Exception:  # noqa: BLE001
        return {}


def blocking_models() -> list:
    """[(key, verbatim_ledger_row)] — the published failure ledger's BLOCKING rows. These are the
    approaches recorded dead; a rule that resembles one is answered before it is run."""
    try:
        from src.automation.rule_lab import BLOCKING_ROWS
        return sorted((k, v) for k, v in dict(BLOCKING_ROWS).items())
    except Exception:  # noqa: BLE001
        return []


# ── replay any date (source: the real /v1 API, in-process) ───────────────────────────
_V1_CLIENT: list = []
_SYM_OK = re.compile(r"^[A-Za-z0-9&\-]{1,20}$")


def _v1(path: str) -> dict:
    """GET the real `/v1` sub-app in-process with the demo key. THIS is the point-in-time proof:
    the same public API a subscriber would call, asked for a past date. Client cached per process."""
    try:
        from src.core.settings import settings
        key = (settings.hermes_v1_dev_key or "").strip()
    except Exception:  # noqa: BLE001
        key = (os.environ.get("HERMES_V1_DEV_KEY") or "").strip()
    if not key:
        return {"status": 0, "error": "no-key"}
    try:
        if not _V1_CLIENT:
            from fastapi.testclient import TestClient
            from src.api.v1 import build_app
            _V1_CLIENT.append(TestClient(build_app(), raise_server_exceptions=False))
        c = _V1_CLIENT[-1]
        r = c.get(path, headers={"X-API-Key": key})
        if r.status_code == 401:
            try:
                os.environ.setdefault("HERMES_V1_DEV_KEY", key)
                from src.api.v1.keys import seed_dev_key
                seed_dev_key()
                r = c.get(path, headers={"X-API-Key": key})
            except Exception:  # noqa: BLE001
                pass
        try:
            return {"status": r.status_code, "json": r.json()}
        except Exception:  # noqa: BLE001
            return {"status": r.status_code, "text": r.text[:2000]}
    except Exception as exc:  # noqa: BLE001
        return {"status": 0, "error": type(exc).__name__}


def replay(sym: str, as_of: str) -> dict:
    """{'symbol','as_of','credibility','attention','universe'} — the three raw API envelopes,
    verbatim. Nothing is reshaped: the envelope IS the evidence."""
    s = (sym or "").strip().upper()[:20]
    if not _SYM_OK.match(s):
        s = ""
    d = (as_of or "").strip()[:10]
    out = {"symbol": s, "as_of": d, "credibility": None, "attention": None, "universe": None}
    if not d:
        return out
    if s:
        out["credibility"] = _v1(f"/securities/{s}/credibility?as_of={d}")
    out["attention"] = _v1(f"/attention?as_of={d}")
    out["universe"] = _v1(f"/universe?as_of={d}")
    return out


def replay_facts(sym: str, as_of: str) -> dict:
    """The CHEAP subset for the Today-page card: universe size + mechanism on the date, and the
    knowable clock for one symbol. Every key is optional — the card teaches rather than guesses."""
    r = replay(sym, as_of)
    f = {"symbol": r.get("symbol") or "", "as_of": r.get("as_of") or ""}
    uni = ((r.get("universe") or {}).get("json") or {})
    data = uni.get("data") if isinstance(uni.get("data"), dict) else uni
    if isinstance(data, dict):
        for k in ("universe_on_as_of", "count", "n"):
            if isinstance(data.get(k), int):
                f["universe_n"] = data[k]
                break
        f["mechanism"] = data.get("as_of_mechanism") or ""
    cred = ((r.get("credibility") or {}).get("json") or {})
    pit = cred.get("pit") if isinstance(cred.get("pit"), dict) else {}
    if isinstance(pit, dict):
        f["knowable_from"] = pit.get("knowable_from") or ""
        f["knowable_basis"] = pit.get("knowable_basis") or ""
    return {k: v for k, v in f.items() if v not in (None, "")} | {
        "symbol": f.get("symbol", ""), "as_of": f.get("as_of", "")}


def _selftest() -> int:
    ok = 0
    g = glossary_entries()
    assert len(g) >= 100, f"glossary parse looks degenerate: {len(g)}"
    assert {"name", "family", "body"} <= set(g[0]), g[0].keys()
    ok += 1
    fams = glossary_families()
    assert len(fams) >= 5 and sum(len(v) for _k, v in fams) == len(g)
    ok += 1
    pages = strategy_pages()
    assert len(pages) >= 10, f"strategy pages: {len(pages)}"
    assert all(p["title"] for p in pages)
    ok += 1
    doc = strategy_doc(pages[0]["slug"])
    assert doc and doc["text"], pages[0]
    ok += 1
    # the sanitizer must beat the classic gap: multi-letter + hyphenated + 4-digit ids
    dirty = ("Ramana decided (D138, S164BB) on 2026-07-16BB per S155-e and S1234; see `3d13d97a1b2`. "
             "\nA clean line about delivery.")
    clean = public_text(dirty)
    for tok in ("Ramana", "D138", "S164BB", "S155-e", "S1234", "2026-07-16BB", "3d13d97a1b2"):
        assert tok not in clean, (tok, clean)
    assert "clean line about delivery" in clean
    ok += 1
    assert strategy_doc("../../PROJECT_STATE") == {} and strategy_doc("nope") == {}
    ok += 1
    v = validation()
    assert set(v) == {"present", "path", "rows", "n_runs"}
    ok += 1
    vocab = rule_vocabulary()
    assert vocab and "liquid500" in vocab["universes"]
    ok += 1
    spec = rule_spec_from_query({"u": "liquid500", "rank": "mom12", "n": "25", "hold": "quarterly",
                                "where": "not_extended"})
    assert rule_query_from_spec(spec) == {"u": "liquid500", "rank": "mom12", "n": "25",
                                          "hold": "quarterly", "where": "not_extended"}
    ok += 1
    assert len(blocking_models()) >= 10
    ok += 1
    print(f"trust_reads selftest OK ({ok} checks) — glossary {len(g)} terms / "
          f"{len(fams)} families · strategies {len(pages)} · research.db present={v['present']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_selftest())
