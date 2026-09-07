function initChat() {
  const input = document.getElementById("chat-input");
  const sendBtn = document.getElementById("chat-send-btn");
  const newChatBtn = document.getElementById("new-chat-btn");
  const personaBtns = document.querySelectorAll(".persona-btn");

  // Persona switching
  personaBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      personaBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      State.currentPersona = btn.dataset.persona;
      showToast(`Switched persona to ${btn.textContent}`, "info");
    });
  });

  // Send message
  if (sendBtn) {
    sendBtn.addEventListener("click", () => sendMessage());
  }

  if (input) {
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  }

  // New Chat
  if (newChatBtn) {
    newChatBtn.addEventListener("click", async () => {
      try {
        const newConv = await API.post("/api/tutor/conversations", {
          title: "New Study Session",
          persona: State.currentPersona
        });
        State.activeConversationId = newConv.id;
        document.getElementById("chat-messages").innerHTML = "";
        renderWelcomeMessage();
        showToast("Started a new study session", "success");
      } catch (err) {
        showToast("Error creating conversation", "error");
      }
    });
  }
}

async function loadMessages(convId) {
  const container = document.getElementById("chat-messages");
  if (!container) return;
  container.innerHTML = "";

  try {
    const messages = await API.get(`/api/tutor/conversations/${convId}/messages`);
    if (messages.length === 0) {
      renderWelcomeMessage();
      return;
    }

    messages.forEach(msg => {
      appendMessage(msg.sender, msg.content, msg.citations);
    });
    scrollChatToBottom();
  } catch (err) {
    console.error("Failed to load messages", err);
  }
}

function renderWelcomeMessage() {
  const name = State.student ? State.student.name : "there";
  const welcomeText = `### 👋 Welcome to your AI Study Room, ${name}!
I am your personal virtual tutor equipped with **RAG**, **Conversational Memory**, and **Study Tools**.

Here is what we can do together:
- 📖 **Ask questions** on your uploaded PDFs (e.g., *"Explain the working of a solar photovoltaic system."*)
- 📝 **Generate practice quizzes** (e.g., *"Give me a 5-question quiz on charge controllers."*)
- 📅 **Build a personalized study plan** tailored to your exam target.
- 🎯 **Pinpoint weak topics** and get custom revision recommendations.

Feel free to pick a prompt below or type your question!`;

  appendMessage("assistant", welcomeText, [], [
    "Explain the working of a solar photovoltaic system",
    "What is the difference between PWM and MPPT charge controllers?",
    "How does an inverter synchronize with the utility AC grid?",
    "Create a 7-day study plan for Renewable Energy Technologies"
  ]);
}

async function sendMessage(overrideText = null) {
  const input = document.getElementById("chat-input");
  const text = (overrideText || (input ? input.value : "")).trim();
  if (!text) return;

  if (input && !overrideText) input.value = "";

  // Append user bubble
  appendMessage("user", text);
  scrollChatToBottom();

  // Show thinking indicator
  const typingId = appendTypingIndicator();
  scrollChatToBottom();

  try {
    const materialSelect = document.getElementById("chat-material-filter");
    const materialId = materialSelect && materialSelect.value ? parseInt(materialSelect.value) : null;

    const res = await API.post("/api/tutor/chat", {
      query: text,
      conversation_id: State.activeConversationId,
      persona: State.currentPersona,
      material_id: materialId
    });

    removeTypingIndicator(typingId);
    appendMessage("assistant", res.answer, res.citations, res.follow_ups);
    scrollChatToBottom();

    // Update suggested follow-up container
    renderSuggestedPills(res.follow_ups);
    
    // Refresh context panel facts
    updateChatContextPanel();
  } catch (err) {
    removeTypingIndicator(typingId);
    appendMessage("assistant", "⚠️ Sorry, I encountered an error answering your question. Please ensure your backend is active or check settings.");
  }
}

