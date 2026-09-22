"""Canonical fingerprints for reconstructable JSON snapshots."""

from __future__ import annotations

import hashlib
import json


def canonical_json_fingerprint(snapshot: dict[str, object]) -> str:
    """Return a stable sha256 fingerprint for a JSON-compatible object."""

    if not isinstance(snapshot, dict):
        raise ValueError("Fingerprint snapshot must be a JSON object")
    try:
        canonical = json.dumps(
            snapshot,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise ValueError(
            "Fingerprint snapshot must contain only JSON-compatible values"
        ) from error
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"