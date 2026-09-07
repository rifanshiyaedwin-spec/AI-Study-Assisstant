from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.database import get_connection
from backend.memory import get_profile, log_study_activity

DEFAULT_CURRICULUM_TEMPLATES = {
    "renewable energy": [
        {
            "day": 1,
            "title": "Solar Radiation & Fundamentals",
            "topic": "Solar Irradiance, GHI, DNI & Atmospheric Effects",
            "objective": "Understand solar spectrum, solar constant (1361 W/m²), and irradiance calculation formulas.",
            "reading": "Chapter 1: Fundamentals of Renewable Energy and Solar Radiation (Pages 1-2)",
            "minutes": 45
        },
        {
            "day": 2,
            "title": "Semiconductor Physics & Photovoltaic Effect",
            "topic": "P-N Junction, Silicon Doping & Bandgap",
            "objective": "Master how photon absorption liberates electron-hole pairs across depletion region.",
            "reading": "Chapter 2.1: The Photovoltaic Effect & Semiconductor Physics (Page 1)",
            "minutes": 60
        },
        {
            "day": 3,
            "title": "Cell, Module & Array Architectures",
            "topic": "Series vs Parallel Connections & Derating",
            "objective": "Analyze IV characteristics, cell open-circuit voltages (0.5-0.6V), and string voltages.",
            "reading": "Chapter 2.2: Solar Photovoltaic Cell to Array Hierarchy (Page 2)",
            "minutes": 45
        },
        {
            "day": 4,
            "title": "Solar Charge Controllers",
            "topic": "PWM vs MPPT Algorithms",
            "objective": "Compare DC-DC switch-mode tracking against nominal voltage clamping; understand 20-35% gain.",
            "reading": "Chapter 3.1: Solar Charge Controllers (Page 2)",
            "minutes": 50
        },
        {
            "day": 5,
            "title": "Inverters & Anti-Islanding Protection",
            "topic": "DC-to-AC Pure Sine Wave & IEEE 1547 Standards",
            "objective": "Learn H-bridge inverter design, grid frequency synchronization, and safety disconnects.",
            "reading": "Chapter 3.2: Power Inverters & Grid Synchronization (Page 2)",
            "minutes": 60
        },
        {
            "day": 6,
            "title": "Battery Storage & Chemical Systems",
            "topic": "Lead-Acid vs LiFePO4 Depth of Discharge (DoD)",
            "objective": "Evaluate cycle life, temperature degradation, and Battery Management Systems (BMS).",
            "reading": "Chapter 3.3: Battery Storage Technologies (Pages 2-3)",
            "minutes": 45
        },
        {
            "day": 7,
            "title": "Wind Energy, Aerodynamics & Betz Limit",
            "topic": "Wind Power Equation P ∝ v³ & Betz 59.3% Maximum",
            "objective": "Derive Betz limit Cp,max = 0.593 and understand pitch/yaw mechanisms.",
            "reading": "Chapter 4: Wind Energy Systems and Aerodynamics (Page 3)",
            "minutes": 60
        }
    ]
}

