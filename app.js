// Global Application State & Router
const API = {
  get: async (url) => {
    const res = await fetch(url);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  post: async (url, data) => {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  put: async (url, data) => {
    const res = await fetch(url, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  delete: async (url) => {
    const res = await fetch(url, { method: "DELETE" });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  upload: async (url, formData) => {
    const res = await fetch(url, {
      method: "POST",
      body: formData
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }
};

const State = {
  currentTab: "chat",
  student: null,
  activeConversationId: null,
  currentPersona: "tutor",
  materials: [],
  activeQuiz: null,
  activePlan: null,
  analytics: null
};

// UI Toast Notification
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  
  const icon = type === "success" ? "✓" : type === "error" ? "⚠" : "ℹ";
  toast.innerHTML = `<span><strong>${icon}</strong></span> <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// Tab Switching
function switchTab(tabId) {
  State.currentTab = tabId;
  document.querySelectorAll(".nav-item").forEach(el => {
    el.classList.toggle("active", el.dataset.tab === tabId);
  });
  document.querySelectorAll(".tab-pane").forEach(el => {
    el.classList.toggle("active", el.id === `tab-${tabId}`);
  });

  const titles = {
    chat: { title: "AI Study Chat & RAG Tutor", desc: "Ask questions, get grounded explanations with source citations." },
    materials: { title: "Course Material Management", desc: "Upload and manage course PDFs, textbooks, and lecture notes." },
    quiz: { title: "AI Quiz Studio", desc: "Generate quizzes, practice exam questions, and test your comprehension." },
    flashcards: { title: "AI Flashcard Studio & Spaced Repetition", desc: "Active recall flashcards with automated spaced repetition scheduling." },
    planner: { title: "AI Learning Plan Generator", desc: "Structured daily study roadmap customized to your goals." },
    analytics: { title: "Progress Tracking & Mastery", desc: "Track learning progress, topic mastery, and revision recommendations." },
    settings: { title: "Settings & AI Configuration", desc: "Manage AI providers, API keys, and student profile preferences." }
  };

  const info = titles[tabId] || { title: "AI Study Assistant", desc: "" };
  document.getElementById("page-title").textContent = info.title;
  document.getElementById("page-desc").textContent = info.desc;

  // Refresh tab data
  if (tabId === "materials") loadMaterials();
  if (tabId === "quiz") loadQuizHistory();
  if (tabId === "flashcards") loadFlashcardDecks();
  if (tabId === "planner") loadPlans();
  if (tabId === "analytics") loadAnalytics();
  if (tabId === "settings") loadSettings();
}

// Initial Boot
document.addEventListener("DOMContentLoaded", async () => {
  // Navigation binding
  document.querySelectorAll(".nav-item").forEach(item => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      const tab = item.dataset.tab;
      if (tab) switchTab(tab);
    });
  });

  // Theme toggle
  const themeToggle = document.getElementById("theme-toggle");
  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme") || "dark";
      const next = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      themeToggle.textContent = next === "dark" ? "🌙" : "☀️";
    });
  }

  // Load profile & initial data
  await loadProfile();
  await loadMaterials();
  initChat();
  initMaterials();
  initQuiz();
  if (typeof initFlashcards === "function") initFlashcards();
  initPlanner();
  initSettings();

  // Load chat conversations
  await loadConversations();
});

async function loadProfile() {
  try {
    const profile = await API.get("/api/student/profile");
    State.student = profile;
    const nameEl = document.getElementById("profile-display-name");
    const avatarEl = document.getElementById("profile-display-avatar");
    const statusEl = document.getElementById("profile-display-status");
    if (nameEl) nameEl.textContent = profile.name;
    if (avatarEl) avatarEl.textContent = profile.name.charAt(0);
    if (statusEl) statusEl.textContent = profile.academic_level;
  } catch (err) {
    console.error("Failed to load student profile", err);
  }
}

async function loadConversations() {
  try {
    const convs = await API.get("/api/tutor/conversations");
    if (convs && convs.length > 0) {
      State.activeConversationId = convs[0].id;
      loadMessages(convs[0].id);
    } else {
      // Create initial conversation
      const newConv = await API.post("/api/tutor/conversations", {
        title: "Renewable Energy Study Session",
        persona: "tutor"
      });
      State.activeConversationId = newConv.id;
      // Show default greeting
      renderWelcomeMessage();
    }
  } catch (err) {
    console.error("Failed to load conversations", err);
  }
}
