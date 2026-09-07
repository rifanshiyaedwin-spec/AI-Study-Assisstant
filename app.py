import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import FRONTEND_DIR, UPLOAD_DIR, SAMPLE_DIR, DB_PATH
from backend.database import init_db, get_connection, get_all_settings, set_setting
from backend.document_processor import extract_text_from_file, chunk_document
from backend.rag import vector_store
from backend.memory import (
    get_profile, update_profile, get_memory_facts, 
    get_weak_topics, log_study_activity
)
from backend.tutor import generate_tutor_response
from backend.quiz import generate_quiz, evaluate_quiz_submission
from backend.planner import generate_learning_plan, toggle_session_status, get_active_plans
from backend.analytics import get_learning_analytics
from backend.tools import (
    generate_flashcard_deck, get_flashcard_decks, get_deck_cards,
    review_flashcard, generate_formula_cheatsheet
)

# Initialize Database on boot
init_db()

app = FastAPI(title="AI Learning and Study Assistant", version="2.0.0")

# Enable CORS for local web interactions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- PYDANTIC REQUEST SCHEMAS -----------------

class ChatRequest(BaseModel):
    query: str
    conversation_id: Optional[int] = None
    persona: Optional[str] = "tutor"
    material_id: Optional[int] = None

class NewConversationRequest(BaseModel):
    title: str = "New Study Session"
    persona: str = "tutor"

class QuizGenerateRequest(BaseModel):
    topic: str = "Solar Photovoltaic Systems"
    material_id: Optional[int] = None
    difficulty: str = "intermediate"
    question_count: int = 5

class QuizEvaluateRequest(BaseModel):
    quiz_id: int
    answers: Dict[str, str]

class PlanGenerateRequest(BaseModel):
    subject: str = "Renewable Energy Technologies"
    goal: str = "Master Core Principles for Final Exam"
    total_days: int = 7
    daily_hours: float = 1.5
    difficulty: str = "intermediate"

class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    academic_level: Optional[str] = None
    target_goal: Optional[str] = None
    learning_style: Optional[str] = None
    study_hours_per_week: Optional[int] = None

class SettingsUpdateRequest(BaseModel):
    settings: Dict[str, Any]

class FlashcardGenerateRequest(BaseModel):
    topic: str = "Solar Photovoltaic Systems"
    material_id: Optional[int] = None
    count: int = 5

class FlashcardReviewRequest(BaseModel):
    rating: str = "good"  # 'again', 'hard', 'good', 'easy'

class CheatsheetRequest(BaseModel):
    topic: str = "Renewable Energy Technologies"
    material_id: Optional[int] = None

class StudyTimerLogRequest(BaseModel):
    duration_minutes: int = 25
    description: str = "Pomodoro Focus Study Session"

class SemanticSearchRequest(BaseModel):
    query: str
    material_id: Optional[int] = None
    top_k: int = 5

# ----------------- COURSE MATERIAL ENDPOINTS -----------------

