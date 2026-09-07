import json
import random
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.database import get_connection, get_setting
from backend.rag import vector_store
from backend.memory import add_memory_fact, log_study_activity

# Pre-curated high-yield question templates derived from course knowledge base
KNOWLEDGE_BANK = [
    {
        "topic": "Solar Photovoltaic Systems",
        "question_text": "What fundamental physical effect converts photon energy directly into DC electricity in a solar cell?",
        "question_type": "mcq",
        "options": [
            "The Photovoltaic Effect",
            "The Thermoelectric Seebeck Effect",
            "The Electromagnetic Induction Principle",
            "The Piezoelectric Effect"
        ],
        "correct_answer": "The Photovoltaic Effect",
        "explanation": "Solar cells convert photon energy directly into DC electricity through the photovoltaic effect occurring across a p-n semiconductor junction.",
        "source_page": 1,
        "related_topic": "Photovoltaic Effect & Physics"
    },
    {
        "topic": "Solar Photovoltaic Systems",
        "question_text": "Under Standard Test Conditions (STC), what is the typical DC open-circuit voltage produced by a single silicon solar cell?",
        "question_type": "mcq",
        "options": [
            "0.5 to 0.6 Volts",
            "1.2 to 1.5 Volts",
            "3.6 to 4.2 Volts",
            "12 to 24 Volts"
        ],
        "correct_answer": "0.5 to 0.6 Volts",
        "explanation": "A single silicon p-n junction cell produces approximately 0.5V to 0.6V DC under STC (1000 W/m², 25°C). Multiple cells are wired in series inside modules to increase voltage.",
        "source_page": 1,
        "related_topic": "Solar PV Cell Hierarchy"
    },
    {
        "topic": "Solar Charge Controllers",
        "question_text": "Why do MPPT (Maximum Power Point Tracking) charge controllers outperform standard PWM controllers by 20% to 35%?",
        "question_type": "mcq",
        "options": [
            "MPPT converts surplus array voltage into additional charging current using high-frequency DC-DC conversion",
            "MPPT converts alternating current into high-voltage direct current",
            "MPPT physically rotates the PV panels toward the sun using mechanical actuators",
            "MPPT eliminates all electrical resistance inside the battery storage bank"
        ],
        "correct_answer": "MPPT converts surplus array voltage into additional charging current using high-frequency DC-DC conversion",
        "explanation": "MPPT controllers continuously track the Vmp and Imp point of the array, converting excess DC voltage into higher charging current through efficient switch-mode power conversion.",
        "source_page": 2,
        "related_topic": "Charge Controllers"
    },
    {
        "topic": "Solar Power Inverters",
        "question_text": "What is the primary function of Anti-Islanding Protection (IEEE 1547 / UL 1741) in grid-tied solar inverters?",
        "question_type": "mcq",
        "options": [
            "Automatically disconnecting the inverter from the grid within milliseconds during a power outage to protect utility linemen",
            "Preventing salt-spray corrosion on panels installed on coastal islands",
            "Increasing inverter output voltage during localized grid brownouts",
            "Disconnecting solar panels when battery state-of-charge reaches 100%"
        ],
        "correct_answer": "Automatically disconnecting the inverter from the grid within milliseconds during a power outage to protect utility linemen",
        "explanation": "Anti-islanding shuts down the inverter when grid power drops, preventing dangerous back-feeding of energized current into power lines undergoing repair.",
        "source_page": 2,
        "related_topic": "Power Inverters"
    },
    {
        "topic": "Battery Storage Technologies",
        "question_text": "Compared to traditional Lead-Acid batteries, what is a primary advantage of Lithium-Iron-Phosphate (LiFePO4) batteries?",
        "question_type": "mcq",
        "options": [
            "Dramatically longer cycle life (4000-7000 cycles) and higher safe Depth of Discharge (80-90% DoD)",
            "Heavier weight and lower energy density requiring structural reinforcement",
            "Lower upfront capital cost per kilowatt-hour of initial capacity",
            "Zero requirement for thermal monitoring or battery management circuitry"
        ],
        "correct_answer": "Dramatically longer cycle life (4000-7000 cycles) and higher safe Depth of Discharge (80-90% DoD)",
        "explanation": "LiFePO4 batteries tolerate 80-90% Depth of Discharge with 4000+ cycles, whereas lead-acid batteries degrade rapidly if discharged beyond 50% DoD.",
        "source_page": 2,
        "related_topic": "Battery Storage"
    },
    {
        "topic": "Wind Energy Systems",
        "question_text": "According to the Betz Law (1919), what is the maximum theoretical aerodynamic power coefficient (Cp,max) that any wind turbine can extract from wind?",
        "question_type": "mcq",
        "options": [
            "16/27 or approximately 59.3%",
            "50.0% exactly",
            "100.0% with perfect airfoil design",
            "33.3% or 1/3"
        ],
        "correct_answer": "16/27 or approximately 59.3%",
        "explanation": "The Betz limit establishes that no turbine rotor can capture more than 59.3% (16/27) of the kinetic energy in wind without completely stopping airflow.",
        "source_page": 3,
        "related_topic": "Betz Limit & Aerodynamics"
    },
    {
        "topic": "Wind Energy Systems",
        "question_text": "How does available kinetic power in an air stream scale with wind velocity v?",
        "question_type": "mcq",
        "options": [
            "Power scales with the cube of velocity: P ∝ v³",
            "Power scales linearly with velocity: P ∝ v",
            "Power scales with the square of velocity: P ∝ v²",
            "Power is inversely proportional to velocity: P ∝ 1/v"
        ],
        "correct_answer": "Power scales with the cube of velocity: P ∝ v³",
        "explanation": "The wind power equation is P = 0.5 * rho * A * v³. Because power scales with v³, doubling wind velocity yields an 8-fold (2³ = 8) increase in power.",
        "source_page": 3,
        "related_topic": "Wind Power Equation"
    },
    {
        "topic": "Solar Photovoltaic Systems",
        "question_text": "True or False: Wiring solar modules in series increases the total circuit current while keeping voltage identical to a single panel.",
        "question_type": "true_false",
        "options": ["True", "False"],
        "correct_answer": "False",
        "explanation": "False. Connecting modules in series adds their voltages together while maintaining the same current. Parallel connection increases current while maintaining voltage.",
        "source_page": 1,
        "related_topic": "PV Modules & Strings"
    },
    {
        "topic": "Solar System Sizing",
        "question_text": "What does one 'Peak Sun Hour' (PSH) represent in solar engineering?",
        "question_type": "mcq",
        "options": [
            "One hour of equivalent solar irradiance at 1000 W/m² (totaling 1 kWh/m²)",
            "The exact hour at solar noon when the sun reaches its zenith",
            "The total number of daylight hours between sunrise and sunset",
            "The maximum operating temperature duration of a silicon solar module"
        ],
        "correct_answer": "One hour of equivalent solar irradiance at 1000 W/m² (totaling 1 kWh/m²)",
        "explanation": "Peak Sun Hours represent the equivalent hours per day at an irradiance of 1000 W/m². For example, 5 kWh/m²/day equals 5 Peak Sun Hours.",
        "source_page": 3,
        "related_topic": "Solar Sizing & Economics"
    },
    {
        "topic": "Solar Power Inverters",
        "question_text": "True or False: Modern crystalline silicon solar panels increase their electrical power output as the cell operating temperature rises above 25°C.",
        "question_type": "true_false",
        "options": ["True", "False"],
        "correct_answer": "False",
        "explanation": "False. Crystalline silicon has a negative temperature coefficient (typically -0.4% per °C), meaning voltage and overall power decrease as temperatures rise above 25°C.",
        "source_page": 3,
        "related_topic": "Temperature Derating"
    }
]

