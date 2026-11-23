"""Merging of WSJT-X / WS logs into one unified log.

The unified log is the concatenation of the selected logs' QSOs with
repeated QSOs dropped and the result ordered chronologically.  "Repeated"
means the same call, band and date/time in the same mode; when the
second copy carries extra details (e.g. an empty grid that the first was
missing), those details are merged into the kept copy.
"""

from __future__ import annotations

__all__ = ["unify_records"]


def _dedup_key(record):
    """Key identifying a repeated QSO: call, band, date, time and mode."""
    return (
        record.call.upper(),
        record.band,
        record.get("qso_date", "").strip(),
        record.get("time_on", "").strip(),
        record.mode,
    )


def _merge_record(base, new):
    """Copy empty fields of duplicate ``new`` into ``base``."""
    for name, value in new.items():
        if value and not base.get(name):
            base[name] = value


def _sort_key(record):
    return (
        record.get("qso_date", ""),
        record.get("time_on", ""),
        record.call,
        record.band,
    )


def unify_records(records, dedupe=True, sort=True):
    """Merge ``records`` into one unified list of QSOs.

    ``dedupe`` collapses repeated QSOs (see :func:`_dedup_key`) to a
    single record; ``sort`` orders the result by ``qso_date``/``time_on``.
    Returns ``(unified, removed)`` where ``removed`` is the number of
    dropped duplicates.
    """
    unified = []
    seen = {}
    removed = 0
    for record in records:
        key = _dedup_key(record)
        if dedupe and key in seen:
            _merge_record(seen[key], record)
            removed += 1
            continue
        if dedupe:
            seen[key] = record
        unified.append(record)
    if sort:
        unified.sort(key=_sort_key)
    return unified, removed