@app.get("/api/materials")
def list_materials():
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM course_materials ORDER BY uploaded_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/materials/upload")
async def upload_material(file: UploadFile = File(...), subject: str = Form("General")):
    filename = file.filename
    clean_name = Path(filename).name
    save_path = UPLOAD_DIR / f"{int(datetime.now().timestamp())}_{clean_name}"

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Process and extract text
    pages = extract_text_from_file(save_path)
    chunks = chunk_document(pages)
    
    total_words = sum(c["token_count"] for c in chunks)
    file_size = save_path.stat().st_size
    now = datetime.now().isoformat()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO course_materials (
            filename, display_name, file_path, file_type, subject, 
            file_size, total_pages, total_words, chunk_count, uploaded_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        clean_name,
        clean_name.replace(".pdf", "").replace(".txt", "").replace("_", " ").title(),
        str(save_path),
        save_path.suffix.lower().replace(".", ""),
        subject,
        file_size,
        len(pages),
        total_words,
        len(chunks),
        now
    ))
    material_id = cursor.lastrowid

    # Insert chunks
    for c in chunks:
        cursor.execute("""
            INSERT INTO document_chunks (
                material_id, chunk_index, page_number, heading, content, token_count, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            material_id, c["chunk_index"], c["page_number"], 
            c["heading"], c["content"], c["token_count"], now
        ))

    conn.commit()
    conn.close()

    # Rebuild Vector Index
    vector_store.build_index()

    # Log activity
    log_study_activity(1, "read", f"Uploaded course document: '{clean_name}'", 5)

    return {
        "success": True,
        "material_id": material_id,
        "filename": clean_name,
        "pages": len(pages),
        "chunks": len(chunks),
        "total_words": total_words
    }

@app.post("/api/materials/load-sample")
def load_sample_material():
    """Loads and indexes the bundled Renewable Energy Technologies course material."""
    pdf_path = SAMPLE_DIR / "renewable_energy_technologies.pdf"
    txt_path = SAMPLE_DIR / "renewable_energy_technologies.txt"
    
    target_path = pdf_path if pdf_path.exists() else txt_path
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Sample material file not found")

    filename = target_path.name
    # Check if already loaded
    conn = get_connection()
    existing = conn.execute("SELECT id FROM course_materials WHERE filename = ?", (filename,)).fetchone()
    if existing:
        conn.close()
        return {"success": True, "message": "Sample material already loaded", "material_id": existing["id"]}

    pages = extract_text_from_file(target_path)
    chunks = chunk_document(pages)
    total_words = sum(c["token_count"] for c in chunks)
    now = datetime.now().isoformat()

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO course_materials (
            filename, display_name, file_path, file_type, subject, 
            file_size, total_pages, total_words, chunk_count, uploaded_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        filename,
        "Renewable Energy Technologies: Solar PV, Wind & Storage",
        str(target_path),
        target_path.suffix.lower().replace(".", ""),
        "Clean Energy Engineering",
        target_path.stat().st_size,
        len(pages),
        total_words,
        len(chunks),
        now
    ))
    material_id = cursor.lastrowid

    for c in chunks:
        cursor.execute("""
            INSERT INTO document_chunks (
                material_id, chunk_index, page_number, heading, content, token_count, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            material_id, c["chunk_index"], c["page_number"], 
            c["heading"], c["content"], c["token_count"], now
        ))

    conn.commit()
    conn.close()

    # Rebuild Vector Index
    vector_store.build_index()

    return {
        "success": True,
        "message": "Sample course material loaded and indexed successfully!",
        "material_id": material_id,
        "chunks": len(chunks),
        "pages": len(pages)
    }

@app.delete("/api/materials/{material_id}")
def delete_material(material_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM course_materials WHERE id = ?", (material_id,))
    conn.commit()
    conn.close()
    vector_store.build_index()
    return {"success": True}

# ----------------- TUTOR & CHAT ENDPOINTS -----------------

@app.get("/api/tutor/conversations")
def get_conversations():
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM conversations WHERE student_id = 1 ORDER BY updated_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/tutor/conversations")
def create_conversation(req: NewConversationRequest):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO conversations (student_id, title, persona, created_at, updated_at)
        VALUES (1, ?, ?, ?, ?)
    """, (req.title, req.persona, now, now))
    conv_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": conv_id, "title": req.title, "persona": req.persona}

@app.get("/api/tutor/conversations/{conv_id}/messages")
def get_conversation_messages(conv_id: int):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM chat_messages WHERE conversation_id = ? ORDER BY id ASC
    """, (conv_id,)).fetchall()
    conn.close()
    
    result = []
    for r in rows:
        item = dict(r)
        if item.get("citations_json"):
            try:
                import json
                item["citations"] = json.loads(item["citations_json"])
            except Exception:
                item["citations"] = []
        else:
            item["citations"] = []
        result.append(item)
    return result

@app.post("/api/tutor/chat")
def chat_with_tutor(req: ChatRequest):
    # If no conversation_id, create a default one
    conv_id = req.conversation_id
    if not conv_id:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO conversations (student_id, title, persona, created_at, updated_at)
            VALUES (1, ?, ?, ?, ?)
        """, (req.query[:35] or "Study Chat", req.persona or "tutor", now, now))
        conv_id = cursor.lastrowid
        conn.commit()
        conn.close()

    result = generate_tutor_response(
        query=req.query,
        conversation_id=conv_id,
        student_id=1,
        persona=req.persona or "tutor",
        material_id=req.material_id
    )
    result["conversation_id"] = conv_id
    return result

# ----------------- QUIZ STUDIO ENDPOINTS -----------------

@app.post("/api/quiz/generate")
def create_quiz(req: QuizGenerateRequest):
    quiz = generate_quiz(
        topic=req.topic,
        material_id=req.material_id,
        difficulty=req.difficulty,
        question_count=req.question_count,
        student_id=1
    )
    return quiz

@app.post("/api/quiz/evaluate")
def grade_quiz(req: QuizEvaluateRequest):
    result = evaluate_quiz_submission(
        quiz_id=req.quiz_id,
        user_answers=req.answers,
        student_id=1
    )
    return result

@app.get("/api/quiz/history")
def get_quiz_history():
    conn = get_connection()
    rows = conn.execute("""
        SELECT a.id as attempt_id, a.quiz_id, a.score, a.total_questions, a.percentage, 
               a.completed_at, q.topic, q.difficulty
        FROM quiz_attempts a
        JOIN quizzes q ON a.quiz_id = q.id
        WHERE a.student_id = 1
        ORDER BY a.completed_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ----------------- LEARNING PLANNER ENDPOINTS -----------------

