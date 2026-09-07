import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from backend.database import get_connection
from backend.rag import vector_store
from backend.memory import log_study_activity

DEFAULT_FLASHCARDS_DATA = [
    {
        "topic": "Solar Photovoltaic Systems",
        "front": "What physical phenomenon occurs at a p-n junction when illuminated by photons?",
        "back": "The Photovoltaic Effect: incident photons with energy greater than the silicon bandgap (~1.12 eV) liberate electron-hole pairs. The built-in electrostatic field sweeps electrons to the n-side and holes to the p-side, producing DC voltage and current.",
        "page": 1
    },
    {
        "topic": "Solar Photovoltaic Systems",
        "front": "What are Standard Test Conditions (STC) for rating solar modules?",
        "back": "1. Irradiance: 1000 W/m²\n2. Cell Temperature: 25°C\n3. Air Mass Spectrum: AM 1.5",
        "page": 1
    },
    {
        "topic": "Solar Charge Controllers",
        "front": "Why is an MPPT charge controller significantly more efficient than a PWM controller?",
        "back": "PWM forces panel voltage down to match the battery bank's lower voltage, throwing away power. MPPT acts as a switch-mode DC-to-DC converter, converting excess voltage into additional charging current (20-35% harvest boost).",
        "page": 2
    },
    {
        "topic": "Solar Power Inverters",
        "front": "What is Anti-Islanding protection in grid-tied solar systems (IEEE 1547 / UL 1741)?",
        "back": "A safety requirement where the grid-tied inverter must immediately disconnect and shut down within milliseconds when utility grid power fails, preventing dangerous back-energization of power lines undergoing worker repair.",
        "page": 2
    },
    {
        "topic": "Battery Storage Technologies",
        "front": "How do Lead-Acid and Lithium-Iron-Phosphate (LiFePO4) compare in Depth of Discharge (DoD) and cycle life?",
        "back": "Lead-Acid: Recommended DoD is only ~50% with 500-1200 cycles.\nLiFePO4: Deep discharge up to 80-90% DoD with 4000-7000 cycles, plus higher thermal stability.",
        "page": 2
    },
    {
        "topic": "Wind Energy Systems",
        "front": "State the Betz Law and its theoretical maximum power coefficient.",
        "back": "Albert Betz (1919) proved that no wind turbine rotor can extract more than 16/27 (59.3%) of the kinetic energy from an air stream without completely stalling wind flow. Modern practical turbines achieve Cp between 0.40 and 0.48.",
        "page": 3
    },
    {
        "topic": "Wind Energy Systems",
        "front": "How does available kinetic wind power scale with wind velocity?",
        "back": "Power scales with the CUBE of wind speed (P ∝ v³). Doubling the wind velocity results in an 8-fold (2³ = 8) increase in theoretical power generation.",
        "page": 3
    },
    {
        "topic": "Solar System Sizing",
        "front": "Define a Peak Sun Hour (PSH).",
        "back": "One Peak Sun Hour represents the equivalent duration of solar irradiance at 1000 W/m² (totaling 1 kWh/m² of solar energy). For example, 5.5 kWh/m²/day equals 5.5 PSH.",
        "page": 3
    }
]

