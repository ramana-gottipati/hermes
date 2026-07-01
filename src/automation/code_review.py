"""GLM-5.2 code reviewer — headless, scheduled, REPORT-ONLY.

WHAT THIS IS
  A read-only code reviewer that runs on a timer. Each run it sends a slice of
  the Hermes source to Z.ai's GLM-5.2 (via the Anthropic-compatible endpoint),
  asks for a correctness + quality review, writes the findings to a dated
  markdown file under data/code_reviews/, and pushes a short summary to the
  owner on Telegram. It NEVER modifies code.

  "Report only" is a deliberate ceiling: the VPS runs live services (bot, API,
  scoring) and its git tree is shared by parallel sessions, so an auto-fixer
  editing the working tree would be unsafe. Findings land in Telegram + a file;
  a human decides what to act on.

WHY GLM CONFIG IS READ FROM ITS OWN ENV (not src.core.settings / the shared
  Anthropic client):
  src.core.llm.client() talks to the REAL Anthropic API and serves the
  production bot. This module builds its OWN Anthropic client with base_url +
  key passed explicitly, read from GLM_* env vars. We must NOT set a global
  ANTHROPIC_BASE_URL on the VPS — that would silently redirect the bot's real
  Anthropic traffic to Z.ai. Keeping the config local also makes deploy purely
  additive: no edit to the shared settings.py on the VPS's dirty tree.

WHAT GETS REVIEWED EACH RUN (--mode):
  auto  (default) : if the working tree has uncommitted changes, review the diff
                    (what's actively being worked on); else review the next
                    rotating batch of source files so the whole tree is swept
                    over many nights.
  diff            : only the uncommitted git diff (+ new untracked files).
  sweep           : only the next rotating batch (cursor in
                    data/code_reviews/.sweep_cursor).
  files F1 F2 ...  : review the given paths.

COST
  GLM-5.2's free quota is finite, so every run is capped (CODE_REVIEW_MAX_BYTES /
  CODE_REVIEW_MAX_FILES). This path never touches Anthropic, so it adds zero to
  the ~Rs300/mo Anthropic budget.

Run:
  python -m src.automation.code_review                  # auto mode, send report
  python -m src.automation.code_review --dry-run        # review + print, no Telegram
  python -m src.automation.code_review --mode sweep
  python -m src.automation.code_review --mode files --files src/web/cockpit.py
Invoked by the hermes-code-review systemd timer (nightly).
"""

import argparse
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Importing settings first triggers load_dotenv(override=True), so the GLM_* and
# TELEGRAM_* values from .env are present in os.environ before we read them.
from src.core.settings import settings
from src.automation.digest import _send

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("hermes.code_review")

ROOT = Path(__file__).resolve().parents[2]          # project root (parent of src/)
REPORT_DIR = ROOT / "data" / "code_reviews"
CURSOR_PATH = REPORT_DIR / ".sweep_cursor"

# Files/dirs never worth sending (vendored, generated, secrets, binaries).
_SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "data",
              "research", "resources", ".idea", ".vscode"}
_SKIP_SUFFIXES = {".pyc", ".db", ".sqlite", ".xlsx", ".csv", ".parquet", ".png",
                  ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".lock"}

SYSTEM_PROMPT = (
    "You are a senior Python engineer reviewing a production FastAPI + SQLite "
    "personal-finance/markets application (Indian equities). Review ONLY the code "
    "you are shown. Prioritise, in order: (1) correctness bugs and crashes, "
    "(2) security / secret-leak / injection issues, (3) resource leaks (DB "
    "connections, file handles, requests sessions) and unhandled exceptions, "
    "(4) concrete simplifications or efficiency wins. For each finding give: a "
    "severity tag [CRITICAL]/[HIGH]/[MEDIUM]/[LOW], the file and approximate line, "
    "a one-line description, and a short fix suggestion. Cite file:line — do NOT "
    "paste large rewrites. If a file looks fine, say so in one line. Be concise; "
    "this report is read on a phone. Output GitHub-flavoured markdown. End with a "
    "short 'Top 3 to fix first' list."
)


# --- GLM client + config ---------------------------------------------------
def _glm_config() -> dict:
    """Read the reviewer's GLM/Z.ai config from env (see module docstring for why
    this is isolated from the shared Anthropic client)."""
    return {
        "api_key": os.getenv("GLM_API_KEY", "").strip(),
        "base_url": os.getenv("GLM_BASE_URL", "https://api.z.ai/api/anthropic").strip(),
        "model": os.getenv("GLM_MODEL", "glm-5.2").strip(),
        "max_bytes": int(os.getenv("CODE_REVIEW_MAX_BYTES", "120000")),
        "max_files": int(os.getenv("CODE_REVIEW_MAX_FILES", "20")),
        "max_tokens": int(os.getenv("CODE_REVIEW_MAX_TOKENS", "4000")),
        "timeout": float(os.getenv("CODE_REVIEW_TIMEOUT", "180")),
    }


