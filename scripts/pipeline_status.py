"""One-shot status of the data-engine backfills (enrichment + Concall Intelligence).
Read-only. Run on the VPS:
    cd /opt/hermes && PYTHONPATH=/opt/hermes .venv/bin/python scripts/pipeline_status.py
"""
from src.core.db import get_conn


def main() -> None:
    with get_conn() as c:
        q = lambda s: c.execute(s).fetchone()[0]

        eq = q("SELECT COUNT(*) FROM company_profile WHERE is_equity=1")
        en = q("SELECT COUNT(*) FROM company_profile WHERE business_brief IS NOT NULL AND length(business_brief)>0")
        unv = q("SELECT COUNT(*) FROM company_profile WHERE unverified=1")
        pct = (100 * en // eq) if eq else 0
        print(f"ENRICHMENT  : {en}/{eq} equities ({pct}%)  pending={eq - en}  unverified={unv}")

        tot = q("SELECT COUNT(*) FROM concalls")
        syms = q("SELECT COUNT(DISTINCT symbol) FROM concalls")
        done = q("SELECT COUNT(*) FROM concalls WHERE extract_status='DONE'")
        pend = q("SELECT COUNT(*) FROM concalls WHERE parse_status='OK' AND transcript_url<>'' "
                 "AND (extract_status IS NULL OR extract_status='FAIL')")
        print(f"CCI CORPUS  : {tot} concalls / {syms} symbols  extracted={done}  pending={pend}")

        gst = dict(c.execute("SELECT status, COUNT(*) FROM concall_guidance GROUP BY status").fetchall())
        settled = sum(gst.get(k, 0) for k in ("MET", "MISSED", "PARTIAL"))
        print(f"CCI PROMISES: {sum(gst.values())} total  settled={settled} "
              f"(MET={gst.get('MET', 0)} MISSED={gst.get('MISSED', 0)} PARTIAL={gst.get('PARTIAL', 0)})  "
              f"OPEN={gst.get('OPEN', 0)}  ONGOING={gst.get('ONGOING', 0)}")

        sc = q("SELECT COUNT(DISTINCT symbol) FROM concall_scores")
        tiers = dict(c.execute("SELECT tier, COUNT(DISTINCT symbol) FROM concall_scores "
                               "WHERE tier IS NOT NULL GROUP BY tier").fetchall())
        print(f"CCI SCORES  : {sc} symbols scored  tiers={tiers}")


if __name__ == "__main__":
    main()
