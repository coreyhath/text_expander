"""SQLite storage for keyboard expander mappings — with profile support."""

import sqlite3
from pathlib import Path

DB_PATH = Path.home() / ".config" / "autofiller" / "mappings.db"

LLM_QUERY_DEFAULT_PROMPT = (
    "Here is a resume: <<<{{resume}}>>>, and here is a job description: <<<{{job_description}}>>>.\n"
    "Respond with only the answer to this question in 1~2 sentence streamlined: <<<{{clipboard}}>>>"
)

COVER_LETTER_DEFAULT_PROMPT = (
    "Today's date is {{date}}.\n\n"
    "Here is a resume:\n<<<{{resume}}>>>\n\n"
    "Here is a job description:\n<<<{{job_description}}>>>\n\n"
    "Write a professional, tailored cover letter for this position. "
    "Use standard business letter format and include today's date at the top. "
    "Be specific about why this candidate is a strong fit. "
    "Keep it to one page. Output only the letter text, no extra commentary."
    "Don't use '—' or other hyphen-similar character."
    "Don't add company related placeholder like [Recipient Name], [Company Name], [Company Address], [City, State, Zip Code]."
    "After contact information, start with 'Dear Hiring Manager,' if you don't know the recipient's name, and end with a professional closing like 'Sincerely,' followed by a signature line with the candidate's name."
)

# Seeded for every new profile (infrastructure shortcuts)
_SYSTEM_ROWS = [
    ("jjj", "job_description",           "store_clipboard"),
    ("rrr", "resume",                    "store_clipboard"),
    ("qqq", LLM_QUERY_DEFAULT_PROMPT,    "llm_query"),
    ("ccc", COVER_LETTER_DEFAULT_PROMPT, "gen_cover_letter"),
    ("uuu", "",                          "show_ui"),
    ("///", "",                          "switch_profile"),
]

# Seeded only for the initial Default profile
_DEFAULT_EXPAND_ROWS = [
    ("#comp", "Your Company Name",                   "expand"),
    ("#titl", "Your Job Title",                      "expand"),
    ("#link", "https://linkedin.com/in/yourprofile", "expand"),
    ("#addr", "Your Street Address, City, State ZIP", "expand"),
]


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with _connect() as conn:
        existing_tables = {
            r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }

        # ── profiles ──────────────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)

        # ── settings ──────────────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Ensure Default profile exists
        conn.execute("INSERT OR IGNORE INTO profiles (name) VALUES ('Default')")
        row = conn.execute("SELECT id FROM profiles WHERE name='Default'").fetchone()
        if row is None:
            # Fallback: use the first available profile as the default anchor
            row = conn.execute("SELECT id FROM profiles ORDER BY id LIMIT 1").fetchone()
        default_id = row[0]

        # Ensure current_profile_id setting exists
        if not conn.execute("SELECT 1 FROM settings WHERE key='current_profile_id'").fetchone():
            conn.execute("INSERT INTO settings VALUES ('current_profile_id', ?)", (str(default_id),))

        # ── mappings ──────────────────────────────────────────────────────────
        if "mappings" in existing_tables:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(mappings)")}
            if "profile_id" not in cols:
                # Add action column if missing (very old schema)
                if "action" not in cols:
                    conn.execute("ALTER TABLE mappings ADD COLUMN action TEXT NOT NULL DEFAULT 'expand'")
                conn.execute(
                    f"ALTER TABLE mappings ADD COLUMN profile_id INTEGER NOT NULL DEFAULT {default_id}"
                )
                # Old primary key was just (shortcut); rebuild with composite PK
                conn.execute("""
                    CREATE TABLE mappings_new (
                        shortcut   TEXT    NOT NULL,
                        expansion  TEXT    NOT NULL DEFAULT '',
                        action     TEXT    NOT NULL DEFAULT 'expand',
                        profile_id INTEGER NOT NULL,
                        PRIMARY KEY (shortcut, profile_id)
                    )
                """)
                conn.execute("INSERT INTO mappings_new SELECT shortcut, expansion, action, profile_id FROM mappings")
                conn.execute("DROP TABLE mappings")
                conn.execute("ALTER TABLE mappings_new RENAME TO mappings")
        else:
            conn.execute("""
                CREATE TABLE mappings (
                    shortcut   TEXT    NOT NULL,
                    expansion  TEXT    NOT NULL DEFAULT '',
                    action     TEXT    NOT NULL DEFAULT 'expand',
                    profile_id INTEGER NOT NULL,
                    PRIMARY KEY (shortcut, profile_id)
                )
            """)

        # ── session_vars ──────────────────────────────────────────────────────
        if "session_vars" in existing_tables:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(session_vars)")}
            if "profile_id" not in cols:
                conn.execute("""
                    CREATE TABLE session_vars_new (
                        name       TEXT    NOT NULL,
                        value      TEXT    NOT NULL DEFAULT '',
                        profile_id INTEGER NOT NULL,
                        PRIMARY KEY (name, profile_id)
                    )
                """)
                conn.execute(
                    f"INSERT INTO session_vars_new SELECT name, value, {default_id} FROM session_vars"
                )
                conn.execute("DROP TABLE session_vars")
                conn.execute("ALTER TABLE session_vars_new RENAME TO session_vars")
        else:
            conn.execute("""
                CREATE TABLE session_vars (
                    name       TEXT    NOT NULL,
                    value      TEXT    NOT NULL DEFAULT '',
                    profile_id INTEGER NOT NULL,
                    PRIMARY KEY (name, profile_id)
                )
            """)

        # Seed Default profile if empty
        if conn.execute("SELECT COUNT(*) FROM mappings WHERE profile_id=?", (default_id,)).fetchone()[0] == 0:
            rows = _DEFAULT_EXPAND_ROWS + _SYSTEM_ROWS
            conn.executemany(
                "INSERT OR IGNORE INTO mappings (shortcut, expansion, action, profile_id) VALUES (?,?,?,?)",
                [(s, e, a, default_id) for s, e, a in rows],
            )

        conn.commit()