def generate_flashcard_deck(
    topic: str = "Solar Photovoltaic Systems",
    material_id: Optional[int] = None,
    count: int = 5,
    student_id: int = 1
) -> Dict[str, Any]:
    """Generates an active-recall flashcard deck grounded in course materials."""
    chunks = vector_store.search(topic, top_k=4, material_id=material_id)

    # Filter matching cards from bank
    topic_words = [w.lower() for w in topic.split() if len(w) > 2]
    matching = []
    others = []
    for c in DEFAULT_FLASHCARDS_DATA:
        text = (c["topic"] + " " + c["front"] + " " + c["back"]).lower()
        if any(w in text for w in topic_words):
            matching.append(c)
        else:
            others.append(c)

    selected = matching + others
    selected = selected[:count]

    # Synthesize additional cards from chunks if needed
    if len(selected) < count and chunks:
        for idx, ch in enumerate(chunks):
            if len(selected) >= count:
                break
            heading = ch.get("heading") or "Key Concept"
            snippet = ch.get("content", "")[:180]
            selected.append({
                "topic": topic,
                "front": f"What is the key principle of '{heading}' in this course unit?",
                "back": f"{snippet}... (Referenced on Page {ch.get('page_number', 1)})",
                "page": ch.get("page_number", 1)
            })

    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    deck_title = f"{topic} Mastery Deck"

    cursor.execute("""
        INSERT INTO flashcard_decks (student_id, material_id, title, topic, card_count, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (student_id, material_id, deck_title, topic, len(selected), now))
    deck_id = cursor.lastrowid

    cards_out = []
    for c in selected:
        cursor.execute("""
            INSERT INTO flashcards (
                deck_id, front_prompt, back_answer, source_page, 
                mastery_level, review_count, next_review_at, created_at
            ) VALUES (?, ?, ?, ?, 0, 0, ?, ?)
        """, (deck_id, c["front"], c["back"], c.get("page", 1), now, now))
        card_id = cursor.lastrowid
        cards_out.append({
            "id": card_id,
            "deck_id": deck_id,
            "front": c["front"],
            "back": c["back"],
            "source_page": c.get("page", 1),
            "mastery_level": 0,
            "review_count": 0
        })

    conn.commit()
    conn.close()

    log_study_activity(student_id, "flashcard", f"Generated Flashcard Deck: '{deck_title}' ({len(selected)} cards)", 10)

    return {
        "deck_id": deck_id,
        "title": deck_title,
        "topic": topic,
        "card_count": len(cards_out),
        "cards": cards_out,
        "created_at": now
    }

def get_flashcard_decks(student_id: int = 1) -> List[Dict[str, Any]]:
    """Retrieves all flashcard decks and card counts for a student."""
    conn = get_connection()
    cursor = conn.cursor()
    decks = cursor.execute("""
        SELECT * FROM flashcard_decks WHERE student_id = ? ORDER BY created_at DESC
    """, (student_id,)).fetchall()

    result = []
    for d in decks:
        deck_id = d["id"]
        stats = cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN mastery_level >= 3 THEN 1 ELSE 0 END) as mastered,
                SUM(CASE WHEN mastery_level BETWEEN 1 AND 2 THEN 1 ELSE 0 END) as learning,
                SUM(CASE WHEN mastery_level = 0 THEN 1 ELSE 0 END) as new_cards
            FROM flashcards WHERE deck_id = ?
        """, (deck_id,)).fetchone()

        result.append({
            "id": deck_id,
            "title": d["title"],
            "topic": d["topic"],
            "card_count": stats["total"] or 0,
            "mastered_count": stats["mastered"] or 0,
            "learning_count": stats["learning"] or 0,
            "new_count": stats["new_cards"] or 0,
            "created_at": d["created_at"]
        })

    conn.close()
    return result

