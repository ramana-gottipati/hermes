"""`/v1` selftest — TestClient over the sub-app on the real local stub DB. Proves the
red-team blockers and tears down everything it seeded.

Run: python -m src.api.v1.selftest
"""
from __future__ import annotations

from src.core.db import get_conn


def _teardown():
    from src.api.v1.schema import ensure_schema
    with get_conn() as conn:
        ensure_schema(conn)
        for t in ("dev", "compliance-demo"):
            conn.execute("DELETE FROM v1_api_scopes WHERE tenant_id=?", (t,))
            conn.execute("DELETE FROM v1_api_keys   WHERE tenant_id=?", (t,))
            conn.execute("DELETE FROM v1_tenants    WHERE tenant_id=?", (t,))
        for k in ("pk_dev", "pk_comp"):
            conn.execute("DELETE FROM v1_usage     WHERE key_id=?", (k,))
            conn.execute("DELETE FROM v1_ratelimit WHERE key_id=?", (k,))


def run() -> None:
    from fastapi.testclient import TestClient
    from src.api.v1 import build_app
    from src.api.v1.keys import seed_dev_key, seed_compliance_key
    from src.api.v1 import envelope as E
    from src.automation import provenance as P

    _teardown()                                   # start clean
    try:
        dev_key = seed_dev_key()                  # research + compliance + data-feed
        comp = seed_compliance_key()              # compliance only
        app = build_app()
        c = TestClient(app, raise_server_exceptions=False)
        H = {"X-API-Key": dev_key}
        HC = {"X-API-Key": comp}

        # 1) auth fail-closed: missing / empty / bad key, and key-in-URL
        assert c.get("/coverage").status_code == 401, "missing key must 401"
        assert c.get("/coverage", headers={"X-API-Key": ""}).status_code == 401, "empty key must 401"
        assert c.get("/coverage", headers={"X-API-Key": "bogus"}).status_code == 401, "bad key must 401"
        assert c.get("/coverage?api_key=" + dev_key).status_code == 400, "key-in-URL must 400"

        # 2) the two-buyer split: compliance key reads the audit faces, is DENIED the research lenses
        assert c.get("/coverage", headers=HC).status_code == 200, "compliance can read coverage"
        assert c.get("/universe", headers=HC).status_code == 200, "compliance can read universe"
        assert c.get("/attention", headers=HC).status_code == 403, "compliance must NOT reach the research lenses"

        # 3) honest faces serve 200 with the envelope contract
        r = c.get("/coverage", headers=H)
        assert r.status_code == 200, r.text
        j = r.json()
        assert set(("data", "_provenance", "_meta", "_entitlement")) <= set(j), j.keys()
        assert isinstance(j["_meta"]["as_of"], dict), "_meta.as_of must be an OBJECT (no single global as-of)"
        assert "methodology_version" in j["_meta"] and "request_id" in j["_meta"]
        assert isinstance(j["_meta"]["degraded"], bool), "_meta.degraded must be a present, honest bool"
        assert "survivorship" in j["_provenance"]
        assert r.headers.get("X-Request-ID"), "request-id header present"
        assert r.headers.get("RateLimit-Limit"), "rate-limit headers present"

        # 4) registry resolvable; health ok
        assert c.get("/provenance/registry", headers=HC).status_code == 200
        assert c.get("/meta/health", headers=H).status_code == 200

        # 5) credibility/attention are DESCRIPTIVE (served 200, NOT gated) — §C falsified the alpha edge.
        #    on the 4-symbol stub credibility has no data -> TYPED ABSENCE, never bare null;
        #    and the payload MUST carry the no-edge / not-a-ranked-signal caveat.
        assert c.get("/attention", headers=H).status_code == 200, "attention served (descriptive)"
        rc = c.get("/securities/RELIANCE/credibility", headers=H)
        assert rc.status_code == 200, rc.text
        jc = rc.json()
        cred = jc["data"]["credibility"]
        assert (cred.get("available") is False) or ("track_record" in cred), cred
        note = (jc["data"].get("note") or "").lower()
        assert "no validated return edge" in note and "not a ranked" in note, "credibility must carry the no-edge caveat"

        # 6) metering: append-only usage rows were written for the dev key (incl. the 4xx)
        with get_conn() as conn:
            n = conn.execute("SELECT COUNT(*) c FROM v1_usage WHERE key_id='pk_dev'").fetchone()["c"]
        assert n >= 4, f"usage log should have rows (got {n})"

        # 7) MODELED value serialises NON-BARE (the un-strippable-caveat law)
        mv = E.modeled_value("2024-06-29", P.provenance_for("fundamentals_history", symbol="X",
                                                            as_of="2024-03-31", period_type="A"))
        assert isinstance(mv, dict) and mv["basis"] == "MODELED" and mv["lag_days"] == 90 \
            and "modeled" in (mv["display"] or "").lower(), mv

        # 8) RFC-7807 on a 401 too
        e401 = c.get("/coverage")
        assert e401.headers.get("content-type", "").startswith("application/problem+json")
        assert e401.json().get("status") == 401

        print("v1 selftest: OK  (auth fail-closed · two-buyer split · credibility descriptive/no-edge · "
              "metered · non-bare modeled · RFC-7807 · rate headers)")
    finally:
        _teardown()


if __name__ == "__main__":
    run()
