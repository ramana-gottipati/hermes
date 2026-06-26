"""Patearn SDK client (face #3). Thin HTTP client over `/v1`.

Strip-resistance (red-team): a MODELED value arrives from `/v1` as a dict
``{value, basis, lag_days}`` — NOT a bare scalar — so `pandas.json_normalize` explodes it
into `*.value`/`*.basis` columns and the caveat rides the data. `ProvenancedResult` keeps
`_provenance`/`_meta` and prints a freshness/disclaimer banner in its repr so a human in a
notebook sees the limits without reading the JSON.

Transport is pluggable: the default uses `requests` against `base_url`; tests inject an
in-process adapter (a FastAPI TestClient) so the SDK is verifiable without a live server —
all four faces still go through the same `/v1` contract.
"""
from __future__ import annotations

from typing import Callable, Optional

DEFAULT_BASE = "http://127.0.0.1:8000/v1"


class ProvenancedResult:
    """An envelope response: .data, .provenance, .meta, .ok, .banner(), .to_frame()."""

    def __init__(self, path: str, status: int, body: dict):
        self.path = path
        self.status = status
        self.raw = body or {}
        self.data = self.raw.get("data")
        self.provenance = self.raw.get("_provenance", {}) or {}
        self.meta = self.raw.get("_meta", {}) or {}
        self.entitlement = self.raw.get("_entitlement", {}) or {}
        self.problem = self.raw if status >= 400 else None

    @property
    def ok(self) -> bool:
        return self.status < 400

    def modeled_classes(self) -> list:
        return [k for k, v in self.provenance.items()
                if isinstance(v, dict) and v.get("basis") == "MODELED"]

    def banner(self) -> str:
        """The strip-resistant one-liner a human/notebook sees (freshness + caveat)."""
        m = self.meta
        bits = [f"patearn {self.path}"]
        if m.get("coverage"):
            bits.append(str(m["coverage"]))
        mc = self.modeled_classes()
        if mc:
            bits.append("availability MODELED: " + ", ".join(mc))
        if m.get("methodology_version"):
            bits.append("methodology " + str(m["methodology_version"]))
        if m.get("disclaimer"):
            bits.append(str(m["disclaimer"]))
        return " · ".join(bits)

    def __repr__(self) -> str:
        if self.problem:
            return f"<PatearnResult {self.status} problem: {self.problem.get('title')}>"
        return f"<PatearnResult {self.path} status={self.status}>\n  ⓘ {self.banner()}"

    def to_frame(self, rows_key: Optional[str] = None):
        """Optional pandas view. Keeps provenance in `df.attrs`; a MODELED cell stays a dict
        so json_normalize surfaces its basis as a column (the caveat is not strippable)."""
        try:
            import pandas as pd
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("pandas not installed; use .data / .raw") from e
        payload = self.data
        if rows_key and isinstance(payload, dict):
            payload = payload.get(rows_key)
        rows = payload if isinstance(payload, list) else [payload]
        df = pd.json_normalize(rows)
        df.attrs["_provenance"] = self.provenance
        df.attrs["_meta"] = self.meta
        df.attrs["banner"] = self.banner()
        return df


class PatearnClient:
    """A thin client over `/v1`. `request_fn(method, path, headers, params) -> (status, json)`
    overrides the transport (tests pass a TestClient adapter)."""

    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE,
                 request_fn: Optional[Callable] = None, timeout: int = 30):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._request_fn = request_fn

    def _call(self, path: str, params: Optional[dict] = None) -> ProvenancedResult:
        headers = {"X-API-Key": self.api_key, "Accept": "application/json"}
        if self._request_fn is not None:
            status, body = self._request_fn("GET", path, headers, params)
        else:
            import requests  # lazy — the SDK imports without requests installed
            r = requests.get(self.base_url + path, headers=headers, params=params, timeout=self.timeout)
            try:
                body = r.json()
            except ValueError:
                body = {}
            status = r.status_code
        return ProvenancedResult(path, status, body)

    # ── the typed surface (mirrors the /v1 endpoints) ──
    def health(self) -> ProvenancedResult:
        return self._call("/meta/health")

    def coverage(self) -> ProvenancedResult:
        return self._call("/coverage")

    def universe(self, as_of: Optional[str] = None) -> ProvenancedResult:
        return self._call("/universe", {"as_of": as_of} if as_of else None)

    def provenance_registry(self) -> ProvenancedResult:
        return self._call("/provenance/registry")

    def credibility(self, symbol: str) -> ProvenancedResult:
        return self._call(f"/securities/{symbol}/credibility")

    def attention(self, limit: int = 6) -> ProvenancedResult:
        return self._call("/attention", {"limit": limit})


# ── selftest (in-process via a TestClient transport; no live server) ──────────
def _selftest() -> None:
    from fastapi.testclient import TestClient
    from src.api.v1 import build_app
    from src.api.v1.keys import seed_dev_key
    from src.api.v1.selftest import _teardown

    _teardown()
    try:
        key = seed_dev_key()
        tc = TestClient(build_app(), raise_server_exceptions=False)

        def adapter(method, path, headers, params):
            r = tc.request(method, path, headers=headers, params=params)
            try:
                return r.status_code, r.json()
            except ValueError:
                return r.status_code, {}

        cli = PatearnClient(key, request_fn=adapter)

        cov = cli.coverage()
        assert cov.ok and cov.status == 200, cov.status
        assert "patearn /coverage" in cov.banner() and "not investment advice" in cov.banner().lower() \
            or "performance claim" in cov.banner().lower(), cov.banner()
        assert isinstance(cov.provenance, dict) and "survivorship" in cov.provenance

        # a bad key surfaces a problem, not a silent empty
        bad = PatearnClient("nope", request_fn=adapter).coverage()
        assert not bad.ok and bad.problem is not None and bad.status == 401

        # credibility is DESCRIPTIVE (served 200) — §C falsified the alpha; the banner carries the
        # no-validated-edge caveat, and on the stub the value is a typed absence (no bare null).
        cred = cli.credibility("RELIANCE")
        assert cred.ok and cred.status == 200, cred.status
        assert "no validated return edge" in cred.banner().lower(), cred.banner()

        # registry resolvable; to_frame keeps provenance in attrs (if pandas present)
        reg = cli.provenance_registry()
        assert reg.ok
        try:
            import pandas  # noqa: F401
            df = reg.to_frame(rows_key="registry")
            assert df.attrs.get("_meta") is not None and len(df) >= 25
            framed = True
        except (ImportError, RuntimeError):
            framed = False

        print(f"sdk selftest: OK  (banner surfaces caveat · bad-key->problem · credibility descriptive/no-edge · "
              f"to_frame{' ok' if framed else ' skipped(no pandas)'})")
    finally:
        _teardown()


if __name__ == "__main__":
    _selftest()
