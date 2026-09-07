async function loadAnalytics() {
  const container = document.getElementById("analytics-dashboard-container");
  if (!container) return;

  try {
    const data = await API.get("/api/analytics");
    State.analytics = data;

    const ov = data.overview;
    container.innerHTML = `
      <!-- Top Metrics -->
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-icon-box" style="background: rgba(59, 130, 246, 0.15); color: var(--accent-primary);">⏱</div>
          <div>
            <div class="metric-number">${ov.total_study_hours} hrs</div>
            <div class="metric-label">Total Study Time</div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon-box" style="background: rgba(16, 185, 129, 0.15); color: var(--success);">📝</div>
          <div>
            <div class="metric-number">${ov.total_quizzes}</div>
            <div class="metric-label">Quizzes Completed</div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon-box" style="background: rgba(245, 158, 11, 0.15); color: var(--warning);">🎯</div>
          <div>
            <div class="metric-number">${ov.average_quiz_score}%</div>
            <div class="metric-label">Average Score</div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon-box" style="background: rgba(236, 72, 153, 0.15); color: #ec4899;">🔥</div>
          <div>
            <div class="metric-number">${ov.streak_days} Days</div>
            <div class="metric-label">Study Streak</div>
          </div>
        </div>
      </div>

      <!-- Revision Recommendations & Weak Areas Alert -->
      <div class="card" style="margin-bottom: 24px;">
        <div class="card-header">
          <div class="card-title">
            <span>🎯</span> <span>AI Revision Recommendations & Targeted Review</span>
          </div>
          <span class="badge" style="background: rgba(245, 158, 11, 0.15); color: var(--warning);">
            Based on Memory & Quiz History
          </span>
        </div>

        <div class="recommendations-list">
          ${data.recommendations.map(r => `
            <div class="alert-box alert-warning" style="margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
              <div>
                <strong>${r.topic}</strong> (Avg: ${r.average_score}%)<br>
                <span style="font-size: 13px;">${r.action_text}</span>
              </div>
              <button class="btn btn-primary btn-sm" onclick="switchTab('chat'); sendMessage('I need to revise ${r.topic}. Can you explain the most critical concepts and test me on them?')">
                Revise Now ➔
              </button>
            </div>
          `).join("")}
        </div>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">
        <!-- Topic Mastery Radar / Bars -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">
              <span>📊</span> <span>Topic Mastery Progress</span>
            </div>
          </div>
          <div class="mastery-bars" style="display: flex; flex-direction: column; gap: 16px;">
            ${data.mastery.map(m => `
              <div>
                <div style="display: flex; justify-content: space-between; font-size: 13.5px; margin-bottom: 6px;">
                  <span><strong>${m.topic}</strong></span>
                  <span style="font-weight: 700; color: ${m.mastery_percentage >= 80 ? 'var(--success)' : m.mastery_percentage >= 60 ? 'var(--warning)' : 'var(--danger)'};">
                    ${m.mastery_percentage}% (${m.status})
                  </span>
                </div>
                <div class="progress-bar-container">
                  <div class="progress-bar-fill" style="width: ${m.mastery_percentage}%; background: ${m.mastery_percentage >= 80 ? 'var(--success)' : m.mastery_percentage >= 60 ? 'var(--warning)' : 'var(--danger)'};"></div>
                </div>
              </div>
            `).join("")}
          </div>
        </div>

        <!-- Recent Activity Timeline -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">
              <span>🕒</span> <span>Recent Study Activity Timeline</span>
            </div>
          </div>
          <div class="activity-timeline" style="display: flex; flex-direction: column; gap: 12px;">
            ${data.recent_activities.length > 0 ? data.recent_activities.map(a => `
              <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; background: var(--bg-input); border-radius: 8px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                  <span style="font-size: 18px;">
                    ${a.activity_type === 'quiz' ? '📝' : a.activity_type === 'read' ? '📖' : a.activity_type === 'chat' ? '💬' : '📅'}
                  </span>
                  <div>
                    <div style="font-size: 13px; font-weight: 600;">${a.description}</div>
                    <div style="font-size: 11px; color: var(--text-muted);">${new Date(a.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} • Duration: ${a.duration_minutes}m</div>
                  </div>
                </div>
                ${a.score !== null && a.score !== undefined ? `
                  <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: var(--success); font-weight: 700;">
                    ${a.score}%
                  </span>
                ` : ''}
              </div>
            `).join("") : `<p style="font-size: 13px; color: var(--text-muted);">No recent study activities recorded yet.</p>`}
          </div>
        </div>
      </div>
    `;
  } catch (err) {
    console.error("Failed to load analytics", err);
  }
}