def generate_learning_plan(
    subject: str = "Renewable Energy Technologies",
    goal: str = "Master Core Principles for Final Exam",
    total_days: int = 7,
    daily_hours: float = 1.5,
    difficulty: str = "intermediate",
    student_id: int = 1
) -> Dict[str, Any]:
    """
    Creates a tailored, multi-day study schedule divided into manageable daily sessions.
    """
    profile = get_profile(student_id)
    subject_key = "renewable energy" if "renew" in subject.lower() or "solar" in subject.lower() else "general"

    template = DEFAULT_CURRICULUM_TEMPLATES.get(subject_key, DEFAULT_CURRICULUM_TEMPLATES["renewable energy"])
    
    # Scale or repeat sessions to match requested total_days
    sessions_to_create = []
    for day in range(1, total_days + 1):
        tpl_idx = (day - 1) % len(template)
        tpl_item = template[tpl_idx]
        sessions_to_create.append({
            "day": day,
            "order": 1,
            "title": f"Day {day}: {tpl_item['title']}",
            "topic": tpl_item["topic"],
            "objective": tpl_item["objective"],
            "reading": tpl_item["reading"],
            "minutes": int(daily_hours * 60)
        })

    # Save to database
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO learning_plans (student_id, subject, goal, total_days, daily_hours, difficulty, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'active', ?)
    """, (student_id, subject, goal, total_days, daily_hours, difficulty, now))
    plan_id = cursor.lastrowid

    plan_sessions = []
    for s in sessions_to_create:
        cursor.execute("""
            INSERT INTO plan_sessions (
                plan_id, day_number, session_order, title, topic, 
                objective, reading_references, estimated_minutes, is_completed, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, NULL)
        """, (
            plan_id, s["day"], s["order"], s["title"], s["topic"],
            s["objective"], s["reading"], s["minutes"]
        ))
        s_id = cursor.lastrowid
        plan_sessions.append({
            "id": s_id,
            "day_number": s["day"],
            "title": s["title"],
            "topic": s["topic"],
            "objective": s["objective"],
            "reading_references": s["reading"],
            "estimated_minutes": s["minutes"],
            "is_completed": False
        })

    conn.commit()
    conn.close()

    # Log activity
    log_study_activity(student_id, "plan_session", f"Created {total_days}-Day Study Plan: '{goal}'", 10)

    return {
        "plan_id": plan_id,
        "subject": subject,
        "goal": goal,
        "total_days": total_days,
        "daily_hours": daily_hours,
        "difficulty": difficulty,
        "sessions": plan_sessions,
        "progress_percentage": 0.0,
        "created_at": now
    }

def toggle_session_status(session_id: int, student_id: int = 1) -> Dict[str, Any]:
    """Toggles session completion and updates overall plan progress."""
    conn = get_connection()
    cursor = conn.cursor()

    session = cursor.execute("SELECT * FROM plan_sessions WHERE id = ?", (session_id,)).fetchone()
    if not session:
        conn.close()
        return {"error": "Session not found"}

    new_status = 0 if session["is_completed"] else 1
    now = datetime.now().isoformat() if new_status else None

    cursor.execute("""
        UPDATE plan_sessions 
        SET is_completed = ?, completed_at = ? 
        WHERE id = ?
    """, (new_status, now, session_id))

    # Get overall plan progress
    plan_id = session["plan_id"]
    stats = cursor.execute("""
        SELECT COUNT(*) as total, SUM(is_completed) as completed
        FROM plan_sessions
        WHERE plan_id = ?
    """, (plan_id,)).fetchone()

    total = stats["total"] or 1
    completed = stats["completed"] or 0
    progress_pct = round((completed / total) * 100, 1)

    if progress_pct >= 100.0:
        cursor.execute("UPDATE learning_plans SET status = 'completed' WHERE id = ?", (plan_id,))

    conn.commit()
    conn.close()

    if new_status:
        log_study_activity(
            student_id, 
            "plan_session", 
            f"Completed Study Session: '{session['title']}'", 
            session["estimated_minutes"]
        )

    return {
        "session_id": session_id,
        "is_completed": bool(new_status),
        "plan_id": plan_id,
        "completed_count": completed,
        "total_count": total,
        "progress_percentage": progress_pct
    }

def get_active_plans(student_id: int = 1) -> List[Dict[str, Any]]:
    """Retrieves all active learning plans for student."""
    conn = get_connection()
    cursor = conn.cursor()
    plans = cursor.execute("""
        SELECT * FROM learning_plans 
        WHERE student_id = ? 
        ORDER BY created_at DESC
    """, (student_id,)).fetchall()

    result = []
    for p in plans:
        sessions = cursor.execute("""
            SELECT * FROM plan_sessions 
            WHERE plan_id = ? 
            ORDER BY day_number ASC, session_order ASC
        """, (p["id"],)).fetchall()
        
        session_list = [dict(s) for s in sessions]
        completed_count = sum(1 for s in session_list if s["is_completed"])
        total_count = len(session_list)
        pct = round((completed_count / total_count * 100), 1) if total_count > 0 else 0.0

        result.append({
            "id": p["id"],
            "subject": p["subject"],
            "goal": p["goal"],
            "total_days": p["total_days"],
            "daily_hours": p["daily_hours"],
            "status": p["status"],
            "progress_percentage": pct,
            "completed_sessions": completed_count,
            "total_sessions": total_count,
            "sessions": session_list,
            "created_at": p["created_at"]
        })

    conn.close()
    return result
