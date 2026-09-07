import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from backend.config import DB_PATH, DEFAULT_SETTINGS

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # 1. System Settings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # 2. Student Profile
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL DEFAULT 'Alex Chen',
        email TEXT DEFAULT 'alex.student@example.com',
        academic_level TEXT NOT NULL DEFAULT 'Undergraduate',
        target_goal TEXT NOT NULL DEFAULT 'Ace Renewable Energy & Engineering Exams',
        learning_style TEXT NOT NULL DEFAULT 'Socratic & Conceptual',
        study_hours_per_week INTEGER NOT NULL DEFAULT 10,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # 3. Course Materials
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS course_materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        display_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_type TEXT NOT NULL,
        subject TEXT NOT NULL DEFAULT 'General',
        file_size INTEGER NOT NULL DEFAULT 0,
        total_pages INTEGER NOT NULL DEFAULT 1,
        total_words INTEGER NOT NULL DEFAULT 0,
        chunk_count INTEGER NOT NULL DEFAULT 0,
        uploaded_at TEXT NOT NULL
    )
    """)

    # 4. Document Chunks
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS document_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        material_id INTEGER NOT NULL,
        chunk_index INTEGER NOT NULL,
        page_number INTEGER NOT NULL DEFAULT 1,
        heading TEXT,
        content TEXT NOT NULL,
        token_count INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (material_id) REFERENCES course_materials(id) ON DELETE CASCADE
    )
    """)

    # 5. Conversations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL DEFAULT 1,
        title TEXT NOT NULL,
        persona TEXT NOT NULL DEFAULT 'tutor',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (student_id) REFERENCES student_profile(id) ON DELETE CASCADE
    )
    """)

    # 6. Chat Messages
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL,
        sender TEXT NOT NULL, -- 'user' or 'assistant'
        content TEXT NOT NULL,
        citations_json TEXT, -- JSON array of {material_id, filename, page, score, snippet}
        created_at TEXT NOT NULL,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
    )
    """)

    # 7. Memory Facts (Student progress & preferences)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memory_facts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL DEFAULT 1,
        fact_type TEXT NOT NULL, -- 'preference', 'strong_topic', 'weak_topic', 'misconception', 'goal'
        topic TEXT NOT NULL,
        content TEXT NOT NULL,
        confidence REAL NOT NULL DEFAULT 1.0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (student_id) REFERENCES student_profile(id) ON DELETE CASCADE
    )
    """)

    # 8. Quizzes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quizzes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        material_id INTEGER,
        topic TEXT NOT NULL,
        difficulty TEXT NOT NULL DEFAULT 'intermediate',
        question_count INTEGER NOT NULL DEFAULT 5,
        created_at TEXT NOT NULL,
        FOREIGN KEY (material_id) REFERENCES course_materials(id) ON DELETE SET NULL
    )
    """)

    # 9. Quiz Questions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quiz_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id INTEGER NOT NULL,
        question_order INTEGER NOT NULL,
        question_type TEXT NOT NULL DEFAULT 'mcq', -- 'mcq', 'true_false', 'short_answer'
        question_text TEXT NOT NULL,
        options_json TEXT, -- JSON array for options
        correct_answer TEXT NOT NULL,
        explanation TEXT NOT NULL,
        source_page INTEGER DEFAULT 1,
        related_topic TEXT,
        FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
    )
    """)

    # 10. Quiz Attempts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quiz_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL DEFAULT 1,
        score INTEGER NOT NULL,
        total_questions INTEGER NOT NULL,
        percentage REAL NOT NULL,
        answers_json TEXT NOT NULL, -- JSON array of user responses & evaluation results
        completed_at TEXT NOT NULL,
        FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES student_profile(id) ON DELETE CASCADE
    )
    """)

    # 11. Learning Plans
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS learning_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL DEFAULT 1,
        subject TEXT NOT NULL,
        goal TEXT NOT NULL,
        total_days INTEGER NOT NULL DEFAULT 7,
        daily_hours REAL NOT NULL DEFAULT 1.5,
        difficulty TEXT NOT NULL DEFAULT 'intermediate',
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL,
        FOREIGN KEY (student_id) REFERENCES student_profile(id) ON DELETE CASCADE
    )
    """)

    # 12. Plan Sessions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS plan_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER NOT NULL,
        day_number INTEGER NOT NULL,
        session_order INTEGER NOT NULL,
        title TEXT NOT NULL,
        topic TEXT NOT NULL,
        objective TEXT NOT NULL,
        reading_references TEXT,
        estimated_minutes INTEGER NOT NULL DEFAULT 45,
        is_completed INTEGER NOT NULL DEFAULT 0,
        completed_at TEXT,
        FOREIGN KEY (plan_id) REFERENCES learning_plans(id) ON DELETE CASCADE
    )
    """)

    # 13. Study Activity Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS study_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL DEFAULT 1,
        activity_type TEXT NOT NULL, -- 'read', 'chat', 'quiz', 'plan_session', 'flashcard', 'timer'
        description TEXT NOT NULL,
        duration_minutes INTEGER NOT NULL DEFAULT 10,
        score REAL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (student_id) REFERENCES student_profile(id) ON DELETE CASCADE
    )
    """)

    # 14. Flashcard Decks
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS flashcard_decks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL DEFAULT 1,
        material_id INTEGER,
        title TEXT NOT NULL,
        topic TEXT NOT NULL,
        card_count INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (material_id) REFERENCES course_materials(id) ON DELETE SET NULL,
        FOREIGN KEY (student_id) REFERENCES student_profile(id) ON DELETE CASCADE
    )
    """)

    # 15. Flashcards
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS flashcards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        deck_id INTEGER NOT NULL,
        front_prompt TEXT NOT NULL,
        back_answer TEXT NOT NULL,
        source_page INTEGER DEFAULT 1,
        mastery_level INTEGER NOT NULL DEFAULT 0, -- 0: New, 1: Learning, 2: Review, 3: Mastered
        review_count INTEGER NOT NULL DEFAULT 0,
        next_review_at TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (deck_id) REFERENCES flashcard_decks(id) ON DELETE CASCADE
    )
    """)

    # Seed initial default student profile if not exists
    cursor.execute("SELECT COUNT(*) FROM student_profile")
    if cursor.fetchone()[0] == 0:
        now = datetime.now().isoformat()
        cursor.execute("""
        INSERT INTO student_profile (name, email, academic_level, target_goal, learning_style, study_hours_per_week, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'Alex Chen',
            'alex.student@example.com',
            'Undergraduate Engineering',
            'Master Renewable Energy Technologies & Score 90%+ in Finals',
            'Socratic & Conceptual',
            12,
            now,
            now
        ))

    # Seed default system settings
    for k, v in DEFAULT_SETTINGS.items():
        cursor.execute("""
        INSERT OR IGNORE INTO system_settings (key, value, updated_at)
        VALUES (?, ?, ?)
        """, (k, str(v), datetime.now().isoformat()))

    conn.commit()
    conn.close()

# Helper accessors
def get_setting(key: str, default: Any = None) -> Any:
    conn = get_connection()
    row = conn.execute("SELECT value FROM system_settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key: str, value: Any):
    conn = get_connection()
    now = datetime.now().isoformat()
    conn.execute("""
    INSERT INTO system_settings (key, value, updated_at)
    VALUES (?, ?, ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
    """, (key, str(value), now))
    conn.commit()
    conn.close()

def get_all_settings() -> Dict[str, str]:
    conn = get_connection()
    rows = conn.execute("SELECT key, value FROM system_settings").fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}
