"""Dual-write contract: entity ``nfc_uid`` + ``nfc_tag_pool`` registry.

Physical tags may seed identity on first bind (NDEF / chip). After that,
SQLite is source of truth. Bind/unbind must update both the domain row and
the pool row in the same application action. Domain objects never FK back
to the pool (no circular references).
"""

from __future__ import annotations

from dataclasses import dataclass

from .shipment_tags import STATUS_AVAILABLE, STATUS_BOUND

SCAN_SOURCE_RESOLVE = "resolve"
SCAN_SOURCE_CHECK_IN = "check_in"
SCAN_SOURCE_BIND = "bind"
SCAN_SOURCE_CONFIRM_WRITE = "confirm_write"


@dataclass(frozen=True, slots=True)
class PoolBindTarget:
    """What the tag pool should record after a successful entity bind."""

    nfc_uid: str
    object_type: str
    object_id: str
    label: str | None = None
    status: str = STATUS_BOUND


def pool_should_align_on_resolve(
    *,
    pool_status: str | None,
    pool_bound_object_id: str | None,
    pool_bound_object_type: str | None,
    resolved_object_id: str,
    resolved_object_type: str,
) -> bool:
    """Align pool only when already bound; never auto-bind available chips."""
    if pool_status != STATUS_BOUND:
        return False
    return (
        pool_bound_object_id != resolved_object_id
        or (pool_bound_object_type or "") != resolved_object_type
    )


def pool_unbind_fields() -> tuple[str, None, None]:
    """Status + cleared bind pointers for an available pool row."""
    return STATUS_AVAILABLE, None, None
