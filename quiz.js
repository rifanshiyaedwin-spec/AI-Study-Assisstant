function initQuiz() {
  const genBtn = document.getElementById("generate-quiz-btn");
  const submitBtn = document.getElementById("submit-quiz-btn");

  if (genBtn) {
    genBtn.addEventListener("click", async () => {
      const topicInput = document.getElementById("quiz-topic-input");
      const diffSelect = document.getElementById("quiz-difficulty-select");
      const countSelect = document.getElementById("quiz-count-select");
      const matSelect = document.getElementById("quiz-material-select");

      const topic = topicInput ? topicInput.value.trim() || "Solar Photovoltaic Systems" : "Solar Photovoltaic Systems";
      const difficulty = diffSelect ? diffSelect.value : "intermediate";
      const count = countSelect ? parseInt(countSelect.value) : 5;
      const materialId = matSelect && matSelect.value ? parseInt(matSelect.value) : null;

      genBtn.disabled = true;
      genBtn.textContent = "Synthesizing Quiz with AI...";

      try {
        const quiz = await API.post("/api/quiz/generate", {
          topic,
          difficulty,
          question_count: count,
          material_id: materialId
        });

        State.activeQuiz = quiz;
        renderActiveQuiz(quiz);
        showToast(`Generated ${quiz.total_questions} questions for "${topic}"!`, "success");
      } catch (err) {
        showToast("Error generating quiz", "error");
      } finally {
        genBtn.disabled = false;
        genBtn.textContent = "⚡ Generate Quiz Now";
      }
    });
  }

  if (submitBtn) {
    submitBtn.addEventListener("click", async () => {
      if (!State.activeQuiz) return;
      
      const userAnswers = {};
      State.activeQuiz.questions.forEach(q => {
        const selected = document.querySelector(`input[name="q_${q.id}"]:checked`);
        if (selected) {
          userAnswers[q.id] = selected.value;
        }
      });

      const answeredCount = Object.keys(userAnswers).length;
      if (answeredCount < State.activeQuiz.questions.length) {
        if (!confirm(`You have answered ${answeredCount} of ${State.activeQuiz.questions.length} questions. Submit anyway?`)) {
          return;
        }
      }

      submitBtn.disabled = true;
      submitBtn.textContent = "Evaluating & Updating Memory...";

      try {
        const res = await API.post("/api/quiz/evaluate", {
          quiz_id: State.activeQuiz.quiz_id,
          answers: userAnswers
        });

        renderQuizEvaluation(res);
        showToast(`Quiz completed! Score: ${res.score}/${res.total_questions}`, "success");
        await loadQuizHistory();
      } catch (err) {
        showToast("Error evaluating quiz", "error");
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Submit Answers & Evaluate";
      }
    });
  }
}

function renderActiveQuiz(quiz) {
  const container = document.getElementById("quiz-questions-area");
  const resultsContainer = document.getElementById("quiz-results-area");
  const actionBox = document.getElementById("quiz-actions-box");
  if (!container) return;

  if (resultsContainer) resultsContainer.style.display = "none";
  container.style.display = "block";
  if (actionBox) actionBox.style.display = "flex";

  container.innerHTML = `
    <div style="margin-bottom: 20px; padding: 14px 18px; background: var(--bg-input); border-radius: 10px; border-left: 4px solid var(--accent-primary);">
      <h2 style="font-size: 16px; font-weight: 700;">${quiz.topic}</h2>
      <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
        Difficulty: <strong>${quiz.difficulty.toUpperCase()}</strong> • Total Questions: <strong>${quiz.total_questions}</strong>
      </div>
    </div>
  ` + quiz.questions.map((q, idx) => `
    <div class="question-card" id="card_q_${q.id}">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
        <span style="font-size: 12px; font-weight: 700; color: var(--accent-primary);">Question ${idx + 1} of ${quiz.total_questions}</span>
        <span style="font-size: 11px; background: rgba(59, 130, 246, 0.1); color: var(--accent-secondary); padding: 2px 8px; border-radius: 4px;">
          Page ${q.source_page}
        </span>
      </div>
      <p style="font-size: 14.5px; font-weight: 600; line-height: 1.5; margin-bottom: 16px;">${q.question_text}</p>
      <div class="options-list">
        ${q.options.map(opt => `
          <label class="option-button">
            <input type="radio" name="q_${q.id}" value="${opt.replace(/"/g, '&quot;')}" style="accent-color: var(--accent-primary);">
            <span>${opt}</span>
          </label>
        `).join("")}
      </div>
    </div>
  `).join("");
}