def generate_quiz(
    topic: str = "Solar Photovoltaic Systems",
    material_id: Optional[int] = None,
    difficulty: str = "intermediate",
    question_count: int = 5,
    student_id: int = 1
) -> Dict[str, Any]:
    """
    Generates a structured quiz from course materials and knowledge base.
    Persists the quiz into SQLite and returns the quiz with question metadata.
    """
    # 1. Search relevant chunks for grounding
    chunks = vector_store.search(topic, top_k=4, material_id=material_id)
    
    # Filter candidates from knowledge bank matching topic keywords or general pool
    topic_keywords = [k.lower() for k in topic.split() if len(k) > 2]
    matching = []
    others = []
    
    for q in KNOWLEDGE_BANK:
        q_text = (q["topic"] + " " + q["question_text"] + " " + q["related_topic"]).lower()
        if any(k in q_text for k in topic_keywords):
            matching.append(q)
        else:
            others.append(q)

    # Combine with matching first
    random.shuffle(matching)
    random.shuffle(others)
    selected_questions = matching + others
    selected_questions = selected_questions[:question_count]

    # If user asked for more than available in bank, synthesize additional questions from RAG chunks
    if len(selected_questions) < question_count and chunks:
        for idx, chunk in enumerate(chunks):
            if len(selected_questions) >= question_count:
                break
            heading = chunk.get("heading") or "General"
            snippet = chunk.get("content", "")[:200]
            new_q = {
                "topic": topic,
                "question_text": f"According to course notes on '{heading}', what is a critical consideration for this topic?",
                "question_type": "mcq",
                "options": [
                    f"Compliance with operating constraints described in: '{snippet[:60]}...'",
                    "Operating completely independently of all atmospheric and temperature variables",
                    "Requiring zero balance-of-system hardware or circuit protection",
                    "Replacing all semiconductor components with mechanical commutators"
                ],
                "correct_answer": f"Compliance with operating constraints described in: '{snippet[:60]}...'",
                "explanation": f"The course material emphasizes this principle on Page {chunk.get('page_number', 1)} under section {heading}.",
                "source_page": chunk.get("page_number", 1),
                "related_topic": heading
            }
            selected_questions.append(new_q)

    # Insert quiz into database
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO quizzes (material_id, topic, difficulty, question_count, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (material_id, topic, difficulty, len(selected_questions), now))
    quiz_id = cursor.lastrowid

    # Insert questions
    formatted_questions = []
    for order, q in enumerate(selected_questions, 1):
        cursor.execute("""
            INSERT INTO quiz_questions (
                quiz_id, question_order, question_type, question_text, 
                options_json, correct_answer, explanation, source_page, related_topic
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            quiz_id, order, q["question_type"], q["question_text"],
            json.dumps(q["options"]), q["correct_answer"], q["explanation"],
            q.get("source_page", 1), q.get("related_topic", topic)
        ))
        q_id = cursor.lastrowid
        formatted_questions.append({
            "id": q_id,
            "order": order,
            "question_type": q["question_type"],
            "question_text": q["question_text"],
            "options": q["options"],
            "source_page": q.get("source_page", 1),
            "related_topic": q.get("related_topic", topic)
        })

    conn.commit()
    conn.close()

    return {
        "quiz_id": quiz_id,
        "topic": topic,
        "difficulty": difficulty,
        "total_questions": len(formatted_questions),
        "questions": formatted_questions,
        "created_at": now
    }

def evaluate_quiz_submission(
    quiz_id: int,
    user_answers: Dict[str, str],
    student_id: int = 1
) -> Dict[str, Any]:
    """
    Evaluates student answers, scores the quiz, computes explanations,
    and automatically updates student memory and weak-topic tracking.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Fetch quiz and questions
    quiz_row = cursor.execute("SELECT * FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()
    if not quiz_row:
        conn.close()
        return {"error": "Quiz not found"}

    question_rows = cursor.execute("""
        SELECT * FROM quiz_questions WHERE quiz_id = ? ORDER BY question_order ASC
    """, (quiz_id,)).fetchall()

    correct_count = 0
    total_questions = len(question_rows)
    evaluations = []
    weak_concepts = []

    for q in question_rows:
        qid = str(q["id"])
        user_choice = user_answers.get(qid, "").strip()
        correct = q["correct_answer"].strip()
        is_correct = (user_choice.lower() == correct.lower())

        if is_correct:
            correct_count += 1
        else:
            related = q["related_topic"] or quiz_row["topic"]
            weak_concepts.append(related)

        evaluations.append({
            "question_id": q["id"],
            "order": q["question_order"],
            "question_text": q["question_text"],
            "user_answer": user_choice,
            "correct_answer": correct,
            "is_correct": is_correct,
            "explanation": q["explanation"],
            "source_page": q["source_page"],
            "related_topic": q["related_topic"]
        })

    percentage = round((correct_count / total_questions * 100), 1) if total_questions > 0 else 0.0
    now = datetime.now().isoformat()

    # Record quiz attempt
    cursor.execute("""
        INSERT INTO quiz_attempts (quiz_id, student_id, score, total_questions, percentage, answers_json, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (quiz_id, student_id, correct_count, total_questions, percentage, json.dumps(evaluations), now))
    attempt_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Update Memory Facts if weak concepts identified
    unique_weaks = list(set(weak_concepts))
    if unique_weaks:
        for concept in unique_weaks:
            add_memory_fact(
                student_id=student_id,
                fact_type="weak_topic",
                topic=concept,
                content=f"Missed question in {quiz_row['topic']} quiz. Needs revision on {concept}.",
                confidence=0.85
            )

    # Log study activity
    log_study_activity(
        student_id=student_id,
        activity_type="quiz",
        description=f"Completed {quiz_row['topic']} Quiz ({correct_count}/{total_questions})",
        duration_minutes=15,
        score=percentage
    )

    # Build student feedback message
    feedback = f"You scored {correct_count}/{total_questions} ({percentage}%) in {quiz_row['topic']}."
    if percentage >= 85:
        feedback += " Outstanding performance! You demonstrate strong mastery of this material."
    elif percentage >= 70:
        feedback += " Good effort! Review the missed questions below to solidify your understanding."
    else:
        if unique_weaks:
            feedback += f" You may want to revise {', '.join(unique_weaks[:3])}."
        else:
            feedback += " Consider reviewing the course chapter before attempting another quiz."

    return {
        "attempt_id": attempt_id,
        "quiz_id": quiz_id,
        "topic": quiz_row["topic"],
        "score": correct_count,
        "total_questions": total_questions,
        "percentage": percentage,
        "feedback": feedback,
        "weak_topics_flagged": unique_weaks,
        "evaluations": evaluations
    }
