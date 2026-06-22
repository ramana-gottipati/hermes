"""Explosive-move reverse-engineering research program.

A bottom-up, survivorship-safe event study over the Hermes NSE archive:
detect genuine explosive moves (day / week / month-sustained), walk back to
fingerprint the precursor state, mine recurring patterns, and validate hit /
success ratios out-of-sample.

Offline research only — never mutates the production hermes.db (opened read-only).
See docs/explosive-move-research.md for the running log and pattern library.
"""
