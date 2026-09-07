import re
import json
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.database import get_connection, get_setting
from backend.rag import vector_store
from backend.memory import (
    get_profile, 
    get_memory_facts, 
    get_weak_topics, 
    get_recent_chat_history,
    log_study_activity
)

def build_prompt_context(retrieved_chunks: List[Dict[str, Any]]) -> str:
    """Builds a formatted context string from retrieved chunks."""
    if not retrieved_chunks:
        return "No specific course materials found for this query."
    
    context_lines = []
    for i, c in enumerate(retrieved_chunks):
        source_tag = f"[Source {i+1}: {c.get('display_name') or c.get('filename')} (Page {c.get('page_number', 1)}) - Section: {c.get('heading', 'General')}]"
        context_lines.append(f"{source_tag}\n{c.get('content', '').strip()}\n")
    return "\n---\n".join(context_lines)

def generate_tutor_response(
    query: str,
    conversation_id: int,
    student_id: int = 1,
    persona: str = "tutor",
    material_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Coordinates RAG retrieval, student memory augmentation, and tutor response generation.
    Supports Gemini API, OpenAI-compatible API, and Built-in pedagogical tutor.
    """
    # 1. RAG Retrieval
    chunks = vector_store.search(query, top_k=4, material_id=material_id)
    
    # 2. Gather Student Context & Memory
    profile = get_profile(student_id)
    weak_topics = get_weak_topics(student_id)
    history = get_recent_chat_history(conversation_id, limit=4)
    
    # Build weak topic hints if relevant
    weak_hint = ""
    if weak_topics:
        matching_weaks = [w for w in weak_topics if any(k in query.lower() for k in w["topic"].lower().split())]
        if matching_weaks:
            weak_hint = f"Note: You previously encountered difficulty with {matching_weaks[0]['topic']} (Score: {matching_weaks[0]['average_score']}%). I will provide extra detail on this concept."

    # 3. Check configured provider
    provider = get_setting("llm_provider", "builtin")
    gemini_key = get_setting("gemini_api_key", "")
    openai_key = get_setting("openai_api_key", "")
    openai_base = get_setting("openai_base_url", "https://api.openai.com/v1")
    model_name = get_setting("model_name", "gemini-1.5-flash")

    answer_text = ""
    follow_ups = []
    
    # Try External LLM if configured and key present
    if provider == "gemini" and gemini_key:
        answer_text = call_gemini_api(query, chunks, profile, weak_topics, history, persona, gemini_key, model_name)
    elif provider == "openai" and openai_key:
        answer_text = call_openai_api(query, chunks, profile, weak_topics, history, persona, openai_key, openai_base, model_name)

    # Fallback to Built-in Pedagogical Tutor Engine if external call failed or not configured
    if not answer_text:
        answer_text, follow_ups = synthesize_builtin_tutor_response(
            query, chunks, profile, weak_hint, persona
        )

    # If follow-ups not generated yet, provide contextual follow-ups
    if not follow_ups:
        follow_ups = generate_default_followups(query, chunks)

    # Format citations
    citations = []
    for c in chunks:
        citations.append({
            "chunk_id": c.get("chunk_id"),
            "material_id": c.get("material_id"),
            "filename": c.get("filename"),
            "display_name": c.get("display_name"),
            "page_number": c.get("page_number", 1),
            "heading": c.get("heading", ""),
            "score": c.get("similarity_score", 0.0),
            "snippet": c.get("content", "")[:180] + "..."
        })

    # Save to database
    conn = get_connection()
    now = datetime.now().isoformat()
    # Save user message
    conn.execute("""
        INSERT INTO chat_messages (conversation_id, sender, content, citations_json, created_at)
        VALUES (?, 'user', ?, NULL, ?)
    """, (conversation_id, query, now))
    # Save assistant message
    conn.execute("""
        INSERT INTO chat_messages (conversation_id, sender, content, citations_json, created_at)
        VALUES (?, 'assistant', ?, ?, ?)
    """, (conversation_id, answer_text, json.dumps(citations), now))
    # Update conversation updated_at
    conn.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id))
    conn.commit()
    conn.close()

    # Log study activity
    log_study_activity(student_id, "chat", f"Asked tutor: '{query[:50]}...'", 10)

    return {
        "answer": answer_text,
        "citations": citations,
        "follow_ups": follow_ups,
        "persona": persona,
        "has_rag_context": len(chunks) > 0
    }

def synthesize_builtin_tutor_response(
    query: str,
    chunks: List[Dict[str, Any]],
    profile: Dict[str, Any],
    weak_hint: str,
    persona: str
) -> tuple[str, List[str]]:
    """
    Intelligent built-in pedagogical tutor that synthesizes detailed, accurate,
    document-grounded responses formatted for the student's chosen learning persona.
    """
    if not chunks:
        response = (
            f"Hello {profile.get('name', 'Student')}! I searched through your uploaded course materials, "
            f"but couldn't find a direct match for: **\"{query}\"**.\n\n"
            "💡 **Helpful Tip**: Try uploading relevant course notes or slides in the **Course Materials** tab, "
            "or rephrase your question using key terms from your syllabus."
        )
        follow_ups = [
            "What course materials are currently uploaded?",
            "How do I upload a PDF lecture note?",
            "Explain the basics of Renewable Energy Technologies"
        ]
        return response, follow_ups

    # Combine chunk contents
    combined_info = " ".join([c["content"] for c in chunks])
    main_heading = chunks[0].get("heading", "Course Material")
    primary_page = chunks[0].get("page_number", 1)
    primary_doc = chunks[0].get("display_name") or chunks[0].get("filename", "Uploaded Material")

    # Persona styling
    greeting = f"Hello {profile.get('name', 'there')}! " if profile.get('name') else ""
    sections = []

    if weak_hint:
        sections.append(f"> 🎯 **Memory Recall**: {weak_hint}\n")

    if persona == "socratic":
        sections.append(f"### 🤔 Socratic Inquiry: {main_heading}\n")
        sections.append(f"To understand **\"{query}\"**, let's first consider the core mechanism described in *{primary_doc}* (Page {primary_page}):\n")
        
        # Extract core sentences
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', combined_info) if len(s.strip()) > 30]
        core_concept = " ".join(sentences[:3]) if sentences else combined_info[:300]
        sections.append(f"**Key Premise:**\n{core_concept}\n")
        
        sections.append("\n**Guided Reflection Questions:**")
        sections.append("1. How does the physics or mechanism in this process directly dictate the efficiency of the whole system?")
        sections.append("2. What happens to the power output when operating conditions (like temperature or load) deviate from standard ratings?")
        sections.append(f"\n*Take a moment to reason through this. When you're ready, tell me what you think happens!*")

    elif persona == "explainer":
        sections.append(f"### 💡 Simple Conceptual Breakdown: {main_heading}\n")
        sections.append(f"Let's break down **\"{query}\"** into simple, everyday terms based on your course notes:\n")
        
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', combined_info) if len(s.strip()) > 25]
        
        # Key idea
        if len(sentences) >= 2:
            sections.append(f"**The Core Idea:**\n{sentences[0]} {sentences[1]}\n")
        
        # Step-by-step
        sections.append("**How It Works Step-by-Step:**")
        step_sentences = sentences[2:7] if len(sentences) > 4 else sentences[1:5]
        for idx, s in enumerate(step_sentences, 1):
            sections.append(f"{idx}. **Step {idx}**: {s}")
            
        sections.append(f"\n*(Source: {primary_doc}, Page {primary_page})*")

    elif persona == "exam":
        sections.append(f"### 📝 High-Yield Exam Review: {main_heading}\n")
        sections.append(f"**Target Concept**: *{query}*\n")
        
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', combined_info) if len(s.strip()) > 25]
        
        sections.append("#### 📌 Key Definitions & Mechanics")
        for s in sentences[:3]:
            sections.append(f"- {s}")
            
        sections.append("\n#### ⚡ Critical Exam Points & Formulas")
        # Check for formulas or numbers
        formulas = re.findall(r'[A-Za-z0-9_]+\s*=\s*[^.\n]+', combined_info)
        if formulas:
            for f in formulas[:3]:
                sections.append(f"- **Key Equation**: `${f.strip()}$`")
        else:
            sections.append("- Pay special attention to conversion efficiency, operating parameters, and Balance of System interfaces.")
            
        sections.append("\n#### ⚠️ Common Student Pitfalls")
        sections.append(f"- Confusing series connection (which scales voltage) with parallel connection (which scales current).")
        sections.append(f"- Neglecting temperature derating coefficients and inverter conversion losses.")
        sections.append(f"\n*(Reference: {primary_doc}, Page {primary_page})*")

    else: # default 'tutor'
        sections.append(f"### 🎓 Concept Explanation: {main_heading}\n")
        sections.append(f"Based on your course material (**{primary_doc}**, Page {primary_page}):\n")
        
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', combined_info) if len(s.strip()) > 25]
        
        # Overview
        intro_text = " ".join(sentences[:2]) if len(sentences) >= 2 else combined_info[:250]
        sections.append(f"{intro_text}\n")
        
        # Key Components / Principles
        sections.append("#### Key Principles & Subsystems:")
        body_sentences = sentences[2:6] if len(sentences) >= 6 else sentences[1:4]
        for idx, s in enumerate(body_sentences, 1):
            sections.append(f"- **Point {idx}**: {s}")
            
        # Summary & Conclusion
        if len(sentences) > 6:
            sections.append(f"\n**Summary:**\n{sentences[6]}")
            
        sections.append(f"\n*(Cited from: {primary_doc}, Page {primary_page} - Section: {chunks[0].get('heading')})*")

    response_text = "\n".join(sections)
    follow_ups = generate_default_followups(query, chunks)
    return response_text, follow_ups

def generate_default_followups(query: str, chunks: List[Dict[str, Any]]) -> List[str]:
    """Generates dynamic follow-up prompt pills based on query context."""
    q_lower = query.lower()
    if "solar" in q_lower or "photovoltaic" in q_lower or "pv" in q_lower:
        return [
            "Give me a 5-question quiz from this topic",
            "What is the difference between PWM and MPPT charge controllers?",
            "How does an inverter synchronize with the utility AC grid?",
            "Create a 7-day study plan for Solar PV Systems"
        ]
    elif "wind" in q_lower or "betz" in q_lower or "turbine" in q_lower:
        return [
            "Explain the Betz Limit and why theoretical efficiency is 59.3%",
            "What is the difference between DFIG and PMSG generators?",
            "Give me a quiz on Wind Energy Systems"
        ]
    elif "battery" in q_lower or "storage" in q_lower:
        return [
            "Compare Lead-Acid vs Lithium-Iron-Phosphate (LiFePO4) batteries",
            "What is Depth of Discharge (DoD) and why does it matter?",
            "Test my understanding with a short quiz on Energy Storage"
        ]
    else:
        return [
            "Can you explain this with a practical real-world example?",
            "Generate a quick practice quiz on this section",
            "Summarize the key exam formulas for this topic",
            "Add this topic to my active study plan"
        ]

def call_gemini_api(query, chunks, profile, weak_topics, history, persona, api_key, model_name) -> str:
    """Calls the official Google Gemini REST API."""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        rag_context = build_prompt_context(chunks)
        
        system_instruction = (
            f"You are an expert virtual tutor helping student {profile.get('name')}. "
            f"Academic Level: {profile.get('academic_level')}. "
            f"Persona: {persona}. "
            f"Student's Target Goal: {profile.get('target_goal')}. "
            f"Always ground your response in the provided Course Material Chunks. "
            f"Cite specific source documents and page numbers explicitly. "
            f"Use clean Markdown formatting, bullet points, and LaTeX formulas for math."
        )

        history_text = "\n".join([f"{h['sender'].capitalize()}: {h['content']}" for h in history])

        prompt_payload = f"""
{system_instruction}

--- RELEVANT COURSE MATERIAL CHUNKS ---
{rag_context}

--- CONVERSATION HISTORY ---
{history_text}

--- STUDENT QUESTION ---
{query}
"""
        payload = {
            "contents": [{"parts": [{"text": prompt_payload}]}],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 1024
            }
        }
        res = requests.post(url, json=payload, timeout=20)
        if res.status_code == 200:
            data = res.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"Gemini API error: {e}")
    return ""

def call_openai_api(query, chunks, profile, weak_topics, history, persona, api_key, base_url, model_name) -> str:
    """Calls OpenAI or OpenAI-compatible endpoint."""
    try:
        url = f"{base_url.rstrip('/')}/chat/completions"
        rag_context = build_prompt_context(chunks)
        
        system_msg = {
            "role": "system",
            "content": (
                f"You are an expert virtual tutor for {profile.get('name')}. "
                f"Persona: {persona}. Level: {profile.get('academic_level')}. "
                f"Ground answers directly in the provided course materials with citations."
            )
        }
        
        messages = [system_msg]
        for h in history:
            role = "assistant" if h["sender"] == "assistant" else "user"
            messages.append({"role": role, "content": h["content"]})
            
        messages.append({
            "role": "user",
            "content": f"Context:\n{rag_context}\n\nQuestion:\n{query}"
        })
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_name or "gpt-4o-mini",
            "messages": messages,
            "temperature": 0.4
        }
        res = requests.post(url, json=payload, headers=headers, timeout=20)
        if res.status_code == 200:
            data = res.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"OpenAI API error: {e}")
    return ""
