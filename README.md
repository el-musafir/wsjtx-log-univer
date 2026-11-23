# WSJTX Log Unifier

Reads the logs WSJT-X and the **WS - Digital Mode Suite** (formerly WSJT-X
Improved) keep in `wsjtx_log.adi` — QSOs in FT8 and FT4 — and writes out
one unified log combining the selected ones.

Both programs store their log as the same ADIF format WSJT-X uses, so
this tool reads either program's log.  It runs on Windows, macOS and
Raspberry Pi (Python 3.8+, standard library only).

## Requirements

- Python 3.8+ with `tkinter` for the graphical interface
  (CPython includes it; on Raspberry Pi run
  `sudo apt install python3-tk` first if missing).

## Quick start

```
python3 wsjtx_log_unifier.py
```

A window opens with the **Logs to take and unify** list:

1. Press **Add files…** (or **Add directory…** to browse a whole folder)
   and pick one or more `wsjtx_log.adi` files.
2. Double-click a row to toggle whether that log is taken into the
   unified log (the row's "Take" column shows ✓/◻).
3. Press **Read logs** to count the QSOs in each file.
4. Press **Save unified log…** to write the unified log: a chronological
   file combining the selected logs, with repeated QSOs removed by
   default.

The options at the bottom control the output: *Remove duplicate QSOs
(call, band, time)* (on by default) and *Sort QSOs by date/time* (on by
default).

## Command line

```
python3 wsjtx_log_unifier.py wsjtx_log.adi [other.adi ...] -o unified_log.adi
```

Useful options: `--no-dedupe` (keep repeated QSOs) and `--no-sort` (keep
the input order instead of sorting by date/time).  With no log files
given the graphical interface opens instead.

## How the logs are read

- WSJT-X and WS write one QSO per ADIF record: `<call>`, `<qso_date>`,
  `<time_on>`, `<band>`, `<mode>`, `<freq>`, `<station_callsign>`,
  `<my_gridsquare>`, and so on.
- WSJT-X writes FT4 QSOs with `<mode>MFSK<submode>FT4`; the tool treats
  that as mode FT4 so FT4 and FT8 QSOs unify cleanly.
- A duplicate is the same call, band and date/time; when the second copy
  carries extra details (for example an empty grid that the first was
  missing), those are merged into the kept record.

## Layout

| File | Purpose |
| ---- | ------- |
| `wsjtx_log_unifier.py` | Entry point: opens the GUI, or runs the CLI with log files. |
| `gui.py` | The graphical interface (`LogsApp`). |
| `adi.py` | Parser and writer for the WSJT-X / WS `wsjtx_log.adi` format. |
| `unify.py` | Merging, duplicate removal and sorting of QSO records. |
| `tests/` | Unit tests: `python3 -m unittest discover -s tests -t .` |
| `tests/fixtures/wsjtx_log.adi` | A small example log in the real WSJT-X format. |
| `LICENSE` | MIT. |

## Where the logs are

- WSJT-X 2.x writes `wsjtx_log.adi` in its log directory (by default the
  program folder, `C:\wsjtx\`).
- The WS suite keeps its log in its own log directory (an install
  folder such as `C:\WS\`).
- In the tool, press **Add directory…** and browse for them; only
  `*.adi` files are picked up.

## Development notes

Nothing here is derived from the WS/WSJT-X source trees; the format is
the public ADIF format those programs write out.
