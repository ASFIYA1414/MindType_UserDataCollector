**Project Audit — MindType_UserDataCollector**

**Summary:**
- **Purpose:** Desktop key-event collector that computes keystroke-derived features and occasionally prompts the user for self-reported stress via a popup. Data is written to an SQLite DB and appended to a CSV dataset.
- **Principal components:** [main.py](main.py), [listener.py](listener.py), [features.py](features.py), [database.py](database.py), [popup.py](popup.py).

**High-level Findings:**
- Functionality is straightforward and understandable. The project appears to work end-to-end: start GUI → capture keystrokes → persist events → compute per-minute features → append to CSV → show popup on drift.
- No automated tests, packaging, or dependency manifest (no `requirements.txt` or `pyproject.toml`).
- Several robustness, correctness, security/privacy, and platform/permission issues need attention.

**Dependencies & Environment:**
- Explicitly used libraries: `pynput`, `pandas`, `numpy`, `tkinter` (stdlib), `sqlite3` (stdlib).
- Missing dependency declaration. Add a `requirements.txt` with at least: `pynput`, `pandas`, `numpy` and their pinned versions.
- On macOS, `pynput` requires Accessibility permissions (System Preferences → Security & Privacy → Accessibility). Document this in README and show an error message if permission denied.

**Security & Privacy Risks:**
- This software collects raw keystrokes — extremely sensitive personal data and potentially PII. There is no consent flow, privacy notice, or data minimization.
  - Recommendation: add explicit informed consent (at setup), a clear privacy policy, and opt-in logging only after consent.
  - Consider hashing/transforming or encrypting sensitive fields or storing only derived features when possible.
- Stored data is in plain SQLite and CSV in project directory — consider encryption at rest or user-selected storage location with proper permissions.

**Correctness & Data Quality Issues:**
- Key pairing (press → release) in `features.compute_and_save_features` is fragile: it pairs the first release for the same key that occurs after a press. This can mismatch when the same key is pressed multiple times quickly or when keys overlap (e.g., held keys).
  - Recommendation: record an event id or sequence number to match press/release, or store an explicit key identifier (scancode) and match by order (press i ↔ next release for that key). Keep press/release indices aligned.
- `format_key` returns `key.char` or `str(key)`. Special keys become strings like `Key.space` — fine but inconsistent formatting across platforms. Consider normalizing names (e.g., `space`, `backspace`, `a`, `A`) and include explicit `is_special` flag if needed.
- `compute_and_save_features` calculates `pause_times` using timestamps of presses only. Inter-key timing that spans release-to-next-press vs. release-to-release might be of interest — clarify the intended definition of `pause`.
- `kpm` calculation divides by duration derived from the fixed window (end_time-start_time). If actual events within the window are far fewer, this is fine; but when `duration_minutes` is zero, code sets `kpm` to zero — guard division carefully.

**Robustness & Reliability:**
- The listener inserts a new SQLite connection for every event (open/commit/close on each key event). This is expensive and may cause IO bottlenecks.
  - Recommendation: use a persistent DB connection with a thread-safe queue (producer: listener thread; consumer: DB writer thread) and batch inserts.
- `listener` relies on global variables and runs the `pynput` listener in a background thread. There is no graceful shutdown sequence that closes pending DB writes. Recommend implementing a controlled stop sequence (signal/flag, flush queue, close DB).
- `start_listener` is called with `user_id` from the GUI; if `get_user_id()` returns None or an empty string, `listener.user_id` becomes None/empty and the listener will early-return in event handlers. Add validation for `user_id` in `main` and show an error if invalid.
- `compute_and_save_features` and `update_last_n_labels` read/write CSV files without exception handling. If `mindtype_dataset.csv` is locked or missing, the functions will raise.
- `update_last_n_labels` uses `df.loc[start_index:, "stress_level"] = label`. If CSV headers mismatch or file contains unexpected types, this may error; add validation and backup copies before write.

**Threading & Concurrency:**
- Current design: `pynput` listener runs in a separate thread. Each event uses its own sqlite connection, so cross-thread DB locking is minimal, but frequent connections are costly.
- If you move to a shared connection, ensure the DB access is serialized (single DB writer thread) because SQLite connections are not fully thread-safe for concurrent writes.

**Error Handling & Logging:**
- There is little-to-no logging. Add `logging` with appropriate levels (INFO, WARNING, ERROR, DEBUG). Replace prints with logs in `main` and `listener`.
- Wrap DB and file IO with try/except and log errors instead of crashing silently.

**Usability & UX:**
- `get_user_id` GUI does not validate input, nor confirm saving location. It also blocks until closed — acceptable, but consider a non-blocking settings screen and persistent configuration file.
- Popups may interrupt users frequently — current cooldown is 450 seconds. Consider user preference settings for frequency and the ability to disable prompts.