def _review_with_glm(payload: str, cfg: dict) -> tuple[str, dict]:
    """Single review call to GLM-5.2. Returns (markdown_text, usage_dict).

    Uses its OWN Anthropic client (explicit base_url + key) so it can never
    affect the production bot's real-Anthropic traffic."""
    from anthropic import Anthropic

    client = Anthropic(api_key=cfg["api_key"], base_url=cfg["base_url"],
                       timeout=cfg["timeout"])
    resp = client.messages.create(
        model=cfg["model"],
        max_tokens=cfg["max_tokens"],
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": payload}],
    )
    text = "".join(getattr(b, "text", "") for b in resp.content) or "(empty response)"
    usage = {
        "input_tokens": getattr(getattr(resp, "usage", None), "input_tokens", None),
        "output_tokens": getattr(getattr(resp, "usage", None), "output_tokens", None),
    }
    return text, usage


# --- file selection --------------------------------------------------------
def _run_git(args: list[str]) -> str:
    try:
        r = subprocess.run(["git", *args], cwd=str(ROOT),
                           capture_output=True, text=True, timeout=30)
        return r.stdout if r.returncode == 0 else ""
    except Exception as e:  # noqa: BLE001 — git missing / not a repo → caller falls back
        log.warning("git %s failed: %s", " ".join(args), e)
        return ""


def _is_reviewable(rel: str) -> bool:
    parts = Path(rel).parts
    if any(p in _SKIP_DIRS for p in parts):
        return False
    if Path(rel).suffix in _SKIP_SUFFIXES:
        return False
    return True


def _all_sources() -> list[Path]:
    """All reviewable Python sources under src/, sorted for a stable sweep order."""
    return sorted(p for p in (ROOT / "src").rglob("*.py")
                  if p.is_file() and _is_reviewable(str(p.relative_to(ROOT))))


def _read_cursor() -> int:
    try:
        return int(CURSOR_PATH.read_text().strip())
    except Exception:
        return 0


def _write_cursor(idx: int) -> None:
    try:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        CURSOR_PATH.write_text(str(idx))
    except Exception as e:  # noqa: BLE001
        log.warning("could not persist sweep cursor: %s", e)


def _block(rel: str, content: str) -> str:
    lang = "python" if rel.endswith(".py") else ""
    return f"\n### `{rel}`\n```{lang}\n{content}\n```\n"


def select_payload(mode: str, files: list[str], cfg: dict) -> tuple[str, str]:
    """Return (payload_text, human_description) for this run, capped to budget."""
    max_bytes, max_files = cfg["max_bytes"], cfg["max_files"]

    # explicit files ---------------------------------------------------------
    if mode == "files":
        chosen = [f for f in files if (ROOT / f).is_file()]
        return _payload_from_files(chosen, max_bytes), f"explicit files: {', '.join(chosen) or '(none)'}"

    # diff -------------------------------------------------------------------
    if mode in ("diff", "auto"):
        diff = _run_git(["diff", "HEAD"]).strip()
        untracked = [f for f in _run_git(["ls-files", "--others", "--exclude-standard"]).split()
                     if _is_reviewable(f)]
        if diff or untracked:
            parts = []
            desc_bits = []
            if diff:
                parts.append("## Uncommitted diff (`git diff HEAD`)\n```diff\n"
                             + diff[:max_bytes] + "\n```\n")
                desc_bits.append("working-tree diff")
            if untracked:
                new_blocks = _payload_from_files(untracked[:max_files],
                                                 max(0, max_bytes - len(parts[0] if parts else "")))
                if new_blocks:
                    parts.append("## New (untracked) files\n" + new_blocks)
                desc_bits.append(f"{len(untracked)} new file(s)")
            return "\n".join(parts), "review of " + " + ".join(desc_bits)
        if mode == "diff":
            return "", "no uncommitted changes to review"
        # auto with a clean tree → fall through to sweep

    # sweep ------------------------------------------------------------------
    sources = _all_sources()
    if not sources:
        return "", "no source files found"
    start = _read_cursor() % len(sources)
    batch = sources[start:start + max_files]
    rels = [str(p.relative_to(ROOT)) for p in batch]
    _write_cursor((start + len(batch)) % len(sources))
    payload = _payload_from_files(rels, max_bytes)
    return payload, (f"rotating sweep, files {start + 1}-{start + len(batch)} of "
                     f"{len(sources)}: {', '.join(rels)}")


