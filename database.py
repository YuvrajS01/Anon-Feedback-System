"""
Database operations for the Anonymous Feedback System.
Uses SQLite for local-only storage.

Anonymity model
---------------
Feedback rows carry NO reference to a token. Progress through a multi-step
session is tracked on the token row itself (the set of teacher/subject pairs
already rated), and the tokens table stores no timestamps, so feedback can
never be joined back to the token that produced it.
"""

import json
import secrets
import sqlite3
from contextlib import contextmanager

from config import DATABASE_PATH, QUESTIONS

SCHEMA_VERSION = 2

# Uppercase letters and digits, minus look-alikes (0/O, 1/I/L)
TOKEN_ALPHABET = ''.join(
    c for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789' if c not in '0O1IL'
)

QUESTION_COLUMNS = [f'q{i}' for i in range(1, len(QUESTIONS) + 1)]
assert len(QUESTION_COLUMNS) == 10, 'The database schema expects exactly 10 questions'


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Create tables and migrate older databases to the current schema."""
    with get_db() as conn:
        conn.execute('PRAGMA journal_mode = WAL')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tokens (
                token TEXT PRIMARY KEY,
                is_used INTEGER DEFAULT 0,
                completed TEXT NOT NULL DEFAULT '[]'
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher TEXT NOT NULL,
                subject TEXT NOT NULL,
                semester INTEGER,
                academic_session TEXT,
                branch TEXT,
                q1 INTEGER NOT NULL, q2 INTEGER NOT NULL,
                q3 INTEGER NOT NULL, q4 INTEGER NOT NULL,
                q5 INTEGER NOT NULL, q6 INTEGER NOT NULL,
                q7 INTEGER NOT NULL, q8 INTEGER NOT NULL,
                q9 INTEGER NOT NULL, q10 INTEGER NOT NULL,
                comment TEXT,
                submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        _migrate(conn)
        conn.execute(
            'CREATE INDEX IF NOT EXISTS idx_feedback_period '
            'ON feedback (semester, academic_session, branch)'
        )
        conn.execute(f'PRAGMA user_version = {SCHEMA_VERSION}')
        conn.commit()


def _columns(conn, table: str) -> set:
    return {row['name'] for row in conn.execute(f'PRAGMA table_info({table})')}


def _migrate(conn):
    """Upgrade databases created by earlier versions of the app."""
    token_cols = _columns(conn, 'tokens')
    if 'completed' not in token_cols:
        conn.execute("ALTER TABLE tokens ADD COLUMN completed TEXT NOT NULL DEFAULT '[]'")

    feedback_cols = _columns(conn, 'feedback')
    for col, sql_type in (('semester', 'INTEGER'), ('academic_session', 'TEXT'), ('branch', 'TEXT')):
        if col not in feedback_cols:
            conn.execute(f'ALTER TABLE feedback ADD COLUMN {col} {sql_type}')

    if 'session_id' not in feedback_cols:
        return

    # v1 linked feedback -> feedback_sessions -> token. Move in-progress state
    # onto the token row, then drop the link so responses become anonymous.
    has_sessions = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='feedback_sessions'"
    ).fetchone()
    if has_sessions:
        sessions = conn.execute('SELECT id, token FROM feedback_sessions').fetchall()
        for s in sessions:
            rows = conn.execute(
                'SELECT teacher, subject FROM feedback WHERE session_id = ?', (s['id'],)
            ).fetchall()
            done = sorted({combo_key(r['teacher'], r['subject']) for r in rows})
            conn.execute('UPDATE tokens SET completed = ? WHERE token = ?',
                         (json.dumps(done), s['token']))

    cols = ', '.join(['teacher', 'subject', 'semester', 'academic_session', 'branch',
                      *QUESTION_COLUMNS, 'comment', 'submitted_at'])
    conn.execute('ALTER TABLE feedback RENAME TO feedback_old')
    conn.execute(f'''
        CREATE TABLE feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher TEXT NOT NULL,
            subject TEXT NOT NULL,
            semester INTEGER,
            academic_session TEXT,
            branch TEXT,
            {', '.join(f'{q} INTEGER NOT NULL' for q in QUESTION_COLUMNS)},
            comment TEXT,
            submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Shuffle row order so insertion order can't be correlated either
    conn.execute(f'INSERT INTO feedback ({cols}) SELECT {cols} FROM feedback_old ORDER BY RANDOM()')
    conn.execute('DROP TABLE feedback_old')
    conn.execute('DROP TABLE IF EXISTS feedback_sessions')


def combo_key(teacher: str, subject: str) -> str:
    """Stable identifier for a teacher-subject pair (robust to reordering combos)."""
    return f'{teacher}\x1f{subject}'


# =============================================================================
# Token operations
# =============================================================================

def generate_token(length: int = 6) -> str:
    """Generate a cryptographically random token."""
    return ''.join(secrets.choice(TOKEN_ALPHABET) for _ in range(length))


def create_tokens(count: int, length: int = 6) -> list:
    """Generate `count` brand-new tokens, store them, and return them."""
    created = []
    with get_db() as conn:
        while len(created) < count:
            token = generate_token(length)
            cursor = conn.execute(
                'INSERT OR IGNORE INTO tokens (token) VALUES (?)', (token,)
            )
            if cursor.rowcount:
                created.append(token)
        conn.commit()
    return created


def add_tokens(tokens: list) -> int:
    """Add specific tokens to the database. Returns the number inserted."""
    with get_db() as conn:
        cursor = conn.executemany(
            'INSERT OR IGNORE INTO tokens (token) VALUES (?)', [(t,) for t in tokens]
        )
        conn.commit()
        return cursor.rowcount


def get_token(token: str) -> dict | None:
    """Return token state ({'is_used': bool, 'completed': set}) or None."""
    with get_db() as conn:
        row = conn.execute(
            'SELECT is_used, completed FROM tokens WHERE token = ?', (token,)
        ).fetchone()
    if row is None:
        return None
    return {'is_used': bool(row['is_used']), 'completed': set(json.loads(row['completed']))}


def get_unused_tokens(limit: int | None = None) -> list:
    """Return tokens that haven't been started yet."""
    sql = "SELECT token FROM tokens WHERE is_used = 0 AND completed = '[]' ORDER BY token"
    params = ()
    if limit:
        sql += ' LIMIT ?'
        params = (limit,)
    with get_db() as conn:
        return [row['token'] for row in conn.execute(sql, params)]


