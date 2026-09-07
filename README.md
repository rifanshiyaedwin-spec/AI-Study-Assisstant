# 🎓 AI Learning and Study Assistant

> **An intelligent personal virtual tutor powered by RAG (Retrieval-Augmented Generation), Student Memory, AI Tools, and Progress Analytics.**

---

## 🌟 Project Overview

The **AI Learning and Study Assistant** acts as an adaptive personal virtual tutor for students. Students can upload course materials (such as textbooks, lecture notes, syllabus guides, and PDF documents). The system processes and indexes these materials, providing grounded answers with source citations, automatically generating personalized study plans, synthesizing interactive quizzes, tracking topic mastery, and pinpointing weak areas for revision.

### ⭐ Project USP
Rather than functioning as a generic chatbot, this assistant combines **four foundational pillars**:
1. **RAG (Retrieval-Augmented Generation)**: Answers are strictly grounded in the student's actual course materials with page-level citations and similarity scores.
2. **Student & Conversational Memory**: Retains the student's academic goals, learning preferences, past quiz scores, and flagged misconceptions.
3. **AI Study Tools**: Features an automated Quiz Generator & Auto-Evaluator, plus a dynamic Study Plan Scheduler.
4. **Adaptive LLM Tutor**: Supports multiple pedagogical personas (*Socratic Tutor*, *Concept Explainer / ELI5*, *Exam Prep Master*, and *Concept Synthesizer*).

---

## 🏗️ Architecture & Technology Stack

```
AI Learning and Study Assistant
├── Frontend (Modern Responsive Single-Page Application)
│   ├── UI: HTML5, CSS3 (Glassmorphism, Dark/Light Themes, Mobile-Responsive)
│   ├── Libraries: Marked.js (Markdown), KaTeX (Math Equations), Lucide Icons
│   └── Modules: App State, Chat & RAG, Course Materials, Quiz Studio, Planner, Analytics
│
├── Backend (FastAPI + Python 3.14)
│   ├── Document Processing: PyPDF (Page-by-page extraction, semantic chunking)
│   ├── Vector Store & RAG: TF-IDF + Cosine Similarity hybrid retrieval with keyword boosting
│   ├── Student Memory: Profile store, conversational history, weak-area detection
│   ├── AI Quiz Engine: Multi-format question generator, answer grader, explanation generator
│   ├── Study Planner: Dynamic curriculum scheduler & interactive daily checklist
│   └── Analytics Engine: Mastery calculator, streak tracker, revision recommender
│
└── Storage Layer
    ├── SQLite: Relational schema for profiles, materials, chunks, quizzes, plans, and logs
    └── Uploads: Local storage for course PDFs, notes, and bundled samples
```

---

## 🚀 Key Modules

### 1. 👤 Student Profile & Memory
- Tracks academic level (*Undergraduate, Postgraduate, High School, Self-Learner*), target goals, and weekly study hour targets.
- Maintains long-term memory facts (*preferred learning style, strong topics, weak areas, misconceptions*).
- Integrates memory recall into tutor interactions (e.g., *"I noticed you previously struggled with charge controllers..."*).

### 2. 📚 Course Material Management
- Drag-and-drop file uploader supporting `.pdf`, `.txt`, and `.md` files.
- Smart document chunker preserving page numbers, token counts, and section headings.
- One-click **"Load Sample: Renewable Energy Technologies"** button providing instant zero-configuration testing.

### 3. 💬 RAG-Based Question Answering & Chatbot
- Semantic retrieval across uploaded materials.
- Transparent source citations displaying the document name, page number, confidence percentage, and snippet.
- 4 Pedagogical Personas:
  - **🎓 Tutor**: Clear, structured conceptual breakdown.
  - **🤔 Socratic**: Guides students through inquiry and thought experiments.
  - **💡 Simple (ELI5)**: Analogy-driven explanations for beginners.
  - **📝 Exam Prep**: Rigorous definitions, critical formulas ($P = V \times I$, Betz Limit $C_{p,max} = 0.593$), and pitfalls.
