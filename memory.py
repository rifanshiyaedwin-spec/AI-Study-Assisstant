import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.database import get_connection

def get_profile(student_id: int = 1) -> Dict[str, Any]:
    """Retrieves student profile."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM student_profile WHERE id = ?", (student_id,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        "id": 1,
        "name": "Alex Chen",
        "academic_level": "Undergraduate Engineering",
        "target_goal": "Master Renewable Energy Technologies",
        "learning_style": "Socratic & Conceptual",
        "study_hours_per_week": 10
    }

def update_profile(student_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Updates student profile fields."""
    conn = get_connection()
    allowed = ["name", "email", "academic_level", "target_goal", "learning_style", "study_hours_per_week"]
    set_clauses = []
    values = []
    for k, v in updates.items():
        if k in allowed:
            set_clauses.append(f"{k} = ?")
            values.append(v)
    if set_clauses:
        values.append(datetime.now().isoformat())
        values.append(student_id)
        sql = f"UPDATE student_profile SET {', '.join(set_clauses)}, updated_at = ? WHERE id = ?"
        conn.execute(sql, tuple(values))
        conn.commit()
    conn.close()
    return get_profile(student_id)

def add_memory_fact(
    student_id: int, 
    fact_type: str, 
    topic: str, 
    content: str, 
    confidence: float = 1.0
):
    """Adds or updates a memory fact about student comprehension or preference."""
    conn = get_connection()
    # Check if duplicate or update existing
    existing = conn.execute("""
        SELECT id FROM memory_facts 
        WHERE student_id = ? AND fact_type = ? AND topic = ?
    """, (student_id, fact_type, topic)).fetchone()

    now = datetime.now().isoformat()
    if existing:
        conn.execute("""
            UPDATE memory_facts 
            SET content = ?, confidence = ?, created_at = ?
            WHERE id = ?
        """, (content, confidence, now, existing["id"]))
    else:
        conn.execute("""
            INSERT INTO memory_facts (student_id, fact_type, topic, content, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (student_id, fact_type, topic, content, confidence, now))
    conn.commit()
    conn.close()

def get_memory_facts(student_id: int = 1, fact_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all memory facts for a student."""
    conn = get_connection()
    if fact_type:
        rows = conn.execute("""
            SELECT * FROM memory_facts 
            WHERE student_id = ? AND fact_type = ? 
            ORDER BY created_at DESC
        """, (student_id, fact_type)).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM memory_facts 
            WHERE student_id = ? 
            ORDER BY created_at DESC
        """, (student_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_weak_topics(student_id: int = 1) -> List[Dict[str, Any]]:
    """
    Computes weak topics dynamically based on quiz performance and memory facts.
    """
    conn = get_connection()
    # 1. From recorded weak_topic memory facts
    facts = conn.execute("""
        SELECT topic, content, confidence, created_at 
        FROM memory_facts 
        WHERE student_id = ? AND fact_type IN ('weak_topic', 'misconception')
        ORDER BY created_at DESC
    """, (student_id,)).fetchall()

    # 2. From quiz attempts with score < 75%
    low_quizzes = conn.execute("""
        SELECT q.topic, a.score, a.total_questions, a.percentage, a.answers_json, a.completed_at
        FROM quiz_attempts a
        JOIN quizzes q ON a.quiz_id = q.id
        WHERE a.student_id = ?
        ORDER BY a.completed_at DESC
    """, (student_id,)).fetchall()
    conn.close()

    topic_stats: Dict[str, Dict[str, Any]] = {}

    for q in low_quizzes:
        topic = q["topic"]
        if topic not in topic_stats:
            topic_stats[topic] = {
                "topic": topic,
                "total_quizzes": 0,
                "total_score": 0,
                "total_questions": 0,
                "latest_percentage": q["percentage"],
                "missed_concepts": []
            }
        topic_stats[topic]["total_quizzes"] += 1
        topic_stats[topic]["total_score"] += q["score"]
        topic_stats[topic]["total_questions"] += q["total_questions"]

        # Parse wrong answers to identify specific missed concepts
        try:
            answers = json.loads(q["answers_json"])
            for ans in answers:
                if not ans.get("is_correct") and ans.get("related_topic"):
                    topic_stats[topic]["missed_concepts"].append(ans["related_topic"])
        except Exception:
            pass

    # Collect topics with average score < 75% or explicitly recorded weak topics
    weak_list = []
    for topic, stats in topic_stats.items():
        avg_pct = (stats["total_score"] / stats["total_questions"] * 100) if stats["total_questions"] > 0 else 0
        if avg_pct < 75:
            # Dedup missed concepts
            unique_missed = list(set(stats["missed_concepts"]))
            weak_list.append({
                "topic": topic,
                "average_score": round(avg_pct, 1),
                "quizzes_taken": stats["total_quizzes"],
                "missed_concepts": unique_missed,
                "recommendation": f"Review key concepts in {topic}" + (f" (focus on {', '.join(unique_missed[:3])})" if unique_missed else "")
            })

    # Add explicitly recorded memory facts if not already included
    existing_topics = {w["topic"].lower() for w in weak_list}
    for f in facts:
        t = f["topic"]
        if t.lower() not in existing_topics:
            weak_list.append({
                "topic": t,
                "average_score": 50.0,
                "quizzes_taken": 1,
                "missed_concepts": [f["content"]],
                "recommendation": f"Revision needed: {f['content']}"
            })
            existing_topics.add(t.lower())

    return weak_list

def log_study_activity(
    student_id: int, 
    activity_type: str, 
    description: str, 
    duration_minutes: int = 15,
    score: Optional[float] = None
):
    """Records an activity event into the student's study timeline."""
    conn = get_connection()
    now = datetime.now().isoformat()
    conn.execute("""
        INSERT INTO study_logs (student_id, activity_type, description, duration_minutes, score, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (student_id, activity_type, description, duration_minutes, score, now))
    conn.commit()
    conn.close()

def get_recent_chat_history(conversation_id: int, limit: int = 6) -> List[Dict[str, str]]:
    """Returns recent exchanges in a conversation."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT sender, content 
        FROM chat_messages 
        WHERE conversation_id = ? 
        ORDER BY id DESC LIMIT ?
    """, (conversation_id, limit)).fetchall()
    conn.close()
    # Reverse to chronological order
    return [{"sender": r["sender"], "content": r["content"]} for r in reversed(rows)]
