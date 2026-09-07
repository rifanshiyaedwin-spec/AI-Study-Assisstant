function initMaterials() {
  const dropzone = document.getElementById("material-dropzone");
  const fileInput = document.getElementById("material-file-input");
  const loadSampleBtn = document.getElementById("load-sample-btn");

  if (dropzone && fileInput) {
    dropzone.addEventListener("click", () => fileInput.click());

    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });

    dropzone.addEventListener("dragleave", () => {
      dropzone.classList.remove("dragover");
    });

    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      if (e.dataTransfer.files.length > 0) {
        handleFileUpload(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener("change", () => {
      if (fileInput.files.length > 0) {
        handleFileUpload(fileInput.files[0]);
      }
    });
  }

  if (loadSampleBtn) {
    loadSampleBtn.addEventListener("click", async () => {
      loadSampleBtn.disabled = true;
      loadSampleBtn.textContent = "Loading & Indexing...";
      try {
        const res = await API.post("/api/materials/load-sample", {});
        showToast(res.message || "Sample loaded successfully!", "success");
        await loadMaterials();
        switchTab("materials");
      } catch (err) {
        showToast("Error loading sample material", "error");
      } finally {
        loadSampleBtn.disabled = false;
        loadSampleBtn.textContent = "🚀 Load Sample: Renewable Energy Technologies";
      }
    });
  }
}

async function handleFileUpload(file) {
  const subjectInput = document.getElementById("material-subject-input");
  const subject = subjectInput ? subjectInput.value.trim() || "General" : "General";

  const formData = new FormData();
  formData.append("file", file);
  formData.append("subject", subject);

  showToast(`Uploading and extracting: ${file.name}...`, "info");

  try {
    const res = await API.upload("/api/materials/upload", formData);
    showToast(`Processed ${res.filename} (${res.pages} pages, ${res.chunks} chunks)`, "success");
    await loadMaterials();
  } catch (err) {
    showToast("Error uploading material: " + err.message, "error");
  }
}