- Dynamic follow-up suggestion pills.

### 4. 📅 AI Learning Plan Generator
- Generates structured day-by-day study roadmaps based on duration (*5, 7, 14 days*), available daily hours, and subject goals.
- Interactive checklist to track completed study sessions.
- Real-time progress bar recalculation.

### 5. 📝 AI Quiz Studio & Auto-Evaluator
- Generates custom quizzes from uploaded materials or specific topics.
- Question formats: Multiple Choice (MCQs), True/False, and Conceptual questions.
- Configurable difficulty (*Beginner, Intermediate, Advanced*).
- Instant scoring with in-depth explanations for every answer and source citations.
- Automatically flags missed concepts into the student's memory facts.

### 6. 📊 Progress Tracking & Revision Recommender
- Dashboard metrics: Study Hours Logged, Quizzes Taken, Average Score %, Study Streak.
- Topic Mastery breakdown with progress meters (*Mastered, In Progress, Needs Revision*).
- Weak Areas Engine with actionable revision tips (e.g., *"You scored 6/10 in Solar PV Systems. You may want to revise PV modules, charge controllers, and inverters."*).

---

## ⚙️ Quick Start Guide

### Prerequisites
- Python 3.10+ (Python 3.14 supported)
- Windows / macOS / Linux

### Installation

1. Navigate to the project directory:
   ```bash
   cd "c:\Users\GCE\Desktop\New folder\Rifanshiya J S"
   ```

2. Install dependencies:
   ```bash
   py -m pip install -r requirements.txt
   ```

3. Launch the application:
   ```bash
   py run.py
   ```

4. Open your web browser and navigate to:
   ```
   http://127.0.0.1:8000
   ```

---

## 🧪 Running Automated Tests

A comprehensive unit and integration test suite covers all backend services, RAG retrieval, quiz evaluation, planner, and REST endpoints:

```bash
py -m unittest tests/test_backend.py
```

---

## 🔌 API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the web dashboard |
| `GET` | `/api/materials` | Lists all indexed course materials |
| `POST` | `/api/materials/upload` | Uploads and chunks a new course document |
| `POST` | `/api/materials/load-sample` | Loads bundled Renewable Energy material |
| `DELETE`| `/api/materials/{id}` | Deletes material and updates vector index |
| `POST` | `/api/tutor/chat` | Grounded RAG question answering |
| `GET` | `/api/tutor/conversations` | Retrieves chat conversation history |
| `POST` | `/api/quiz/generate` | Generates quiz questions on chosen topic |
| `POST` | `/api/quiz/evaluate` | Grades quiz, updates memory & weak areas |
| `GET` | `/api/quiz/history` | Retrieves past quiz attempts |
| `POST` | `/api/plans/generate` | Generates multi-day study schedule |
| `POST` | `/api/plans/sessions/{id}/toggle` | Toggles study session completion |
| `POST` | `/api/flashcards/generate` | Synthesizes flashcard deck from materials |
| `GET` | `/api/flashcards/decks` | Lists flashcard decks with mastery stats |
| `GET` | `/api/flashcards/decks/{id}` | Retrieves deck cards for active review |
| `POST` | `/api/flashcards/cards/{id}/review` | Updates spaced repetition mastery rating |
| `POST` | `/api/tools/cheatsheet` | Generates high-yield formula & concept cheatsheet |
| `POST` | `/api/study/log-timer` | Logs completed Pomodoro focus study minutes |
| `GET` | `/api/materials/{id}/chunks` | Retrieves indexed document chunks and metadata |
| `POST` | `/api/materials/explore-search` | Interactive semantic search against chunks |
| `GET` | `/api/analytics` | Returns metrics, mastery levels, & recommendations |
| `GET` | `/api/student/profile` | Fetches student profile and goals |
| `PUT` | `/api/student/profile` | Updates student profile preferences |
| `GET` | `/api/settings` | Gets AI provider & model settings |
| `POST` | `/api/settings` | Updates AI configuration (Gemini / OpenAI keys) |
