"""Parser and writer for the ADIF logs written by WSJT-X and the WS suite.

Both WSJT-X and the WS suite ("WS - Digital Mode Suite", formerly WSJT-X
Improved) write their QSO log as an ADIF file named ``wsjtx_log.adi``, so
reading this format reads either program's log.  The format is plain
ADIF as produced by WSJT-X: every QSO is one record of space separated
``name:value`` tags terminated by ``<eor>``, for example::

    ADIF Export
    <adif_ver:5>3.1.1
    <created_timestamp:15>20250504 194948
    <programid:6>WSJT-X
    <programversion:5>2.7.0
    <eoh>
    <call:6>JA7DXX <gridsquare:0> <mode:3>FT8 <rst_sent:3>-15
    <rst_rcvd:3>-14 <qso_date:8>20250504 <time_on:6>194945
    <qso_date_off:8>20250504 <time_off:6>194945 <band:3>20m
    <freq:9>14.074849 <station_callsign:5>DF3TN <my_gridsquare:4>JN49
    <eor>

WSJT-X stores FT4 QSOs with ``<mode:4>MFSK<submode:3>FT4`` (mode "MFSK"
plus the FT4 submode); the :attr:`QsoRecord.mode` property normalises
that to "FT4" so FT4 and FT8 QSOs unify cleanly.
"""

from __future__ import annotations

import re

__all__ = [
    "AdifParseError",
    "CANONICAL_FIELDS",
    "QsoRecord",
    "parse_adi_file",
    "parse_adi_text",
    "render_record",
    "write_adi",
]

#: Record terminators understood by the parser.
TERMINATORS = frozenset({"eoh", "eor", "eof"})

#: Canonical field order used when writing records (mirrors WSJT-X style).
CANONICAL_FIELDS = (
    "call",
    "gridsquare",
    "mode",
    "submode",
    "rst_sent",
    "rst_rcvd",
    "qso_date",
    "time_on",
    "qso_date_off",
    "time_off",
    "band",
    "freq",
    "station_callsign",
    "my_gridsquare",
)
_CANONICAL_SET = frozenset(CANONICAL_FIELDS)

_TAG_RE = re.compile(r"<([A-Za-z_][A-Za-z0-9_]*)(?::(\d+))?>")


class AdifParseError(Exception):
    """Raised when a file cannot be parsed as a WSJT-X style ADIF log."""


class QsoRecord(dict):
    """One QSO record: a mapping of lowercase field names to string values.

    Prefer the :attr:`mode`, :attr:`call`, :attr:`band` and
    :attr:`date_time_key` helpers over reading raw tags.
    """

    @property
    def call(self) -> str:
        """The other station's callsign (``<call>``)."""
        return self.get("call", "").strip()

    @property
    def mode(self) -> str:
        """The effective operating mode ("FT8", "FT4", "MFSK", ...).

        WSJT-X writes FT4 as ``mode=MFSK`` with a ``submode=FT4`` tag;
        when that combination is seen the submode is reported as the mode.
        """
        mode = self.get("mode", "").strip().upper()
        if mode in ("", "MFSK"):
            mode = self.get("submode", "").strip().upper() or mode
        return mode

    @property
    def band(self) -> str:
        """The band name, upper-cased ("20m" -> "20M")."""
        return self.get("band", "").strip().upper()

    @property
    def date_time_key(self):
        """The ``(qso_date, time_on)`` pair identifying a QSO."""
        return (self.get("qso_date", ""), self.get("time_on", ""))


def _scan_tags(text):
    """Yield ``(name, value)`` for every tag found in ``text``.

    Values use the ADIF length prefix (``<name:12>...``); values of tags
    without a length run to the next ``<`` (or the end of the text).
    Anything that does not look like a tag is skipped.
    """
    i = 0
    n = len(text)
    while i < n:
        j = text.find("<", i)
        if j < 0:
            break
        match = _TAG_RE.match(text, j)
        if match is None:
            i = j + 1
            continue
        name = match.group(1).lower()
        length = int(match.group(2)) if match.group(2) else None
        pos = match.end()
        if length is not None:
            value = text[pos:pos + length]
            pos += length
        else:
            next_tag = text.find("<", pos)
            value = text[pos:] if next_tag < 0 else text[pos:next_tag]
            pos = next_tag if next_tag >= 0 else n
        yield name, value
        i = pos


def parse_adi_text(text):
    """Parse ADIF log text into a list of :class:`QsoRecord`."""
    records = []
    current = None
    for name, value in _scan_tags(text):
        if name in TERMINATORS:
            if current is not None:
                if current.call:
                    records.append(current)
                current = None
            continue
        if current is None:
            current = QsoRecord()
        if name not in current:
            current[name] = value
    if current is not None and current.call:
        records.append(current)
    return records


def parse_adi_file(path):
    """Parse the ADIF log at ``path`` into a list of :class:`QsoRecord`."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError as exc:
        raise AdifParseError(f"{path}: {exc.strerror or exc}") from exc
    return parse_adi_text(text)


def _format_tag(name, value):
    value = str(value)
    return f"<{name}:{len(value)}>{value}"


def render_record(record):
    """Render one QSO record to an ADIF string ending with ``<eor>``."""
    parts = []
    for name in CANONICAL_FIELDS:
        if name == "mode":
            value = record.mode
        else:
            value = record.get(name)
        if value:
            parts.append(_format_tag(name, value))
    for name in record:  # non-canonical fields, in file order
        if name not in _CANONICAL_SET and record.get(name):
            parts.append(_format_tag(name, record[name]))
    parts.append("<eor>")
    return " ".join(parts)


def write_adi(path, records):
    """Write ``records`` as a WSJT-X style ADIF log to ``path``."""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("ADIF Export\n")
        f.write("<eoh>\n")
        for record in records:
            f.write(render_record(record))
            f.write("\n")