def get_token_stats() -> dict:
    """Token statistics for the dashboard and control panel."""
    with get_db() as conn:
        row = conn.execute('''
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(is_used = 1), 0) AS used,
                COALESCE(SUM(is_used = 0 AND completed != '[]'), 0) AS in_progress
            FROM tokens
        ''').fetchone()
    stats = dict(row)
    stats['unused'] = stats['total'] - stats['used'] - stats['in_progress']
    return stats


# =============================================================================
# Feedback operations
# =============================================================================

class AlreadySubmitted(Exception):
    """Raised when a token tries to rate the same teacher-subject twice."""


def submit_feedback(token: str, combo: dict, all_combos: list, ratings: list,
                    comment: str, period: dict) -> bool:
    """
    Atomically save one feedback entry and record progress on the token.

    Returns True when this submission completed every combo (token is now used).
    Raises AlreadySubmitted if this combo was already rated with this token,
    and ValueError if the token is invalid or already used.
    """
    key = combo_key(combo['teacher'], combo['subject'])
    with get_db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        try:
            row = conn.execute(
                'SELECT is_used, completed FROM tokens WHERE token = ?', (token,)
            ).fetchone()
            if row is None or row['is_used']:
                raise ValueError('Invalid or used token')
            completed = set(json.loads(row['completed']))
            if key in completed:
                raise AlreadySubmitted(key)

            conn.execute(f'''
                INSERT INTO feedback
                (teacher, subject, semester, academic_session, branch,
                 {', '.join(QUESTION_COLUMNS)}, comment)
                VALUES ({', '.join('?' * (6 + len(QUESTION_COLUMNS)))})
            ''', (combo['teacher'], combo['subject'], period['semester'],
                  period['session'], period['branch'], *ratings, comment or None))

            completed.add(key)
            required = {combo_key(c['teacher'], c['subject']) for c in all_combos}
            is_done = required <= completed
            conn.execute(
                'UPDATE tokens SET completed = ?, is_used = ? WHERE token = ?',
                (json.dumps(sorted(completed)), int(is_done), token)
            )
            conn.commit()
            return is_done
        except Exception:
            conn.rollback()
            raise


