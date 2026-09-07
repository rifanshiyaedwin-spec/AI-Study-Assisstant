import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from backend.database import get_connection
from backend.memory import get_weak_topics, get_profile

def get_learning_analytics(student_id: int = 1) -> Dict[str, Any]:
    """
    Computes comprehensive learning analytics, mastery levels,
    weak areas, and revision recommendations.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Total Study Logs and Hours
    logs = cursor.execute("""
        SELECT activity_type, description, duration_minutes, score, timestamp 
        FROM study_logs 
        WHERE student_id = ? 
        ORDER BY timestamp DESC
    """, (student_id,)).fetchall()

    total_study_minutes = sum(r["duration_minutes"] for r in logs)
    total_study_hours = round(total_study_minutes / 60.0, 1)

    # 2. Quiz Metrics
    quizzes = cursor.execute("""
        SELECT a.id, a.quiz_id, a.score, a.total_questions, a.percentage, a.answers_json, a.completed_at,
               q.topic
        FROM quiz_attempts a
        JOIN quizzes q ON a.quiz_id = q.id
        WHERE a.student_id = ?
        ORDER BY a.completed_at DESC
    """, (student_id,)).fetchall()

    total_quizzes = len(quizzes)
    if total_quizzes > 0:
        avg_score = round(sum(q["percentage"] for q in quizzes) / total_quizzes, 1)
    else:
        avg_score = 0.0

    # 3. Topic Mastery Breakdown
    topic_data: Dict[str, Dict[str, Any]] = {}
    for q in quizzes:
        t = q["topic"]
        if t not in topic_data:
            topic_data[t] = {"total_q": 0, "correct_q": 0, "attempts": 0}
        topic_data[t]["attempts"] += 1
        topic_data[t]["correct_q"] += q["score"]
        topic_data[t]["total_q"] += q["total_questions"]

    mastery_list = []
    for topic, d in topic_data.items():
        pct = round((d["correct_q"] / d["total_q"] * 100), 1) if d["total_q"] > 0 else 0.0
        status = "Mastered" if pct >= 80 else ("In Progress" if pct >= 60 else "Needs Revision")
        mastery_list.append({
            "topic": topic,
            "mastery_percentage": pct,
            "quizzes_taken": d["attempts"],
            "status": status
        })

    # If no quizzes yet, provide initial baseline topics
    if not mastery_list:
        mastery_list = [
            {"topic": "Solar Photovoltaic Systems", "mastery_percentage": 0.0, "quizzes_taken": 0, "status": "Not Started"},
            {"topic": "Solar Charge Controllers", "mastery_percentage": 0.0, "quizzes_taken": 0, "status": "Not Started"},
            {"topic": "Power Inverters & Grid Sync", "mastery_percentage": 0.0, "quizzes_taken": 0, "status": "Not Started"},
            {"topic": "Wind Energy & Betz Limit", "mastery_percentage": 0.0, "quizzes_taken": 0, "status": "Not Started"}
        ]

    # 4. Learning Plan Progress
    plans = cursor.execute("""
        SELECT COUNT(*) as total_plans FROM learning_plans WHERE student_id = ?
    """, (student_id,)).fetchone()
    
    session_stats = cursor.execute("""
        SELECT COUNT(*) as total, SUM(is_completed) as completed
        FROM plan_sessions s
        JOIN learning_plans p ON s.plan_id = p.id
        WHERE p.student_id = ?
    """, (student_id,)).fetchone()

    total_sessions = session_stats["total"] or 0
    completed_sessions = session_stats["completed"] or 0
    plan_pct = round((completed_sessions / total_sessions * 100), 1) if total_sessions > 0 else 0.0

    # 5. Course Materials Count
    materials_count = cursor.execute("SELECT COUNT(*) FROM course_materials").fetchone()[0]

    # 6. Recent Study Activity Timeline
    timeline = []
    for l in logs[:10]:
        timeline.append({
            "activity_type": l["activity_type"],
            "description": l["description"],
            "duration_minutes": l["duration_minutes"],
            "score": l["score"],
            "timestamp": l["timestamp"]
        })

    conn.close()

    # 7. Weak Topics & Revision Recommendations
    weak_topics = get_weak_topics(student_id)
    recommendations = []

    for w in weak_topics:
        recommendations.append({
            "topic": w["topic"],
            "average_score": w["average_score"],
            "missed_concepts": w.get("missed_concepts", []),
            "action_text": w["recommendation"],
            "suggested_action": f"Take a quick practice quiz or ask the AI tutor to explain {w['topic']}"
        })

    if not recommendations:
        recommendations.append({
            "topic": "General Revision",
            "average_score": 100.0,
            "missed_concepts": [],
            "action_text": "Great job! All tested topics meet high comprehension standards.",
            "suggested_action": "Try generating a challenging 10-question Advanced Quiz."
        })

    return {
        "overview": {
            "total_study_hours": total_study_hours,
            "total_quizzes": total_quizzes,
            "average_quiz_score": avg_score,
            "plan_progress_percentage": plan_pct,
            "completed_sessions": completed_sessions,
            "total_sessions": total_sessions,
            "course_materials_count": materials_count,
            "streak_days": 4
        },
        "mastery": mastery_list,
        "weak_areas": weak_topics,
        "recommendations": recommendations,
        "recent_activities": timeline
    }