**Data Ethics & Compliance:**
- Collecting keystrokes may be illegal or require strict consent (depending on jurisdiction). Add a strong consent mechanism and consider consulting legal/privacy experts before deploying or collecting real user data.

**Testing & CI:**
- No tests present. Add unit tests for: DB init, event insert logic (mocked), `compute_and_save_features` (with synthetic DataFrame), CSV append/update. Use `pytest` and add a `requirements-dev.txt`.
- Add a simple linting setup (flake8/black) and a `pre-commit` configuration.

**Platform Notes:**
- macOS: `pynput` needs Accessibility permission; `tkinter` may require install of Tcl/Tk via system package managers if not present in Python distribution.
- Windows/Linux: test `format_key` outputs for special keys; behavior differs by platform.

**File-by-file Notes & Recommendations:**
- [main.py](main.py):
  - Good architecture for main loop and baseline EMA update.
  - Recommendations:
    - Validate `user_id` from `get_user_id()` and require explicit consent before starting listener.
    - Persist `session_id` handling (currently always 1; the listener increments `current_session` when idle). Consider unifying session management in a single module.
    - Add logging and graceful shutdown to stop the listener and flush pending writes.

- [listener.py](listener.py):
  - Issues:
    - Creates a DB connection per event; expensive.
    - Uses `format_key` and `str(key)` which can differ across platforms.
    - No exception handling around DB writes.
  - Recommendations:
    - Implement a buffered queue and a dedicated DB writer thread that consumes and batches events.
    - Add try/except around DB operations and retry/backoff on failure.
    - Normalize key names and consider capturing key scan codes if available.

- [features.py](features.py):
  - Issues:
    - Fragile matching of presses/releases; may mis-pair repeated keys.
    - Uses pandas and numpy without dependency management.
    - No error handling for CSV read/write operations.
  - Recommendations:
    - Store an event sequence number or id to reliably match press/release pairs.
    - Add explicit exception handling and file locking when writing CSV.
    - Consider storing derived features directly into a DB table instead of an append-only CSV (or at least maintain a journaling/backup policy).

- [database.py](database.py):
  - Simple and adequate for creating the table. No further DB schema or indices.
  - Recommendations:
    - Add an index on `(user_id, session_id, timestamp)` for faster queries.
    - Consider a separate table for computed features and another for raw keystrokes.
    - Consider migrations (e.g., use `alembic` or a simple migration-version table) as schema evolves.

- [popup.py](popup.py):
  - Simple modal tkinter poller returning binary 0/1 values.
  - Recommendation: return an enum or descriptive string instead of raw integers for clarity; display privacy/consent text in the popup.

**Quick Wins (priority order):**
1. Add `requirements.txt` and a short `README.md` indicating permissions and usage (macOS Accessibility).  
2. Add logging and wrap DB/file operations with try/except.  
3. Implement a DB-writer queue to batch inserts and avoid opening/closing on every key event.  
4. Add an explicit consent dialog before starting collection and persist consent status.  
5. Add a unit test suite for `compute_and_save_features` using synthetic events.

**Medium-term Improvements:**
- Harden press/release pairing (add event ids or sequence numbers).  
- Store features in DB with timestamps and a clear schema; use CSV only for export.  
- Add encryption at rest for DB/CSV or allow user to choose storage path.  
- Add configuration (YAML/JSON) for thresholds like `DRIFT_THRESHOLD`, `POPUP_COOLDOWN`, `IDLE_TIMEOUT`.

**Long-term / Architectural:**
- Consider separating components: a small privileged native agent that captures keys and writes events to a secure local store, plus a non-privileged analytics process that reads derived features. This reduces privilege surface.
- Consider transforming raw keystrokes into privacy-preserving aggregates on-device and uploading only aggregates if remote collection is required.

**Suggested Minimal Checklist to ship (example):**
- [ ] Add `requirements.txt` and `README.md` with macOS instructions.
- [ ] Add logging and error handling for DB and file IO.
- [ ] Add consent flow and persistent opt-in flag.
- [ ] Implement buffered DB writes and graceful shutdown.
- [ ] Add tests for feature computation and CSV handling.
- [ ] Add a simple CI (GitHub Actions) to run linters/tests.

**Examples of specific code improvements (short):**
- Use a queue in `listener.py` to push events to a DB writer thread instead of `insert_event` opening/closing every time.
- Change `compute_and_save_features` pairing logic to pair by press index and the next release that has not yet been consumed for that key.
- Add `cursor.execute('CREATE INDEX IF NOT EXISTS idx_keystrokes_user_time ON keystrokes(user_id, session_id, timestamp)')` in `init_db()`.

If you want, I can: add a `requirements.txt`, implement a buffered DB writer (modify `listener.py`), add logging and a basic `README.md`, and create unit tests for `features.compute_and_save_features`. Which of those would you like me to start with?


---

Generated on 2026-02-17 — concise audit for developer review.
