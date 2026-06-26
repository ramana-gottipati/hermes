"""Isolated v2 staging entrypoint — serves the trust surface live WITHOUT touching the
parallel-owned main.py.

Mounts the Coverage & Settlement ledger (`/dash/coverage`), the v2 design-system style guide
(`/dash/ui-kit`), and the full `/v1` service layer (`/v1/*`) on a standalone FastAPI app. This
is the gate-free way to run/demo/stage the v2 surface while the production 2-line hook into
main.py stays deferred (main.py is perpetually parallel-owned). It can also run as its own
uvicorn on a separate VPS port to put the surface in front of a buyer before the main.py
cut-over.

Run:  uvicorn src.api.preview_app:app --port 8799
Then: GET /  (→ /dash/coverage) · /dash/ui-kit · /v1/coverage (X-API-Key from --seed-dev)
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from src.web import ui_kit, coverage_view
from src.api.v1 import build_app

app = FastAPI(title="Patearn v2 (isolated staging surface)")
app.include_router(ui_kit.router)
app.include_router(coverage_view.router)
app.mount("/v1", build_app())


@app.get("/")
def _root():
    return RedirectResponse("/dash/coverage")


# seed a local dev key so /v1 is usable in a demo (idempotent; no-op if the DB is unavailable)
try:
    from src.api.v1.keys import seed_dev_key
    seed_dev_key()
except Exception:  # noqa: BLE001 — never block startup on the seed
    pass
