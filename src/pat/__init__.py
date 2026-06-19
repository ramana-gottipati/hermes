"""Pat — the natural-language guided-search assistant for the Patearn web tool.

Pat lives as a tab in the dashboard (``/dash/pat``). It turns a plain-English
question into a data pull via tap-to-answer chips, and explains what every
metric / column / value in the data actually means.

Layout (built in phases):
  - ``glossary``  — the data dictionary that GROUNDS every explanation. This is
                    the asset: write the data in plain words once, Pat reads it
                    at question-time. Live numbers always come fresh from the DB.
  - ``flows``     — (next) the question -> chip -> parameter tree + the SQL
                    templates each flow compiles to. The tap path is pure
                    Python/SQL (zero LLM).
  - ``engine``    — (next) runs a flow, and calls Gemini Flash (via
                    ``src.core.llm_router``) ONLY at the edges: free-text
                    understanding + phrasing a glossary entry conversationally.

Cost posture: the tap-through path is deterministic and free. Gemini Flash is
the only model ever used; Claude is never called from Pat.
"""

from src.pat.glossary import GLOSSARY, FAMILIES, get, find, family

__all__ = ["GLOSSARY", "FAMILIES", "get", "find", "family"]
