"""Resilient CCI extraction drain — keep extracting pending concalls in batches,
riding out Gemini 503 capacity spikes until the queue is empty.

Order is `--breadth` (round-robin recent-first across symbols): on a finite Gemini
budget every symbol's most-recent call is extracted before any symbol's second, so
limited credit buys COVERAGE for the full-universe credibility ranking instead of
exhaustive 2019 depth on a few names. rn is recomputed each batch, so the budget is
the natural depth cap — yet it still drains to 0 if the budget allows. (Swap to
`--oldest` only when the goal is building settled track records, not breadth.)

Each `concall_extract --pending` batch stops itself after 5 consecutive failures
(a sustained spike); this loop cools off and resumes, so a transient Google-side
outage just slows the backfill instead of needing a human to relaunch it. 503s are
unbilled, so the wasted retries during a spike cost nothing. Idempotent throughout.

Operational helper (not part of the app); run on the VPS WITH ABSOLUTE PATHS (the
`cd X && A & B` form leaves B in $HOME -> "no such file"):
    PYTHONPATH=/opt/hermes nohup /opt/hermes/.venv/bin/python \
        /opt/hermes/scripts/cci_drain_loop.py >/var/log/hermes-cci-drain.log 2>&1 &
"""
import subprocess
import time

from src.core.db import get_conn

PY = "/opt/hermes/.venv/bin/python"
CWD = "/opt/hermes"
BATCH = 240          # LLM calls per batch before a fresh pending-check
WORKERS = 8          # parallel extraction workers per batch (network-bound → near-linear)
ROUNDS = 300         # hard cap — high so it can co-run with a long broad-ingest feeding the queue
COOLOFF = 30         # seconds between batches; the batch's own circuit-breaker handles a spike


def pending() -> int:
    """Transcripts still awaiting extraction — mirrors concall_extract.pending_rows."""
    with get_conn() as c:
        return c.execute(
            "SELECT COUNT(*) FROM concalls WHERE parse_status='OK' AND transcript_url<>'' "
            "AND (extract_status IS NULL OR extract_status='FAIL')").fetchone()[0]


MAX_HARD_FAILS = 5   # consecutive non-zero exits = a real crash (not a 503 spike) → abort


def main() -> None:
    empty = 0
    hard_fail = 0
    for rnd in range(1, ROUNDS + 1):
        p = pending()
        if p == 0:
            empty += 1
            print(f"[drain-loop] round {rnd}: queue empty ({empty}/10 idle checks)", flush=True)
            if empty >= 10:                 # ~5 min idle → a feeding ingest has finished + drained
                print("[drain-loop] COMPLETE", flush=True)
                return
            time.sleep(COOLOFF)
            continue
        empty = 0
        print(f"[drain-loop] round {rnd}: {p} pending", flush=True)
        rc = subprocess.run([PY, "-m", "src.automation.concall_extract", "--pending",
                             "--breadth", "--max-calls", str(BATCH), "--workers", str(WORKERS)],
                            cwd=CWD).returncode
        # The batch's own circuit-breaker exits 0 on a 503 spike; a NON-zero exit means a hard
        # crash (bad invocation / missing module / auth) the breaker can't catch — don't busy-spin
        # 300× on it (which could also burn billed calls before each crash). Back off, then abort.
        if rc != 0:
            hard_fail += 1
            print(f"[drain-loop] round {rnd}: extractor exited rc={rc} "
                  f"(hard failure {hard_fail}/{MAX_HARD_FAILS})", flush=True)
            if hard_fail >= MAX_HARD_FAILS:
                print("[drain-loop] ABORT — consecutive hard failures (not a 503 spike); "
                      "check the extractor invocation / auth", flush=True)
                return
            time.sleep(COOLOFF * (2 ** hard_fail))   # exponential backoff on a real crash
            continue
        hard_fail = 0
        time.sleep(COOLOFF)
    print("[drain-loop] hit round cap — rerun to continue", flush=True)


if __name__ == "__main__":
    main()
