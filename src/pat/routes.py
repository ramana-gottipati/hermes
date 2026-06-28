"""Pat's own FastAPI router — deliberately OUT of ``dashboard.py``.

The ``/dash/pat`` page route lives in ``dashboard.py`` (a heavily contended file
owned by parallel work). Pat's JSON side-channels live here instead and are
mounted from ``main.py`` (``app.include_router``), so the page file never has to
change to add a Pat backend endpoint.

Today this is the feedback channel behind the 👍/👎 UI. Writes go through
``src.pat.feedback`` (self-contained store); this layer only validates and
shapes the request. No LLM, no SQL here.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.pat import feedback
from src.pat import boards

router = APIRouter(prefix="/pat", tags=["pat"])


class FeedbackIn(BaseModel):
    verdict: str = Field(..., description="'up' or 'down'")
    query: str = Field("", max_length=500)
    flow: str = Field("", max_length=40)
    params: dict = Field(default_factory=dict)
    source: str | None = Field(None, max_length=40)


class CorrectionIn(BaseModel):
    id: int | None = Field(None, description="row id from the prior 👎 POST, to enrich it")
    expected: str | None = Field(None, max_length=1000, description="what the analyst wanted")
    what_wrong: str | None = Field(None, max_length=500)
    # Fallback context, used only if `id` is missing so the correction isn't lost:
    query: str = Field("", max_length=500)
    flow: str = Field("", max_length=40)
    params: dict = Field(default_factory=dict)
    source: str | None = Field(None, max_length=40)


@router.post("/feedback")
def submit_feedback(fb: FeedbackIn) -> dict:
    """Record a 👍/👎 on a Pat answer. Returns the new row id (for the 👎 follow-up)."""
    fid = feedback.record(
        verdict=fb.verdict, query=fb.query, flow=fb.flow,
        params=fb.params, source=fb.source,
    )
    return {"ok": fid is not None, "id": fid}


@router.post("/feedback/correct")
def submit_correction(c: CorrectionIn) -> dict:
    """Attach 'what you expected' to a prior 👎 (the gold signal).

    Enriches the existing row by id; if the id is missing/stale, inserts a fresh
    'down' row carrying the correction so the signal is never dropped.
    """
    if c.id:
        if feedback.update(c.id, expected_text=c.expected, what_wrong=c.what_wrong):
            return {"ok": True, "id": c.id}
    fid = feedback.record(
        verdict="down", query=c.query, flow=c.flow, params=c.params,
        what_wrong=c.what_wrong, expected_text=c.expected,
        source=c.source or "correction",
    )
    return {"ok": fid is not None, "id": fid}


# ── saved BOARDS (name any NL query / screen, reload it; power the workbench) ──
class BoardIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=60)
    query: str = Field("", max_length=500)
    flow: str = Field("", max_length=40)
    params: dict = Field(default_factory=dict)
    kind: str = Field("pat", max_length=10)


@router.post("/board/save")
def board_save(b: BoardIn) -> dict:
    """Pin a named board (NL query or screen). Upserts by (name, kind)."""
    bid = boards.save(name=b.name, query=b.query, flow=b.flow, params=b.params, kind=b.kind)
    return {"ok": bid is not None, "id": bid}


@router.post("/board/delete")
def board_delete(b: BoardIn) -> dict:
    """Delete a board by name + kind."""
    return {"ok": boards.delete(b.name, kind=b.kind)}


@router.get("/boards")
def board_list(kind: str = "") -> dict:
    """List saved boards (optionally filtered by kind)."""
    return {"boards": boards.list_boards(kind=kind or None)}
