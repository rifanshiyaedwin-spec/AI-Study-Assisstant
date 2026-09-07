// Pomodoro Focus Study Timer with Automatic Activity Logging
const Timer = {
  duration: 25 * 60, // 25 minutes
  timeLeft: 25 * 60,
  mode: "focus", // 'focus' or 'break'
  timerId: null,
  isRunning: false,

  init() {
    this.displayEl = document.getElementById("pomodoro-display");
    this.toggleBtn = document.getElementById("pomodoro-toggle");
    this.resetBtn = document.getElementById("pomodoro-reset");
    this.modeBadge = document.getElementById("pomodoro-mode-badge");

    if (!this.displayEl || !this.toggleBtn) return;

    this.toggleBtn.addEventListener("click", () => this.toggle());
    if (this.resetBtn) {
      this.resetBtn.addEventListener("click", () => this.reset());
    }

    this.updateDisplay();
  },

  toggle() {
    if (this.isRunning) {
      this.pause();
    } else {
      this.start();
    }
  },

  start() {
    if (this.isRunning) return;
    this.isRunning = true;
    this.toggleBtn.textContent = "⏸ Pause";
    this.toggleBtn.classList.remove("btn-primary");
    this.toggleBtn.classList.add("btn-secondary");

    this.timerId = setInterval(() => {
      this.tick();
    }, 1000);
  },

  pause() {
    if (!this.isRunning) return;
    this.isRunning = false;
    clearInterval(this.timerId);
    this.toggleBtn.textContent = "▶ Start";
    this.toggleBtn.classList.remove("btn-secondary");
    this.toggleBtn.classList.add("btn-primary");
  },

  reset() {
    this.pause();
    this.timeLeft = this.mode === "focus" ? 25 * 60 : 5 * 60;
    this.updateDisplay();
  },

  tick() {
    if (this.timeLeft > 0) {
      this.timeLeft--;
      this.updateDisplay();
    } else {
      this.complete();
    }
  },

  async complete() {
    this.pause();
    if (this.mode === "focus") {
      // Completed a 25-minute focus session!
      showToast("🎉 Pomodoro Completed! 25 minutes logged to your study record!", "success");
      try {
        await API.post("/api/study/log-timer", {
          duration_minutes: 25,
          description: "Completed 25-min Pomodoro Focus Session"
        });
      } catch (e) {
        console.error("Failed to log timer", e);
      }

      // Switch to break
      this.mode = "break";
      this.timeLeft = 5 * 60;
      if (this.modeBadge) {
        this.modeBadge.textContent = "REST BREAK (5m)";
        this.modeBadge.style.background = "rgba(16, 185, 129, 0.2)";
        this.modeBadge.style.color = "var(--success)";
      }
    } else {
      showToast("Break over! Ready for another focused study block?", "info");
      this.mode = "focus";
      this.timeLeft = 25 * 60;
      if (this.modeBadge) {
        this.modeBadge.textContent = "FOCUS MODE";
        this.modeBadge.style.background = "rgba(59, 130, 246, 0.2)";
        this.modeBadge.style.color = "var(--accent-secondary)";
      }
    }
    this.updateDisplay();
  },

  updateDisplay() {
    if (!this.displayEl) return;
    const mins = Math.floor(this.timeLeft / 60);
    const secs = this.timeLeft % 60;
    this.displayEl.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
};

document.addEventListener("DOMContentLoaded", () => {
  Timer.init();
});
