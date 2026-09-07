function initPlanner() {
  const genBtn = document.getElementById("generate-plan-btn");

  if (genBtn) {
    genBtn.addEventListener("click", async () => {
      const subjectInput = document.getElementById("plan-subject-input");
      const goalInput = document.getElementById("plan-goal-input");
      const daysInput = document.getElementById("plan-days-input");
      const hoursInput = document.getElementById("plan-hours-input");

      const subject = subjectInput ? subjectInput.value.trim() || "Renewable Energy Technologies" : "Renewable Energy Technologies";
      const goal = goalInput ? goalInput.value.trim() || "Master Core Principles for Final Exam" : "Master Core Principles for Final Exam";
      const days = daysInput ? parseInt(daysInput.value) : 7;
      const hours = hoursInput ? parseFloat(hoursInput.value) : 1.5;

      genBtn.disabled = true;
      genBtn.textContent = "Synthesizing Roadmap...";

      try {
        const plan = await API.post("/api/plans/generate", {
          subject,
          goal,
          total_days: days,
          daily_hours: hours,
          difficulty: "intermediate"
        });

        showToast(`Created ${days}-day learning roadmap for "${subject}"!`, "success");
        await loadPlans();
      } catch (err) {
        showToast("Error creating learning plan", "error");
      } finally {
        genBtn.disabled = false;
        genBtn.textContent = "📅 Create Learning Plan";
      }
    });
  }
}

async function loadPlans() {
  const container = document.getElementById("active-plans-container");
  if (!container) return;

  try {
    const plans = await API.get("/api/plans");
    if (plans.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 40px; background: var(--bg-card); border-radius: var(--card-radius); border: 1px dashed var(--border-color);">
          <div style="font-size: 32px; margin-bottom: 12px;">📅</div>
          <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 6px;">No Active Study Plan</h3>
          <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 16px;">
            Set your target exam goal and study availability on the left to generate your custom roadmap.
          </p>
        </div>
      `;
      return;
    }

    const currentPlan = plans[0]; // Show latest active plan
    container.innerHTML = `
      <div class="card" style="margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
          <div>
            <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: var(--success); font-size: 11px; padding: 3px 8px; border-radius: 6px;">
              ACTIVE ROADMAP
            </span>
            <h2 style="font-size: 18px; font-weight: 700; margin-top: 6px;">${currentPlan.subject}</h2>
            <p style="font-size: 13px; color: var(--text-secondary); margin-top: 2px;">Goal: ${currentPlan.goal}</p>
          </div>
          <div style="text-align: right;">
            <div style="font-size: 20px; font-weight: 800; color: var(--accent-primary);" id="plan-pct-badge">
              ${currentPlan.progress_percentage}%
            </div>
            <div style="font-size: 11.5px; color: var(--text-muted);" id="plan-count-badge">
              ${currentPlan.completed_sessions} of ${currentPlan.total_sessions} completed
            </div>
          </div>
        </div>

        <div class="progress-bar-container">
          <div class="progress-bar-fill" id="plan-progress-fill" style="width: ${currentPlan.progress_percentage}%;"></div>
        </div>
      </div>

      <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 14px;">Daily Study Sessions Checklist</h3>
      <div class="sessions-list" style="display: flex; flex-direction: column; gap: 12px;">
        ${currentPlan.sessions.map(s => `
          <div class="card" style="padding: 16px; border-left: 4px solid ${s.is_completed ? 'var(--success)' : 'var(--accent-primary)'}; background: ${s.is_completed ? 'rgba(16, 185, 129, 0.04)' : 'var(--bg-card)'};">
            <div style="display: flex; align-items: flex-start; gap: 14px;">
              <input type="checkbox" id="session_chk_${s.id}" ${s.is_completed ? 'checked' : ''} 
                     style="width: 20px; height: 20px; margin-top: 3px; accent-color: var(--success); cursor: pointer;"
                     onchange="toggleSession(${s.id})">
              <div style="flex: 1;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <h4 style="font-size: 15px; font-weight: 600; text-decoration: ${s.is_completed ? 'line-through' : 'none'}; color: ${s.is_completed ? 'var(--text-muted)' : 'var(--text-primary)'};">
                    ${s.title}
                  </h4>
                  <span style="font-size: 12px; color: var(--text-muted);">⏱ ${s.estimated_minutes} mins</span>
                </div>
                <div style="font-size: 13px; color: var(--text-secondary); margin: 6px 0;">
                  <strong>Focus:</strong> ${s.topic}
                </div>
                <div style="font-size: 12.5px; color: var(--text-muted); margin-bottom: 8px;">
                  🎯 <em>${s.objective}</em>
                </div>
                <div style="font-size: 12px; background: var(--bg-input); padding: 6px 10px; border-radius: 6px; display: inline-flex; align-items: center; gap: 6px;">
                  <span>📖</span> <span>${s.reading_references}</span>
                </div>
                <div style="margin-top: 10px; display: flex; gap: 8px;">
                  <button class="btn btn-secondary btn-sm" onclick="switchTab('chat'); sendMessage('Let\\'s begin studying Day ${s.day_number}: ${s.topic}. Can you explain the core concepts and give me an interactive lesson?')">
                    💬 Study with Tutor
                  </button>
                  <button class="btn btn-secondary btn-sm" onclick="switchTab('quiz'); document.getElementById('quiz-topic-input').value = '${s.topic}'; document.getElementById('generate-quiz-btn').click();">
                    ⚡ Quiz This Topic
                  </button>
                </div>
              </div>
            </div>
          </div>
        `).join("")}
      </div>
    `;
  } catch (err) {
    console.error("Failed to load plans", err);
  }
}

async function toggleSession(sessionId) {
  try {
    const res = await API.post(`/api/plans/sessions/${sessionId}/toggle`, {});
    showToast(res.is_completed ? "Session marked complete! Great progress!" : "Session reopened", "success");
    
    // Update progress bar
    const fill = document.getElementById("plan-progress-fill");
    const pctBadge = document.getElementById("plan-pct-badge");
    const countBadge = document.getElementById("plan-count-badge");
    if (fill) fill.style.width = `${res.progress_percentage}%`;
    if (pctBadge) pctBadge.textContent = `${res.progress_percentage}%`;
    if (countBadge) countBadge.textContent = `${res.completed_count} of ${res.total_count} completed`;

    await loadPlans();
  } catch (err) {
    showToast("Error updating session", "error");
  }
}