# ── global settings ──────────────────────────────────────────────────────────

def get_setting(key: str, default: str = "") -> str:
    with _connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def set_setting(key: str, value: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?,?)"
            " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        conn.commit()


# ── profile management ────────────────────────────────────────────────────────

def get_current_profile_id() -> int:
    with _connect() as conn:
        return int(conn.execute("SELECT value FROM settings WHERE key='current_profile_id'").fetchone()[0])


def get_current_profile_name() -> str:
    with _connect() as conn:
        pid = int(conn.execute("SELECT value FROM settings WHERE key='current_profile_id'").fetchone()[0])
        row = conn.execute("SELECT name FROM profiles WHERE id=?", (pid,)).fetchone()
        return row[0] if row else "Default"


def get_profiles() -> list[str]:
    with _connect() as conn:
        return [r[0] for r in conn.execute("SELECT name FROM profiles ORDER BY name").fetchall()]


def create_profile(name: str) -> None:
    with _connect() as conn:
        conn.execute("INSERT INTO profiles (name) VALUES (?)", (name,))
        pid = conn.execute("SELECT id FROM profiles WHERE name=?", (name,)).fetchone()[0]
        conn.executemany(
            "INSERT INTO mappings (shortcut, expansion, action, profile_id) VALUES (?,?,?,?)",
            [(s, e, a, pid) for s, e, a in _SYSTEM_ROWS],
        )
        conn.commit()


def delete_profile(name: str) -> None:
    with _connect() as conn:
        if conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0] <= 1:
            raise ValueError("Cannot delete the last profile.")
        row = conn.execute("SELECT id FROM profiles WHERE name=?", (name,)).fetchone()
        if not row:
            return
        pid = row[0]
        conn.execute("DELETE FROM mappings WHERE profile_id=?", (pid,))
        conn.execute("DELETE FROM session_vars WHERE profile_id=?", (pid,))
        conn.execute("DELETE FROM profiles WHERE id=?", (pid,))
        # If deleted profile was active, switch to first available
        cur = int(conn.execute("SELECT value FROM settings WHERE key='current_profile_id'").fetchone()[0])
        if cur == pid:
            new_pid = conn.execute("SELECT id FROM profiles ORDER BY id LIMIT 1").fetchone()[0]
            conn.execute("UPDATE settings SET value=? WHERE key='current_profile_id'", (str(new_pid),))
        conn.commit()


def set_current_profile(name: str) -> None:
    with _connect() as conn:
        row = conn.execute("SELECT id FROM profiles WHERE name=?", (name,)).fetchone()
        if not row:
            raise ValueError(f"Profile '{name}' not found.")
        conn.execute("UPDATE settings SET value=? WHERE key='current_profile_id'", (str(row[0]),))
        conn.commit()


# ── mappings CRUD (profile-scoped) ────────────────────────────────────────────

def get_all() -> dict[str, dict]:
    pid = get_current_profile_id()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT shortcut, expansion, action FROM mappings WHERE profile_id=? ORDER BY shortcut",
            (pid,),
        ).fetchall()
    return {r[0]: {"expansion": r[1], "action": r[2]} for r in rows}


def add(shortcut: str, expansion: str, action: str = "expand") -> None:
    pid = get_current_profile_id()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO mappings (shortcut, expansion, action, profile_id) VALUES (?,?,?,?)",
            (shortcut, expansion, action, pid),
        )
        conn.commit()


def update(old_shortcut: str, new_shortcut: str, expansion: str, action: str = "expand") -> None:
    pid = get_current_profile_id()
    with _connect() as conn:
        if old_shortcut != new_shortcut:
            conn.execute("DELETE FROM mappings WHERE shortcut=? AND profile_id=?", (old_shortcut, pid))
            conn.execute(
                "INSERT INTO mappings (shortcut, expansion, action, profile_id) VALUES (?,?,?,?)",
                (new_shortcut, expansion, action, pid),
            )
        else:
            conn.execute(
                "UPDATE mappings SET expansion=?, action=? WHERE shortcut=? AND profile_id=?",
                (expansion, action, old_shortcut, pid),
            )
        conn.commit()


def delete(shortcut: str) -> None:
    pid = get_current_profile_id()
    with _connect() as conn:
        conn.execute("DELETE FROM mappings WHERE shortcut=? AND profile_id=?", (shortcut, pid))
        conn.commit()


# ── session variables (profile-scoped) ───────────────────────────────────────

def get_session_vars() -> dict[str, str]:
    pid = get_current_profile_id()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT name, value FROM session_vars WHERE profile_id=? ORDER BY name", (pid,)
        ).fetchall()
    return {r[0]: r[1] for r in rows}


def set_session_var(name: str, value: str) -> None:
    pid = get_current_profile_id()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO session_vars (name, value, profile_id) VALUES (?,?,?)"
            " ON CONFLICT(name, profile_id) DO UPDATE SET value=excluded.value",
            (name, value, pid),
        )
        conn.commit()
