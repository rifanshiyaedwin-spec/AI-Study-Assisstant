import unittest
import json
from pathlib import Path
from fastapi.testclient import TestClient

from backend.config import SAMPLE_DIR, DB_PATH
from backend.database import init_db, get_connection
from backend.document_processor import extract_text_from_file, chunk_document
from backend.rag import vector_store
from backend.memory import (
    get_profile, update_profile, add_memory_fact, 
    get_memory_facts, get_weak_topics, log_study_activity
)
from backend.tutor import generate_tutor_response
from backend.quiz import generate_quiz, evaluate_quiz_submission
from backend.planner import generate_learning_plan, toggle_session_status, get_active_plans
from backend.analytics import get_learning_analytics
from backend.app import app, load_sample_material

class TestAILearningAssistant(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        load_sample_material()
        cls.client = TestClient(app)

    def test_01_document_processing_and_chunking(self):
        pdf_path = SAMPLE_DIR / "renewable_energy_technologies.pdf"
        self.assertTrue(pdf_path.exists(), "Sample PDF must exist")
        
        pages = extract_text_from_file(pdf_path)
        self.assertGreaterEqual(len(pages), 1, "Should extract at least 1 page")
        
        chunks = chunk_document(pages, chunk_size=400, chunk_overlap=80)
        self.assertGreater(len(chunks), 0, "Should generate chunks")
        self.assertIn("content", chunks[0])
        self.assertIn("page_number", chunks[0])
        self.assertIn("heading", chunks[0])

    def test_02_vector_store_and_rag_retrieval(self):
        # Search for solar PV
        results = vector_store.search("solar photovoltaic cell semiconductor p-n junction", top_k=3)
        self.assertGreater(len(results), 0, "RAG search must return matching chunks")
        
        top_result = results[0]
        self.assertIn("similarity_score", top_result)
        self.assertGreater(top_result["similarity_score"], 0.0)
        self.assertTrue(
            "solar" in top_result["content"].lower() or "photovoltaic" in top_result["content"].lower() or "silicon" in top_result["content"].lower(),
            "Retrieved chunk should contain relevant terms"
        )

    def test_03_student_profile_and_memory(self):
        profile = get_profile(1)
        self.assertIsNotNone(profile)
        self.assertIn("name", profile)

        # Update profile
        updated = update_profile(1, {"name": "Alex Chen", "study_hours_per_week": 14})
        self.assertEqual(updated["study_hours_per_week"], 14)

        # Add memory fact
        add_memory_fact(1, "weak_topic", "Charge Controllers", "Needs revision on PWM vs MPPT efficiency gains", 0.9)
        facts = get_memory_facts(1, "weak_topic")
        self.assertTrue(any(f["topic"] == "Charge Controllers" for f in facts))

        # Check weak topics detection
        weak_topics = get_weak_topics(1)
        self.assertTrue(any("charge" in w["topic"].lower() for w in weak_topics))

    def test_04_tutor_response_generation(self):
        conv_res = self.client.post("/api/tutor/conversations", json={
            "title": "Unit Test Session",
            "persona": "tutor"
        })
        conv_id = conv_res.json()["id"]

        response = generate_tutor_response(
            query="Explain the working of a solar photovoltaic system.",
            conversation_id=conv_id,
            student_id=1,
            persona="tutor"
        )
        self.assertIn("answer", response)
        self.assertGreater(len(response["answer"]), 50)
        self.assertIn("citations", response)
        self.assertGreater(len(response["citations"]), 0)
        self.assertIn("follow_ups", response)

    def test_05_quiz_generation_and_evaluation(self):
        # Generate Quiz
        quiz = generate_quiz(
            topic="Solar Photovoltaic Systems",
            difficulty="intermediate",
            question_count=3,
            student_id=1
        )
        self.assertIn("quiz_id", quiz)
        self.assertEqual(len(quiz["questions"]), 3)

        # Evaluate Quiz
        user_answers = {}
        # Provide correct answers
        for q in quiz["questions"]:
            user_answers[str(q["id"])] = q["options"][0]

        eval_result = evaluate_quiz_submission(
            quiz_id=quiz["quiz_id"],
            user_answers=user_answers,
            student_id=1
        )
        self.assertIn("score", eval_result)
        self.assertIn("feedback", eval_result)
        self.assertEqual(eval_result["total_questions"], 3)
        self.assertIn("evaluations", eval_result)

    def test_06_learning_plan_generator(self):
        plan = generate_learning_plan(
            subject="Renewable Energy Technologies",
            goal="Ace Final Exam with 90%+",
            total_days=5,
            daily_hours=1.5,
            student_id=1
        )
        self.assertEqual(plan["total_days"], 5)
        self.assertEqual(len(plan["sessions"]), 5)

        # Toggle session
        first_session = plan["sessions"][0]
        toggle_res = toggle_session_status(first_session["id"], 1)
        self.assertTrue(toggle_res["is_completed"])
        self.assertGreater(toggle_res["progress_percentage"], 0.0)

        # Get active plans
        plans = get_active_plans(1)
        self.assertGreater(len(plans), 0)

    def test_07_learning_analytics(self):
        analytics = get_learning_analytics(1)
        self.assertIn("overview", analytics)
        self.assertIn("mastery", analytics)
        self.assertIn("weak_areas", analytics)
        self.assertIn("recommendations", analytics)
        self.assertGreaterEqual(analytics["overview"]["total_study_hours"], 0.0)

    def test_08_api_endpoints(self):
        # Materials endpoint
        res = self.client.get("/api/materials")
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json(), list)

        # Profile endpoint
        res = self.client.get("/api/student/profile")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["name"], "Alex Chen")

        # Chat endpoint
        res = self.client.post("/api/tutor/chat", json={
            "query": "What is the difference between PWM and MPPT charge controllers?",
            "persona": "tutor"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("answer", data)
        self.assertIn("citations", data)

        # Analytics endpoint
        res = self.client.get("/api/analytics")
        self.assertEqual(res.status_code, 200)
        self.assertIn("overview", res.json())

    def test_09_flashcard_deck_and_review(self):
        # Generate Deck
        res = self.client.post("/api/flashcards/generate", json={
            "topic": "Solar Photovoltaic Systems",
            "count": 4
        })
        self.assertEqual(res.status_code, 200)
        deck_data = res.json()
        self.assertIn("deck_id", deck_data)
        self.assertGreaterEqual(deck_data["card_count"], 1)

        deck_id = deck_data["deck_id"]
        cards = deck_data["cards"]
        first_card_id = cards[0]["id"]

        # Review Card (Good)
        rev_res = self.client.post(f"/api/flashcards/cards/{first_card_id}/review", json={
            "rating": "good"
        })
        self.assertEqual(rev_res.status_code, 200)
        self.assertGreaterEqual(rev_res.json()["mastery_level"], 1)

        # List Decks
        list_res = self.client.get("/api/flashcards/decks")
        self.assertEqual(list_res.status_code, 200)
        self.assertGreater(len(list_res.json()), 0)

    def test_10_cheatsheet_generator(self):
        res = self.client.post("/api/tools/cheatsheet", json={
            "topic": "Renewable Energy Technologies"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("content", data)
        self.assertIn("Betz", data["content"])
        self.assertIn("P = V", data["content"])

    def test_11_study_timer_log(self):
        res = self.client.post("/api/study/log-timer", json={
            "duration_minutes": 25,
            "description": "Completed Unit Test Pomodoro Block"
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])

    def test_12_chunks_inspector_endpoint(self):
        # Get materials
        mat_res = self.client.get("/api/materials")
        self.assertEqual(mat_res.status_code, 200)
        materials = mat_res.json()
        self.assertGreater(len(materials), 0)

        first_mat_id = materials[0]["id"]
        chunks_res = self.client.get(f"/api/materials/{first_mat_id}/chunks")
        self.assertEqual(chunks_res.status_code, 200)
        chunks = chunks_res.json()
        self.assertGreater(len(chunks), 0)
        self.assertIn("heading", chunks[0])
        self.assertIn("content", chunks[0])

        # Test semantic search explorer
        search_res = self.client.post("/api/materials/explore-search", json={
            "query": "photovoltaic inverter",
            "top_k": 3
        })
        self.assertEqual(search_res.status_code, 200)
        self.assertGreater(search_res.json()["total_matches"], 0)

if __name__ == "__main__":
    unittest.main()
