"""Patearn Python/Excel SDK — face #3 of "one bus, four faces".

A thin, dependency-light client over the REST `/v1` layer. It does not re-implement any
logic; it calls `/v1` and returns the provenance-stamped envelope as a `ProvenancedResult`
whose repr/banner SURFACES the freshness + caveat (so a notebook user can't miss it) and
whose `.to_frame()` keeps provenance attached + folds MODELED `{value,basis,lag_days}`
cells into columns (so a pandas flatten can't strip the caveat — the red-team's fix).
"""
from src.api.sdk.client import PatearnClient, ProvenancedResult

__all__ = ["PatearnClient", "ProvenancedResult"]
