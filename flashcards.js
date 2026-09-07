// Flashcard Studio & Spaced Repetition (SRS)
let activeDeck = null;
let currentCardIndex = 0;
let isCardFlipped = false;

function initFlashcards() {
  const genBtn = document.getElementById("generate-flashcards-btn");
  const flipBtn = document.getElementById("flashcard-flip-btn");

  if (genBtn) {
    genBtn.addEventListener("click", async () => {
      const topicInput = document.getElementById("flashcard-topic-input");
      const matSelect = document.getElementById("flashcard-material-select");
      const countSelect = document.getElementById("flashcard-count-select");

      const topic = topicInput ? topicInput.value.trim() || "Solar Photovoltaic Systems" : "Solar Photovoltaic Systems";
      const materialId = matSelect && matSelect.value ? parseInt(matSelect.value) : null;
      const count = countSelect ? parseInt(countSelect.value) : 5;

      genBtn.disabled = true;
      genBtn.textContent = "Synthesizing Flashcards...";

      try {
        const deck = await API.post("/api/flashcards/generate", {
          topic,
          material_id: materialId,
          count
        });
        showToast(`Created flashcard deck with ${deck.card_count} cards!`, "success");
        await loadFlashcardDecks();
        openDeckForStudy(deck.deck_id);
      } catch (err) {
        showToast("Error generating flashcards", "error");
      } finally {
        genBtn.disabled = false;
        genBtn.textContent = "🃏 Generate Flashcard Deck";
      }
    });
  }

  // Keyboard navigation for flashcard review
  document.addEventListener("keydown", (e) => {
    if (State.currentTab !== "flashcards" || !activeDeck) return;
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;

    if (e.code === "Space") {
      e.preventDefault();
      flipFlashcard();
    } else if (isCardFlipped) {
      if (e.key === "1") submitCardRating("again");
      if (e.key === "2") submitCardRating("hard");
      if (e.key === "3") submitCardRating("good");
      if (e.key === "4") submitCardRating("easy");
    }
  });
}