function appendMessage(sender, markdownContent, citations = [], followUps = []) {
  const container = document.getElementById("chat-messages");
  if (!container) return;

  const bubble = document.createElement("div");
  bubble.className = `message-bubble ${sender}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar-icon";
  avatar.textContent = sender === "user" ? (State.student ? State.student.name.charAt(0) : "U") : "AI";

  const contentBox = document.createElement("div");
  contentBox.className = "message-content";

  // Parse markdown
  let formattedHtml = typeof marked !== "undefined" ? marked.parse(markdownContent) : markdownContent.replace(/\n/g, "<br>");
  contentBox.innerHTML = formattedHtml;

  // Add citations if assistant
  if (sender === "assistant" && citations && citations.length > 0) {
    const citContainer = document.createElement("div");
    citContainer.className = "citations-container";
    
    const citHeader = document.createElement("div");
    citHeader.className = "citation-header";
    citHeader.innerHTML = `<span>📑</span> <span>Source Citations (${citations.length} Grounded References)</span>`;
    citContainer.appendChild(citHeader);

    citations.forEach((c, idx) => {
      const badge = document.createElement("span");
      badge.className = "citation-badge";
      const docName = c.display_name || c.filename || "Course Doc";
      badge.innerHTML = `<strong>[${idx+1}]</strong> ${docName} • Page ${c.page_number} (${Math.round(c.score * 100)}% match)`;
      badge.title = `Snippet: "${c.snippet}"`;
      badge.addEventListener("click", () => {
        showCitationModal(c);
      });
      citContainer.appendChild(badge);
    });

    contentBox.appendChild(citContainer);
  }

  // Add Audio Tutor Read Aloud button for assistant messages
  if (sender === "assistant") {
    const audioBar = document.createElement("div");
    audioBar.style.display = "flex";
    audioBar.style.justifyContent = "flex-end";
    audioBar.style.marginTop = "8px";
    
    const audioBtn = document.createElement("button");
    audioBtn.className = "btn btn-secondary btn-sm";
    audioBtn.style.padding = "2px 8px";
    audioBtn.style.fontSize = "11px";
    audioBtn.innerHTML = "🔊 Listen";
    audioBtn.title = "Read aloud with AI voice";
    audioBtn.addEventListener("click", () => toggleSpeech(markdownContent, audioBtn));
    audioBar.appendChild(audioBtn);
    contentBox.appendChild(audioBar);
  }

  bubble.appendChild(avatar);
  bubble.appendChild(contentBox);
  container.appendChild(bubble);

  // If follow-ups provided, update bottom pills
  if (followUps && followUps.length > 0) {
    renderSuggestedPills(followUps);
  }
}

function appendTypingIndicator() {
  const container = document.getElementById("chat-messages");
  const id = `typing-${Date.now()}`;
  const bubble = document.createElement("div");
  bubble.className = "message-bubble assistant";
  bubble.id = id;

  bubble.innerHTML = `
    <div class="avatar-icon">AI</div>
    <div class="message-content" style="display: flex; align-items: center; gap: 8px;">
      <span style="font-size: 13px; color: var(--text-secondary);">Analyzing course materials & synthesizing answer...</span>
    </div>
  `;
  container.appendChild(bubble);
  return id;
}

function removeTypingIndicator(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function renderSuggestedPills(pills) {
  const container = document.getElementById("chat-suggested-pills");
  if (!container) return;
  container.innerHTML = "";
  if (!pills || pills.length === 0) return;

  pills.forEach(p => {
    const pill = document.createElement("button");
    pill.className = "suggested-pill";
    pill.textContent = p;
    pill.addEventListener("click", () => {
      sendMessage(p);
    });
    container.appendChild(pill);
  });
}

function scrollChatToBottom() {
  const container = document.getElementById("chat-messages");
  if (container) {
    container.scrollTop = container.scrollHeight;
  }
}

function showCitationModal(citation) {
  const modal = document.getElementById("citation-modal");
  const body = document.getElementById("citation-modal-body");
  if (!modal || !body) return;

  body.innerHTML = `
    <h3 style="margin-bottom: 8px; color: var(--accent-primary);">${citation.display_name || citation.filename}</h3>
    <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 14px;">
      <strong>Page:</strong> ${citation.page_number} | 
      <strong>Section:</strong> ${citation.heading || "General"} | 
      <strong>Relevance Score:</strong> ${Math.round(citation.score * 100)}%
    </div>
    <div style="background: var(--bg-input); padding: 14px; border-radius: 8px; border: 1px solid var(--border-color); font-size: 13.5px; line-height: 1.6;">
      <p>${citation.snippet || "No detailed snippet available."}</p>
    </div>
  `;
  modal.classList.add("show");
}

async function updateChatContextPanel() {
  try {
    const memory = await API.get("/api/student/memory");
    const container = document.getElementById("chat-memory-box");
    if (!container) return;

    if (memory.weak_topics && memory.weak_topics.length > 0) {
      container.innerHTML = memory.weak_topics.slice(0, 3).map(w => `
        <div style="font-size: 12px; margin-bottom: 8px; padding: 6px 10px; background: rgba(245, 158, 11, 0.1); border-left: 3px solid var(--warning); border-radius: 4px;">
          <strong>${w.topic}</strong> (Score: ${w.average_score}%)<br>
          <span style="color: var(--text-secondary);">${w.recommendation}</span>
        </div>
      `).join("");
    } else {
      container.innerHTML = `<p style="font-size: 12px; color: var(--text-muted);">No weak topics identified yet. Take a quiz to assess mastery!</p>`;
    }
  } catch (err) {
    console.error("Failed to update chat context panel", err);
  }
}

function toggleSpeech(text, btn) {
  if (!('speechSynthesis' in window)) {
    showToast("Speech synthesis is not supported in this browser.", "info");
    return;
  }
  if (window.speechSynthesis.speaking) {
    window.speechSynthesis.cancel();
    btn.innerHTML = "🔊 Listen";
    return;
  }
  
  // Clean markdown syntax for speech
  const clean = text.replace(/#{1,6}\s*/g, '')
                    .replace(/\*{1,3}/g, '')
                    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
                    .replace(/`{1,3}[^`]*`{1,3}/g, '')
                    .replace(/>\s*/g, '');

  const utterance = new SpeechSynthesisUtterance(clean);
  utterance.rate = 1.0;
  utterance.pitch = 1.0;
  utterance.onend = () => { btn.innerHTML = "🔊 Listen"; };
  utterance.onerror = () => { btn.innerHTML = "🔊 Listen"; };
  btn.innerHTML = "⏹ Stop";
  window.speechSynthesis.speak(utterance);
}