@app.post("/api/plans/generate")
def create_plan(req: PlanGenerateRequest):
    plan = generate_learning_plan(
        subject=req.subject,
        goal=req.goal,
        total_days=req.total_days,
        daily_hours=req.daily_hours,
        difficulty=req.difficulty,
        student_id=1
    )
    return plan

@app.get("/api/plans")
def list_plans():
    return get_active_plans(1)

@app.post("/api/plans/sessions/{session_id}/toggle")
def toggle_session(session_id: int):
    return toggle_session_status(session_id, 1)

# ----------------- STUDENT PROFILE & MEMORY -----------------

@app.get("/api/student/profile")
def fetch_profile():
    return get_profile(1)

@app.put("/api/student/profile")
def modify_profile(req: ProfileUpdateRequest):
    return update_profile(1, req.model_dump(exclude_unset=True))

@app.get("/api/student/memory")
def fetch_memory():
    facts = get_memory_facts(1)
    weak = get_weak_topics(1)
    return {
        "facts": facts,
        "weak_topics": weak
    }

# ----------------- PROGRESS & ANALYTICS -----------------

@app.get("/api/analytics")
def fetch_analytics():
    return get_learning_analytics(1)

# ----------------- FLASHCARD STUDIO ENDPOINTS -----------------

@app.post("/api/flashcards/generate")
def create_flashcard_deck(req: FlashcardGenerateRequest):
    return generate_flashcard_deck(
        topic=req.topic,
        material_id=req.material_id,
        count=req.count,
        student_id=1
    )

@app.get("/api/flashcards/decks")
def list_flashcard_decks():
    return get_flashcard_decks(1)

@app.get("/api/flashcards/decks/{deck_id}")
def get_deck_cards_endpoint(deck_id: int):
    return get_deck_cards(deck_id)

@app.post("/api/flashcards/cards/{card_id}/review")
def review_flashcard_endpoint(card_id: int, req: FlashcardReviewRequest):
    return review_flashcard(card_id, req.rating, 1)

# ----------------- AI STUDY TOOLS ENDPOINTS -----------------

@app.post("/api/tools/cheatsheet")
def get_cheatsheet(req: CheatsheetRequest):
    return generate_formula_cheatsheet(req.topic, req.material_id)

@app.post("/api/study/log-timer")
def log_study_timer(req: StudyTimerLogRequest):
    log_study_activity(1, "timer", req.description, req.duration_minutes)
    return {"success": True, "message": f"Logged {req.duration_minutes} minutes of study session"}

# ----------------- DOCUMENT CHUNKS INSPECTOR ENDPOINTS -----------------

@app.get("/api/materials/{material_id}/chunks")
def get_material_chunks(material_id: int):
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, chunk_index, page_number, heading, content, token_count
        FROM document_chunks
        WHERE material_id = ?
        ORDER BY chunk_index ASC
    """, (material_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/materials/explore-search")
def explore_semantic_search(req: SemanticSearchRequest):
    results = vector_store.search(
        query=req.query,
        top_k=req.top_k,
        material_id=req.material_id,
        min_score=0.01
    )
    return {"query": req.query, "results": results, "total_matches": len(results)}

# ----------------- SETTINGS ENDPOINTS -----------------

@app.get("/api/settings")
def fetch_settings():
    return get_all_settings()

@app.post("/api/settings")
def modify_settings(req: SettingsUpdateRequest):
    for k, v in req.settings.items():
        set_setting(k, v)
    return {"success": True, "settings": get_all_settings()}

# ----------------- FRONTEND STATIC SERVING -----------------

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
def serve_index():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse({"message": "AI Learning and Study Assistant API is live"})
