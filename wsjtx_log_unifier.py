#!/usr/bin/env python3
"""Read WSJT-X / WS logs in FT8 and FT4 and write out a unified ADIF log.

Both WSJT-X and the WS suite ("WS - Digital Mode Suite", formerly WSJT-X
Improved) keep their QSO log in ``wsjtx_log.adi`` (ADIF format).  This
tool reads one or more of those logs, drops repeated QSOs and writes the
resulting unified log back out.

Usage:
    python wsjtx_log_unifier.py [LOG ...] [-o OUTPUT] [--no-dedupe] [--no-sort]

Without log files it opens the graphical interface (see ``gui.py``).
"""

from __future__ import annotations

import argparse

from adi import AdifParseError, parse_adi_file, write_adi
from unify import unify_records


def run_cli(files, output="unified_log.adi", dedupe=True, sort=True):
    """Read ``files`` and write the unified log; returns an exit code."""
    records = []
    errors = []
    for path in files:
        try:
            recs = parse_adi_file(path)
        except AdifParseError as exc:
            errors.append(str(exc))
            continue
        records.extend(recs)
        print(f"{path}: {len(recs)} QSOs")
    unified, removed = unify_records(records, dedupe=dedupe, sort=sort)
    write_adi(output, unified)
    print(f"Wrote {len(unified)} QSOs to {output}")
    if removed:
        print(f"Removed {removed} duplicates.")
    for err in errors:
        print(f"error: {err}")
    return 1 if errors else 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="wsjtx_log_unifier",
        description=(
            "Read WSJT-X / WS logs in FT8 and FT4 and write out a "
            "unified ADIF log."),
    )
    parser.add_argument(
        "files", nargs="*", metavar="LOG",
        help="wsjtx_log.adi files to read "
             "(default: the graphical interface)")
    parser.add_argument(
        "-o", "--output", default="unified_log.adi",
        help="output file (default: %(default)s)")
    parser.add_argument(
        "--no-dedupe", action="store_true",
        help="keep repeated QSOs")
    parser.add_argument(
        "--no-sort", action="store_true",
        help="keep the input order instead of sorting by date and time")
    args = parser.parse_args(argv)

    if args.files:
        return run_cli(args.files, args.output,
                       dedupe=not args.no_dedupe, sort=not args.no_sort)
    from gui import run_gui
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