async function loadMaterials() {
  const container = document.getElementById("materials-list");
  const chatSelect = document.getElementById("chat-material-filter");
  const quizSelect = document.getElementById("quiz-material-select");
  if (!container) return;

  try {
    const list = await API.get("/api/materials");
    State.materials = list;

    // Update filter dropdowns
    if (chatSelect) {
      chatSelect.innerHTML = `<option value="">All Course Materials</option>` + 
        list.map(m => `<option value="${m.id}">${m.display_name || m.filename}</option>`).join("");
    }
    if (quizSelect) {
      quizSelect.innerHTML = `<option value="">Auto-select from best match</option>` + 
        list.map(m => `<option value="${m.id}">${m.display_name || m.filename}</option>`).join("");
    }

    if (list.length === 0) {
      container.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 40px; background: var(--bg-card); border-radius: var(--card-radius); border: 1px dashed var(--border-color);">
          <div style="font-size: 32px; margin-bottom: 12px;">📂</div>
          <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 6px;">No Course Materials Uploaded Yet</h3>
          <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 16px;">
            Upload your lecture notes, textbook PDFs, or click below to load the bundled sample.
          </p>
          <button class="btn btn-primary" onclick="document.getElementById('load-sample-btn').click()">
            🚀 Load Sample: Renewable Energy Technologies
          </button>
        </div>
      `;
      return;
    }

    container.innerHTML = list.map(m => `
      <div class="card" style="display: flex; flex-direction: column; justify-content: space-between;">
        <div>
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
            <span style="font-size: 24px;">${m.file_type === 'pdf' ? '📄' : '📝'}</span>
            <span class="badge" style="background: rgba(59, 130, 246, 0.15); color: var(--accent-secondary); font-size: 11px; padding: 3px 8px; border-radius: 6px;">
              ${m.subject}
            </span>
          </div>
          <h3 style="font-size: 15px; font-weight: 700; margin-bottom: 6px; line-height: 1.4;">${m.display_name || m.filename}</h3>
          <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">
            File: <code>${m.filename}</code>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; font-size: 11.5px; background: var(--bg-input); padding: 10px; border-radius: 8px; margin-bottom: 14px;">
            <div><span style="color: var(--text-muted);">Pages:</span> <strong>${m.total_pages}</strong></div>
            <div><span style="color: var(--text-muted);">Chunks:</span> <strong>${m.chunk_count}</strong></div>
            <div><span style="color: var(--text-muted);">Words:</span> <strong>${m.total_words}</strong></div>
          </div>
        </div>
        <div style="display: flex; flex-wrap: wrap; gap: 6px; border-top: 1px solid var(--border-color); padding-top: 12px;">
          <button class="btn btn-secondary btn-sm" onclick="askAboutMaterial('${m.display_name || m.filename}', ${m.id})">
            💬 Ask Tutor
          </button>
          <button class="btn btn-secondary btn-sm" onclick="inspectChunks(${m.id}, '${(m.display_name || m.filename).replace(/'/g, "\\'")}')">
            🔍 Chunks
          </button>
          <button class="btn btn-secondary btn-sm" onclick="generateCheatsheet('${(m.display_name || m.filename).replace(/'/g, "\\'")}', ${m.id})">
            📐 Cheatsheet
          </button>
          <button class="btn btn-secondary btn-sm" style="color: var(--danger); margin-left: auto;" onclick="deleteMaterial(${m.id})">
            🗑
          </button>
        </div>
      </div>
    `).join("");

  } catch (err) {
    console.error("Failed to load materials", err);
  }
}

function askAboutMaterial(title, materialId) {
  switchTab("chat");
  const filter = document.getElementById("chat-material-filter");
  if (filter) filter.value = materialId;
  sendMessage(`Give me an overview of the key concepts covered in "${title}".`);
}

async function deleteMaterial(id) {
  if (!confirm("Are you sure you want to delete this course material and its vector index?")) return;
  try {
    await API.delete(`/api/materials/${id}`);
    showToast("Material removed", "info");
    await loadMaterials();
  } catch (err) {
    showToast("Failed to delete material", "error");
  }
}

async function inspectChunks(materialId, title) {
  const modal = document.getElementById("chunks-modal");
  const modalTitle = document.getElementById("chunks-modal-title");
  const modalBody = document.getElementById("chunks-modal-body");
  if (!modal || !modalBody) return;

  if (modalTitle) modalTitle.textContent = `Chunk Explorer: ${title}`;
  modalBody.innerHTML = `<div style="text-align: center; padding: 20px;">Loading indexed chunks...</div>`;
  modal.classList.add("show");

  try {
    const chunks = await API.get(`/api/materials/${materialId}/chunks`);
    modalBody.innerHTML = `
      <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 16px;">
        Total Indexed Chunks: <strong>${chunks.length}</strong> (Page numbers, headings, and character tokens)
      </div>
      <div style="display: flex; flex-direction: column; gap: 10px; max-height: 60vh; overflow-y: auto;">
        ${chunks.map((c, i) => `
          <div style="background: var(--bg-input); padding: 12px 14px; border-radius: 8px; border-left: 3px solid var(--accent-primary);">
            <div style="display: flex; justify-content: space-between; font-size: 11.5px; color: var(--text-muted); margin-bottom: 6px;">
              <span><strong>Chunk #${c.chunk_index + 1}</strong> • ${c.heading || 'General'}</span>
              <span>Page ${c.page_number} • ${c.token_count} words</span>
            </div>
            <p style="font-size: 13px; line-height: 1.5; color: var(--text-primary); font-family: inherit;">
              ${c.content}
            </p>
          </div>
        `).join("")}
      </div>
    `;
  } catch (err) {
    modalBody.innerHTML = `<div style="color: var(--danger);">Failed to load chunks: ${err.message}</div>`;
  }
}

async function generateCheatsheet(title, materialId) {
  const modal = document.getElementById("cheatsheet-modal");
  const modalTitle = document.getElementById("cheatsheet-modal-title");
  const modalBody = document.getElementById("cheatsheet-modal-body");
  if (!modal || !modalBody) return;

  if (modalTitle) modalTitle.textContent = `⚡ AI Study Cheatsheet: ${title}`;
  modalBody.innerHTML = `<div style="text-align: center; padding: 30px;">Synthesizing high-yield equations & concept review...</div>`;
  modal.classList.add("show");

  try {
    const res = await API.post("/api/tools/cheatsheet", {
      topic: title,
      material_id: materialId
    });

    const formattedHtml = typeof marked !== "undefined" ? marked.parse(res.content) : res.content.replace(/\n/g, '<br>');
    modalBody.innerHTML = `
      <div style="display: flex; justify-content: flex-end; gap: 8px; margin-bottom: 12px;">
        <button class="btn btn-secondary btn-sm" onclick="navigator.clipboard.writeText(\`${res.content.replace(/`/g, '\\`').replace(/\\/g, '\\\\')}\`); showToast('Cheatsheet copied to clipboard!', 'success')">
          📋 Copy Markdown
        </button>
      </div>
      <div style="background: var(--bg-input); padding: 20px; border-radius: 10px; border: 1px solid var(--border-color); font-size: 13.5px; line-height: 1.6;">
        ${formattedHtml}
      </div>
    `;
  } catch (err) {
    modalBody.innerHTML = `<div style="color: var(--danger);">Failed to generate cheatsheet: ${err.message}</div>`;
  }
}
