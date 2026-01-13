"""
Database operations for the Anonymous Feedback System.
Uses SQLite for local-only storage.
"""

import sqlite3
from contextlib import contextmanager
from config import DATABASE_PATH


def init_db():
    """Initialize the database with required tables."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Create tokens table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tokens (
                token TEXT PRIMARY KEY,
                is_used INTEGER DEFAULT 0
            )
        ''')
        
        # Create feedback table (no token reference for anonymity)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher TEXT NOT NULL,
                subject TEXT NOT NULL,
                q1 INTEGER NOT NULL,
                q2 INTEGER NOT NULL,
                q3 INTEGER NOT NULL,
                q4 INTEGER NOT NULL,
                q5 INTEGER NOT NULL,
                q6 INTEGER NOT NULL,
                q7 INTEGER NOT NULL,
                q8 INTEGER NOT NULL,
                q9 INTEGER NOT NULL,
                q10 INTEGER NOT NULL,
                comment TEXT,
                submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# Token operations
def add_tokens(tokens: list):
    """Add multiple tokens to the database."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.executemany(
            'INSERT OR IGNORE INTO tokens (token, is_used) VALUES (?, 0)',
            [(t,) for t in tokens]
        )
        conn.commit()
        return cursor.rowcount


def validate_token(token: str) -> bool:
    """Check if a token is valid (exists and unused)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT is_used FROM tokens WHERE token = ?',
            (token,)
        )
        row = cursor.fetchone()
        return row is not None and row['is_used'] == 0


def mark_token_used(token: str) -> bool:
    """Mark a token as used. Returns True if successful."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE tokens SET is_used = 1 WHERE token = ? AND is_used = 0',
            (token,)
        )
        conn.commit()
        return cursor.rowcount > 0


def get_token_stats() -> dict:
    """Get token statistics for admin dashboard."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as total FROM tokens')
        total = cursor.fetchone()['total']
        
        cursor.execute('SELECT COUNT(*) as used FROM tokens WHERE is_used = 1')
        used = cursor.fetchone()['used']
        
        return {
            'total': total,
            'used': used,
            'unused': total - used
        }


# Feedback operations
def save_feedback(teacher: str, subject: str, ratings: list, comment: str):
    """Save feedback to database."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO feedback 
            (teacher, subject, q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, comment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (teacher, subject, *ratings, comment))
        conn.commit()


def get_all_feedback() -> list:
    """Get all feedback entries."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM feedback ORDER BY submitted_at DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]


def get_feedback_by_teacher(teacher: str) -> list:
    """Get feedback for a specific teacher."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM feedback WHERE teacher = ? ORDER BY submitted_at DESC
        ''', (teacher,))
        return [dict(row) for row in cursor.fetchall()]


def get_feedback_by_subject(subject: str) -> list:
    """Get feedback for a specific subject."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM feedback WHERE subject = ? ORDER BY submitted_at DESC
        ''', (subject,))
        return [dict(row) for row in cursor.fetchall()]


def get_teacher_summary() -> list:
    """Get average ratings per teacher."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                teacher,
                COUNT(*) as feedback_count,
                ROUND(AVG(q1), 2) as avg_q1,
                ROUND(AVG(q2), 2) as avg_q2,
                ROUND(AVG(q3), 2) as avg_q3,
                ROUND(AVG(q4), 2) as avg_q4,
                ROUND(AVG(q5), 2) as avg_q5,
                ROUND(AVG(q6), 2) as avg_q6,
                ROUND(AVG(q7), 2) as avg_q7,
                ROUND(AVG(q8), 2) as avg_q8,
                ROUND(AVG(q9), 2) as avg_q9,
                ROUND(AVG(q10), 2) as avg_q10,
                ROUND((AVG(q1) + AVG(q2) + AVG(q3) + AVG(q4) + AVG(q5) + 
                       AVG(q6) + AVG(q7) + AVG(q8) + AVG(q9) + AVG(q10)) / 10, 2) as overall_avg
            FROM feedback
            GROUP BY teacher
            ORDER BY overall_avg DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]


def get_question_averages() -> dict:
    """Get average rating for each question across all feedback."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                ROUND(AVG(q1), 2) as q1,
                ROUND(AVG(q2), 2) as q2,
                ROUND(AVG(q3), 2) as q3,
                ROUND(AVG(q4), 2) as q4,
                ROUND(AVG(q5), 2) as q5,
                ROUND(AVG(q6), 2) as q6,
                ROUND(AVG(q7), 2) as q7,
                ROUND(AVG(q8), 2) as q8,
                ROUND(AVG(q9), 2) as q9,
                ROUND(AVG(q10), 2) as q10
            FROM feedback
        ''')
        row = cursor.fetchone()
        if row:
            return dict(row)
        return {}