def _where(period: dict | None = None, teacher: str | None = None,
           subject: str | None = None) -> tuple[str, list]:
    """Build a WHERE clause for the optional period / teacher / subject filters."""
    clauses, params = [], []
    if period:
        clauses.append('semester IS ? AND academic_session IS ? AND branch IS ?')
        params += [period['semester'], period['session'], period['branch']]
    if teacher is not None:
        clauses.append('teacher = ?')
        params.append(teacher)
    if subject is not None:
        clauses.append('subject = ?')
        params.append(subject)
    return ('WHERE ' + ' AND '.join(clauses) if clauses else ''), params


def _avg_columns() -> str:
    avgs = ', '.join(f'ROUND(AVG({q}), 2) AS {q}' for q in QUESTION_COLUMNS)
    overall = ' + '.join(f'AVG({q})' for q in QUESTION_COLUMNS)
    return f'{avgs}, ROUND(({overall}) / {len(QUESTION_COLUMNS)}, 2) AS overall'


def get_feedback(period: dict | None = None, teacher: str | None = None,
                 subject: str | None = None) -> list:
    """Get feedback entries, optionally filtered by period, teacher and/or subject."""
    where, params = _where(period, teacher, subject)
    with get_db() as conn:
        rows = conn.execute(
            f'SELECT * FROM feedback {where} ORDER BY teacher, subject, submitted_at', params
        ).fetchall()
    return [dict(r) for r in rows]


def get_teacher_summary(period: dict | None = None) -> list:
    """Average ratings per teacher-subject pair."""
    where, params = _where(period)
    with get_db() as conn:
        rows = conn.execute(f'''
            SELECT teacher, subject, COUNT(*) AS responses,
                   COUNT(NULLIF(TRIM(comment), '')) AS comments,
                   {_avg_columns()}
            FROM feedback {where}
            GROUP BY teacher, subject
            ORDER BY overall DESC
        ''', params).fetchall()
    return [dict(r) for r in rows]


def get_question_averages(period: dict | None = None, teacher: str | None = None,
                          subject: str | None = None) -> dict:
    """Average rating per question, plus `overall` and `responses`."""
    where, params = _where(period, teacher, subject)
    with get_db() as conn:
        row = conn.execute(
            f'SELECT COUNT(*) AS responses, {_avg_columns()} FROM feedback {where}', params
        ).fetchone()
    return dict(row)


def get_periods() -> list:
    """Distinct academic periods that have feedback, newest first."""
    with get_db() as conn:
        rows = conn.execute('''
            SELECT semester, academic_session AS session, branch, COUNT(*) AS responses
            FROM feedback
            GROUP BY semester, academic_session, branch
            ORDER BY academic_session DESC, semester DESC, branch
        ''').fetchall()
    return [dict(r) for r in rows]


def reset_database():
    """Delete all tokens and feedback."""
    with get_db() as conn:
        conn.execute('DELETE FROM feedback')
        conn.execute('DELETE FROM tokens')
        conn.commit()