def _payload_from_files(rels: list[str], budget: int) -> str:
    out, used, included, skipped = [], 0, 0, 0
    for rel in rels:
        try:
            content = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        block = _block(rel, content)
        if used + len(block) > budget and included > 0:
            skipped += 1
            continue
        out.append(block)
        used += len(block)
        included += 1
    if skipped:
        out.append(f"\n_({skipped} further file(s) omitted to stay within the "
                   f"per-run size cap.)_\n")
    return "".join(out)


# --- report + delivery -----------------------------------------------------
def _destinations() -> list[int]:
    """Owner DM(s) from telegram_allowed_user_ids — code reviews go to the owner,
    not the public patearn group."""
    ids = [x.strip() for x in (settings.telegram_allowed_user_ids or "").split(",") if x.strip()]
    return [int(x) for x in ids if x.lstrip("-").isdigit()]


def _esc(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _write_report(desc: str, model: str, review: str, usage: dict, ts: datetime) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"review-{ts.strftime('%Y-%m-%d-%H%M')}.md"
    header = (f"# Hermes code review — {ts.astimezone().strftime('%d %b %Y, %I:%M %p')}\n\n"
              f"- **Model:** `{model}` (Z.ai GLM)\n"
              f"- **Scope:** {desc}\n"
              f"- **Tokens:** in={usage.get('input_tokens')} out={usage.get('output_tokens')}\n\n"
              f"---\n\n")
    path.write_text(header + review, encoding="utf-8")
    return path


def _telegram_summary(desc: str, review: str, path: Path, ts: datetime) -> str:
    body = review.strip()
    if len(body) > 3500:
        body = body[:3500] + "\n…(truncated — full report on the VPS)"
    return (f"🔎 <b>Hermes code review — {ts.astimezone().strftime('%d %b, %I:%M %p')}</b>\n"
            f"<i>{_esc(desc)}</i>\n\n"
            f"{_esc(body)}\n\n"
            f"<i>Full report:</i> <code>{_esc(str(path))}</code>")


# --- run -------------------------------------------------------------------
def run(mode: str = "auto", files: list[str] | None = None, dry_run: bool = False) -> str | None:
    cfg = _glm_config()
    if not cfg["api_key"]:
        log.warning("GLM_API_KEY not set — skipping review. Add it to %s "
                    "(get a key at https://z.ai/manage-apikey).", ROOT / ".env")
        return None

    payload, desc = select_payload(mode, files or [], cfg)
    if not payload.strip():
        log.info("nothing to review (%s).", desc)
        return None
    log.info("reviewing: %s (%d chars to GLM)", desc, len(payload))

    try:
        review, usage = _review_with_glm(payload, cfg)
    except Exception as e:  # noqa: BLE001 — network / quota / endpoint errors
        log.exception("GLM review call failed: %s", e)
        return None

    ts = datetime.now(timezone.utc)
    path = _write_report(desc, cfg["model"], review, usage, ts)
    log.info("wrote report: %s (tokens in=%s out=%s)", path,
             usage.get("input_tokens"), usage.get("output_tokens"))

    if dry_run:
        print("\n===== GLM-5.2 CODE REVIEW (dry-run, not sent) =====\n")
        print(f"scope: {desc}\n")
        print(review)
        return review

    if not settings.telegram_bot_token:
        log.warning("TELEGRAM_BOT_TOKEN not set — report written to %s but not sent.", path)
        return review
    dests = _destinations()
    if not dests:
        log.warning("no TELEGRAM_ALLOWED_USER_IDS — report written to %s but not sent.", path)
        return review

    msg = _telegram_summary(desc, review, path, ts)
    ok = all(_send(d, msg) for d in dests)
    log.info("telegram summary %s to %d destination(s)",
             "sent" if ok else "FAILED (will reappear next run)", len(dests))
    return review


def main() -> None:
    ap = argparse.ArgumentParser(description="GLM-5.2 code reviewer (report-only)")
    ap.add_argument("--mode", choices=["auto", "diff", "sweep", "files"], default="auto",
                    help="auto (diff if dirty else sweep) | diff | sweep | files")
    ap.add_argument("--files", nargs="*", default=[],
                    help="paths to review when --mode files")
    ap.add_argument("--dry-run", action="store_true",
                    help="review + write file + print, but do not send to Telegram")
    args = ap.parse_args()
    try:
        run(mode=args.mode, files=args.files, dry_run=args.dry_run)
    except Exception:
        log.exception("code_review run failed")


if __name__ == "__main__":
    main()