async function loadFlashcardDecks() {
  const container = document.getElementById("flashcard-decks-list");
  const matSelect = document.getElementById("flashcard-material-select");
  if (!container) return;

  // Populate material select if empty
  if (matSelect && State.materials && matSelect.options.length <= 1) {
    matSelect.innerHTML = `<option value="">Auto-select from best match</option>` + 
      State.materials.map(m => `<option value="${m.id}">${m.display_name || m.filename}</option>`).join("");
  }

  try {
    const decks = await API.get("/api/flashcards/decks");
    if (decks.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 30px; background: var(--bg-card); border-radius: var(--card-radius); border: 1px dashed var(--border-color);">
          <div style="font-size: 32px; margin-bottom: 8px;">🃏</div>
          <h4 style="font-size: 15px; font-weight: 600; margin-bottom: 4px;">No Flashcard Decks Yet</h4>
          <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 12px;">
            Generate your first active recall deck using the form on the left.
          </p>
        </div>
      `;
      return;
    }

    container.innerHTML = decks.map(d => `
      <div class="card" style="padding: 14px; margin-bottom: 10px; cursor: pointer; border: 1px solid var(--border-color);" onclick="openDeckForStudy(${d.id})">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
          <h4 style="font-size: 14px; font-weight: 700; color: var(--text-primary);">${d.title}</h4>
          <span class="badge" style="background: rgba(59, 130, 246, 0.15); color: var(--accent-secondary); font-size: 11px;">
            ${d.card_count} Cards
          </span>
        </div>
        <div style="display: flex; gap: 12px; font-size: 11.5px; color: var(--text-muted);">
          <span>🏆 Mastered: <strong>${d.mastered_count}</strong></span>
          <span>🔄 Learning: <strong>${d.learning_count}</strong></span>
          <span>🆕 New: <strong>${d.new_count}</strong></span>
        </div>
      </div>
    `).join("");

    // If no active deck opened, open the first one
    if (!activeDeck && decks.length > 0) {
      openDeckForStudy(decks[0].id);
    }
  } catch (err) {
    console.error("Failed to load flashcard decks", err);
  }
}

async function openDeckForStudy(deckId) {
  try {
    const cards = await API.get(`/api/flashcards/decks/${deckId}`);
    if (cards.length === 0) {
      showToast("This deck has no cards", "info");
      return;
    }
    activeDeck = { id: deckId, cards };
    currentCardIndex = 0;
    isCardFlipped = false;
    renderCurrentFlashcard();
  } catch (err) {
    showToast("Error opening deck", "error");
  }
}

function renderCurrentFlashcard() {
  const container = document.getElementById("flashcard-viewer-area");
  if (!container || !activeDeck) return;

  const cards = activeDeck.cards;
  if (currentCardIndex >= cards.length) {
    // Completed review session!
    container.innerHTML = `
      <div class="card" style="text-align: center; padding: 48px 24px;">
        <div style="font-size: 48px; margin-bottom: 16px;">🎉</div>
        <h2 style="font-size: 22px; font-weight: 800; margin-bottom: 8px;">Review Session Completed!</h2>
        <p style="font-size: 14px; color: var(--text-secondary); margin-bottom: 24px;">
          You reviewed all ${cards.length} cards in this deck. Spaced repetition intervals have been scheduled!
        </p>
        <div style="display: flex; justify-content: center; gap: 12px;">
          <button class="btn btn-primary" onclick="openDeckForStudy(${activeDeck.id})">🔄 Review Deck Again</button>
          <button class="btn btn-secondary" onclick="switchTab('analytics')">📊 Check Mastery Analytics</button>
        </div>
      </div>
    `;
    return;
  }

  const card = cards[currentCardIndex];
  isCardFlipped = false;

  container.innerHTML = `
    <!-- Header info -->
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
      <span style="font-size: 13px; font-weight: 700; color: var(--accent-primary);">
        Card ${currentCardIndex + 1} of ${cards.length}
      </span>
      <span style="font-size: 11px; background: rgba(59, 130, 246, 0.15); color: var(--accent-secondary); padding: 3px 8px; border-radius: 4px;">
        Page ${card.source_page}
      </span>
    </div>

    <!-- 3D Card Viewer -->
    <div class="flashcard-scene" onclick="flipFlashcard()">
      <div class="flashcard-card" id="active-flashcard-card">
        <!-- Front Face -->
        <div class="flashcard-face flashcard-front">
          <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: var(--text-muted); margin-bottom: 12px;">
            QUESTION / PROMPT (Click or Space to Flip)
          </div>
          <div class="flashcard-text">
            ${card.front}
          </div>
          <div style="margin-top: auto; font-size: 11.5px; color: var(--accent-secondary);">
            💡 <em>Click card to reveal explanation</em>
          </div>
        </div>

        <!-- Back Face -->
        <div class="flashcard-face flashcard-back">
          <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: var(--success); margin-bottom: 12px;">
            ANSWER & CONCEPT EXPLANATION
          </div>
          <div class="flashcard-text" style="font-size: 14.5px; line-height: 1.6;">
            ${card.back.replace(/\n/g, '<br>')}
          </div>
          <div style="margin-top: auto; font-size: 11.5px; color: var(--text-muted);">
            Source Reference: Page ${card.source_page}
          </div>
        </div>
      </div>
    </div>

    <!-- Review Rating Buttons (Visible when flipped or toggleable) -->
    <div id="flashcard-controls-bar" style="display: flex; justify-content: center; gap: 10px; margin-top: 20px;">
      <button class="btn btn-secondary" onclick="flipFlashcard()" id="flip-button-label">
        🔄 Flip Card (Space)
      </button>
      <div id="rating-buttons-group" style="display: none; gap: 8px;">
        <button class="btn btn-sm" style="background: #ef4444; color: white;" onclick="submitCardRating('again')" title="Key: 1">
          🔴 Again (1h)
        </button>
        <button class="btn btn-sm" style="background: #f59e0b; color: white;" onclick="submitCardRating('hard')" title="Key: 2">
          🟠 Hard (1d)
        </button>
        <button class="btn btn-sm" style="background: #10b981; color: white;" onclick="submitCardRating('good')" title="Key: 3">
          🟢 Good (3d)
        </button>
        <button class="btn btn-sm" style="background: #3b82f6; color: white;" onclick="submitCardRating('easy')" title="Key: 4">
          🔵 Easy (7d)
        </button>
      </div>
    </div>
  `;
}

function flipFlashcard() {
  const cardEl = document.getElementById("active-flashcard-card");
  const ratingGroup = document.getElementById("rating-buttons-group");
  const flipBtnLabel = document.getElementById("flip-button-label");
  if (!cardEl) return;

  isCardFlipped = !isCardFlipped;
  if (isCardFlipped) {
    cardEl.classList.add("is-flipped");
    if (ratingGroup) ratingGroup.style.display = "flex";
    if (flipBtnLabel) flipBtnLabel.style.display = "none";
  } else {
    cardEl.classList.remove("is-flipped");
    if (ratingGroup) ratingGroup.style.display = "none";
    if (flipBtnLabel) flipBtnLabel.style.display = "inline-flex";
  }
}

async function submitCardRating(rating) {
  if (!activeDeck || currentCardIndex >= activeDeck.cards.length) return;
  const card = activeDeck.cards[currentCardIndex];

  try {
    await API.post(`/api/flashcards/cards/${card.id}/review`, { rating });
    currentCardIndex++;
    renderCurrentFlashcard();
  } catch (err) {
    showToast("Failed to save review", "error");
  }
}