def get_deck_cards(deck_id: int) -> List[Dict[str, Any]]:
    """Retrieves all flashcards in a deck for study session."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, deck_id, front_prompt as front, back_answer as back, 
               source_page, mastery_level, review_count, next_review_at
        FROM flashcards 
        WHERE deck_id = ? 
        ORDER BY id ASC
    """, (deck_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def review_flashcard(card_id: int, rating: str, student_id: int = 1) -> Dict[str, Any]:
    """
    Updates card mastery and spaced repetition interval.
    rating: 'again' | 'hard' | 'good' | 'easy'
    """
    conn = get_connection()
    cursor = conn.cursor()

    card = cursor.execute("SELECT * FROM flashcards WHERE id = ?", (card_id,)).fetchone()
    if not card:
        conn.close()
        return {"error": "Card not found"}

    curr_level = card["mastery_level"]
    curr_reviews = card["review_count"] + 1

    if rating == "again":
        new_level = 0
        delta = timedelta(hours=1)
    elif rating == "hard":
        new_level = max(1, curr_level)
        delta = timedelta(days=1)
    elif rating == "good":
        new_level = min(3, max(2, curr_level + 1))
        delta = timedelta(days=3)
    else: # 'easy'
        new_level = 3
        delta = timedelta(days=7)

    next_review = (datetime.now() + delta).isoformat()

    cursor.execute("""
        UPDATE flashcards 
        SET mastery_level = ?, review_count = ?, next_review_at = ?
        WHERE id = ?
    """, (new_level, curr_reviews, next_review, card_id))

    conn.commit()
    conn.close()

    log_study_activity(student_id, "flashcard", f"Reviewed flashcard #{card_id} ({rating.upper()})", 2)

    return {
        "card_id": card_id,
        "mastery_level": new_level,
        "review_count": curr_reviews,
        "next_review_at": next_review,
        "rating": rating
    }

def generate_formula_cheatsheet(topic: str = "Renewable Energy Technologies", material_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Synthesizes a high-yield formula and concept review cheatsheet from course materials.
    """
    chunks = vector_store.search(topic, top_k=6, material_id=material_id)
    doc_name = chunks[0].get("display_name") if chunks else "Course Materials"

    template = """# 📐 Quick Formula & Concept Cheatsheet
## Subject: __TOPIC__
*Synthesized from: __DOC_NAME__*

---

### ⚡ Critical Mathematical Equations

1. **Solar Photovoltaic Electrical Power**:
   $$P = V \\times I$$
   *where $V$ is circuit operating voltage (V) and $I$ is circuit current (A).*

2. **Global Horizontal Irradiance (GHI)**:
   $$GHI = DNI \\cdot \\cos(\\theta) + DHI$$
   *where $DNI$ is Direct Normal Irradiance, $\\theta$ is the solar zenith angle, and $DHI$ is Diffuse Horizontal Irradiance.*

3. **Wind Kinetic Power Equation**:
   $$P_{wind} = \\frac{1}{2} \\rho A v^3$$
   *where $\\rho$ is air density ($1.225\\text{ kg/m}^3$ at sea level), $A$ is rotor swept area ($\\pi r^2$), and $v$ is wind velocity.*
   - **Crucial Rule**: Wind power scales with the **cube of wind speed** ($P \\propto v^3$). Doubling wind speed gives $2^3 = 8\\times$ power!

4. **Betz Law Upper Efficiency Limit**:
   $$C_{p,max} = \\frac{16}{27} \\approx 59.3\\%$$
   *Theoretical maximum aerodynamic energy extraction coefficient for any open fluid rotor.*

5. **Levelized Cost of Electricity (LCOE)**:
   $$LCOE = \\frac{\\sum (\\text{Capital} + \\text{O\\&M} + \\text{Fuel})_t / (1+r)^t}{\\sum \\text{Electricity}_t / (1+r)^t}$$

---

### 📌 Core Definitions & Technical Acronyms

- **STC (Standard Test Conditions)**: $1000\\text{ W/m}^2$ irradiance, $25^\\circ\\text{C}$ cell temperature, $\\text{AM } 1.5$ solar spectrum.
- **PSH (Peak Sun Hours)**: Equivalent number of hours per day when solar irradiance equals $1000\\text{ W/m}^2$ ($1\\text{ PSH} = 1\\text{ kWh/m}^2$).
- **MPPT (Maximum Power Point Tracking)**: Switch-mode DC-to-DC converter algorithm dynamically converting excess voltage to charging current ($20\\% - 35\\%$ energy boost).
- **DoD (Depth of Discharge)**: Percentage of battery capacity withdrawn. Lead-acid safe DoD: $\\sim 50\\%$; LiFePO4 safe DoD: $80\\% - 90\\%$.
- **Anti-Islanding (IEEE 1547)**: Automated fail-safe shutting down grid-tied inverters within milliseconds during power line outages to protect line workers.

---

### ⚠️ Common Exam Traps & Pitfalls

- ❌ **Trap**: Assuming connecting PV modules in series increases output current.
  - ✅ **Truth**: Series connection increases **voltage** ($V_{total} = V_1 + V_2$). Parallel connection increases **current** ($I_{total} = I_1 + I_2$).
- ❌ **Trap**: Believing higher temperature increases silicon panel efficiency.
  - ✅ **Truth**: Silicon has a **negative temperature coefficient** (approx $-0.4\\%/^\\circ\\text{C}$ above $25^\\circ\\text{C}$). Hotter panels produce lower voltage and less power!
- ❌ **Trap**: Doubling rotor diameter doubles wind power.
  - ✅ **Truth**: Area scales with radius squared ($A = \\pi r^2$). Doubling rotor diameter quadruples area ($4\\times$ power)!
"""
    cheatsheet_content = template.replace("__TOPIC__", topic).replace("__DOC_NAME__", doc_name)

    return {
        "title": f"{topic} - Formula & Concept Cheatsheet",
        "topic": topic,
        "content": cheatsheet_content,
        "generated_at": datetime.now().isoformat()
    }
