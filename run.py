import os
import sys
import uvicorn
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.database import init_db, get_connection
from backend.app import load_sample_material
from backend.quiz import generate_quiz, evaluate_quiz_submission
from backend.planner import generate_learning_plan, toggle_session_status

def bootstrap():
    print("=" * 65)
    print("  AI Learning and Study Assistant - Personal Virtual Tutor")
    print("=" * 65)
    print("[1/4] Initializing SQLite database and schema...")
    init_db()
    
    print("[2/4] Indexing sample course material (Renewable Energy Technologies)...")
    try:
        sample_res = load_sample_material()
        print(f"      -> {sample_res.get('message', 'Indexed successfully')}")
    except Exception as e:
        print(f"      -> Sample loading notice: {e}")

    print("[3/4] Seeding baseline learning plan & sample quiz history...")
    conn = get_connection()
    # Check if we already have plans
    plan_count = conn.execute("SELECT COUNT(*) FROM learning_plans").fetchone()[0]
    if plan_count == 0:
        plan = generate_learning_plan(
            subject="Renewable Energy Technologies",
            goal="Master Core Principles & Score 90%+ in Finals",
            total_days=7,
            daily_hours=1.5,
            difficulty="intermediate",
            student_id=1
        )
        # Mark day 1 completed
        if plan.get("sessions"):
            first_session_id = plan["sessions"][0]["id"]
            toggle_session_status(first_session_id, 1)

    # Check if we already have quiz attempts
    quiz_count = conn.execute("SELECT COUNT(*) FROM quiz_attempts").fetchone()[0]
    if quiz_count == 0:
        # Generate an initial quiz and submit a realistic attempt (e.g. 3/5 = 60%, flagging weak areas as in user prompt!)
        quiz = generate_quiz(
            topic="Solar Photovoltaic Systems",
            material_id=None,
            difficulty="intermediate",
            question_count=5,
            student_id=1
        )
        if quiz.get("questions"):
            # Intentionally miss 2 questions to demonstrate weak topic detection & revision advice!
            # Example user prompt: "You scored 6/10 in Solar PV Systems. You may want to revise PV modules, charge controllers, and inverters."
            mock_answers = {}
            for idx, q in enumerate(quiz["questions"]):
                if idx in [0, 1, 4]:
                    # Pick correct answer
                    mock_answers[str(q["id"])] = q["options"][0]
                else:
                    # Pick wrong distractor
                    mock_answers[str(q["id"])] = q["options"][-1]
            evaluate_quiz_submission(quiz["quiz_id"], mock_answers, student_id=1)

    conn.close()

    print("[4/4] System ready! Starting server on http://127.0.0.1:8000 ...")
    print("=" * 65)

if __name__ == "__main__":
    bootstrap()
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=False)