function renderQuizEvaluation(evalResult) {
  const container = document.getElementById("quiz-questions-area");
  const resultsContainer = document.getElementById("quiz-results-area");
  const actionBox = document.getElementById("quiz-actions-box");

  if (container) container.style.display = "none";
  if (actionBox) actionBox.style.display = "none";
  if (!resultsContainer) return;
  resultsContainer.style.display = "block";

  const isGood = evalResult.percentage >= 70;
  const alertClass = isGood ? "alert-success" : "alert-warning";

  resultsContainer.innerHTML = `
    <div class="card" style="margin-bottom: 24px; text-align: center; padding: 32px 20px;">
      <div style="font-size: 44px; margin-bottom: 12px;">${isGood ? "🏆" : "📚"}</div>
      <h2 style="font-size: 24px; font-weight: 800; margin-bottom: 6px;">
        Score: ${evalResult.score} / ${evalResult.total_questions} (${evalResult.percentage}%)
      </h2>
      <div class="alert-box ${alertClass}" style="max-width: 600px; margin: 16px auto; text-align: left;">
        <div>
          <strong>🎯 Tutor Assessment & Memory Update:</strong><br>
          ${evalResult.feedback}
        </div>
      </div>
      <div style="display: flex; justify-content: center; gap: 12px; margin-top: 16px;">
        <button class="btn btn-primary" onclick="switchTab('analytics')">📊 View Learning Analytics</button>
        <button class="btn btn-secondary" onclick="switchTab('chat'); sendMessage('I just took the quiz on ${evalResult.topic} and scored ${evalResult.score}/${evalResult.total_questions}. Can you help me review the areas I missed?')">💬 Discuss with AI Tutor</button>
      </div>
    </div>

    <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 16px;">Detailed Question Breakdown & Explanations</h3>
    <div class="eval-breakdown">
      ${evalResult.evaluations.map((ev, idx) => `
        <div class="question-card" style="border-left: 4px solid ${ev.is_correct ? 'var(--success)' : 'var(--danger)'};">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-size: 13px; font-weight: 700; color: ${ev.is_correct ? 'var(--success)' : 'var(--danger)'};">
              ${ev.is_correct ? '✓ Correct' : '✗ Missed'} - Question ${idx + 1}
            </span>
            <span style="font-size: 11px; color: var(--text-muted);">Source: Page ${ev.source_page}</span>
          </div>
          <p style="font-weight: 600; margin-bottom: 12px;">${ev.question_text}</p>
          <div style="font-size: 13px; margin-bottom: 8px;">
            <span style="color: var(--text-muted);">Your Answer:</span> 
            <strong style="color: ${ev.is_correct ? 'var(--success)' : 'var(--danger)'};">${ev.user_answer || '(Unanswered)'}</strong>
          </div>
          ${!ev.is_correct ? `
            <div style="font-size: 13px; margin-bottom: 8px;">
              <span style="color: var(--text-muted);">Correct Answer:</span> 
              <strong style="color: var(--success);">${ev.correct_answer}</strong>
            </div>
          ` : ''}
          <div style="margin-top: 12px; padding: 12px; background: var(--bg-input); border-radius: 8px; font-size: 13px; line-height: 1.5;">
            <strong>💡 Explanation:</strong> ${ev.explanation}
          </div>
        </div>
      `).join("")}
    </div>
  `;
}

async function loadQuizHistory() {
  const container = document.getElementById("quiz-history-list");
  if (!container) return;

  try {
    const list = await API.get("/api/quiz/history");
    if (list.length === 0) {
      container.innerHTML = `<p style="font-size: 13px; color: var(--text-muted);">No quiz attempts logged yet. Generate your first quiz above!</p>`;
      return;
    }

    container.innerHTML = list.map(q => `
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 14px; background: var(--bg-input); border-radius: 8px; margin-bottom: 8px;">
        <div>
          <div style="font-size: 13.5px; font-weight: 600;">${q.topic}</div>
          <div style="font-size: 11px; color: var(--text-muted);">${new Date(q.completed_at).toLocaleDateString()} • ${q.difficulty.toUpperCase()}</div>
        </div>
        <div style="text-align: right;">
          <div style="font-size: 14px; font-weight: 700; color: ${q.percentage >= 70 ? 'var(--success)' : 'var(--warning)'};">
            ${q.score}/${q.total_questions} (${q.percentage}%)
          </div>
        </div>
      </div>
    `).join("");
  } catch (err) {
    console.error("Failed to load quiz history", err);
  }
}
