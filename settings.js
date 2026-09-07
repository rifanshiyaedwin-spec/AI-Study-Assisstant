function initSettings() {
  const profileForm = document.getElementById("profile-settings-form");
  const aiForm = document.getElementById("ai-settings-form");

  if (profileForm) {
    profileForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const name = document.getElementById("setting-name").value;
      const level = document.getElementById("setting-level").value;
      const goal = document.getElementById("setting-goal").value;
      const style = document.getElementById("setting-style").value;
      const hours = parseInt(document.getElementById("setting-hours").value);

      try {
        const updated = await API.put("/api/student/profile", {
          name, academic_level: level, target_goal: goal,
          learning_style: style, study_hours_per_week: hours
        });
        State.student = updated;
        await loadProfile();
        showToast("Student profile updated successfully!", "success");
      } catch (err) {
        showToast("Failed to update profile", "error");
      }
    });
  }

  if (aiForm) {
    aiForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const provider = document.getElementById("setting-llm-provider").value;
      const geminiKey = document.getElementById("setting-gemini-key").value;
      const openaiKey = document.getElementById("setting-openai-key").value;
      const model = document.getElementById("setting-model-name").value;

      try {
        await API.post("/api/settings", {
          settings: {
            llm_provider: provider,
            gemini_api_key: geminiKey,
            openai_api_key: openaiKey,
            model_name: model
          }
        });
        showToast("AI configuration saved successfully!", "success");
      } catch (err) {
        showToast("Failed to save settings", "error");
      }
    });
  }

  // Handle provider dropdown switch to show/hide relevant key fields
  const providerSelect = document.getElementById("setting-llm-provider");
  if (providerSelect) {
    providerSelect.addEventListener("change", () => {
      toggleProviderFields(providerSelect.value);
    });
  }
}

function toggleProviderFields(provider) {
  const geminiBox = document.getElementById("gemini-key-group");
  const openaiBox = document.getElementById("openai-key-group");
  if (geminiBox) geminiBox.style.display = (provider === "gemini" ? "block" : "none");
  if (openaiBox) openaiBox.style.display = (provider === "openai" ? "block" : "none");
}

async function loadSettings() {
  try {
    const profile = await API.get("/api/student/profile");
    if (document.getElementById("setting-name")) document.getElementById("setting-name").value = profile.name || "";
    if (document.getElementById("setting-level")) document.getElementById("setting-level").value = profile.academic_level || "Undergraduate";
    if (document.getElementById("setting-goal")) document.getElementById("setting-goal").value = profile.target_goal || "";
    if (document.getElementById("setting-style")) document.getElementById("setting-style").value = profile.learning_style || "Socratic & Conceptual";
    if (document.getElementById("setting-hours")) document.getElementById("setting-hours").value = profile.study_hours_per_week || 10;

    const settings = await API.get("/api/settings");
    if (document.getElementById("setting-llm-provider")) {
      document.getElementById("setting-llm-provider").value = settings.llm_provider || "builtin";
      toggleProviderFields(settings.llm_provider || "builtin");
    }
    if (document.getElementById("setting-gemini-key")) document.getElementById("setting-gemini-key").value = settings.gemini_api_key || "";
    if (document.getElementById("setting-openai-key")) document.getElementById("setting-openai-key").value = settings.openai_api_key || "";
    if (document.getElementById("setting-model-name")) document.getElementById("setting-model-name").value = settings.model_name || "gemini-1.5-flash";

  } catch (err) {
    console.error("Failed to load settings", err);
  }
}
