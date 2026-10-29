// S10 Chẩn đoán AI (FR-18 → FR-20): the browser calls only POST /diagnose on our own server.

const symptom = document.getElementById("symptom");
const button = document.getElementById("diagnose-btn");
const help = document.getElementById("symptom-help");
const STATES = ["state-empty", "state-wait", "state-ok", "state-bad"];

// The prompt (app/ai.py) asks for a last line "Mức khẩn cấp: LOW|MEDIUM|HIGH".
const URGENCY = {
  LOW: ["Thấp — có thể theo dõi thêm", "urgency-low", 1],
  MEDIUM: ["Trung bình — nên xử lý trong tuần", "urgency-medium", 2],
  HIGH: ["Cao — cần kiểm tra ngay", "urgency-high", 3],
};
const URGENCY_LINE = /^\s*(?:mức khẩn cấp|urgency)\s*:\s*\**\s*(LOW|MEDIUM|HIGH)\b.*$/im;

function show(id) {
  for (const state of STATES) document.getElementById(state).hidden = state !== id;
  // On a phone the result card sits under the form: bring it into view.
  document.getElementById(id).closest(".card").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function updateCount() {
  document.getElementById("symptom-count").textContent = `${symptom.value.length}/1000`;
}

function setHelp(message, isError) {
  help.textContent = message;
  help.className = isError ? "text-bad" : "muted";
}

function showSuggestion(text) {
  const match = text.match(URGENCY_LINE);
  const box = document.getElementById("urgency");
  if (match) {
    const [label, className, level] = URGENCY[match[1].toUpperCase()];
    box.className = `urgency ${className}`;
    document.getElementById("urgency-text").textContent = label;
    box.querySelectorAll(".meter i").forEach((bar, i) => bar.classList.toggle("on", i < level));
  }
  box.hidden = !match;
  document.getElementById("suggestion").textContent = (match ? text.replace(match[0], "") : text).trim();
  show("state-ok");
}

symptom.addEventListener("input", () => {
  updateCount();
  if (symptom.value.trim().length >= 10) setHelp("Từ 10 đến 1000 ký tự", false);
});

for (const chip of document.querySelectorAll("[data-example]")) {
  chip.addEventListener("click", () => {
    symptom.value = chip.dataset.example;
    updateCount();
    setHelp("Từ 10 đến 1000 ký tự", false);
    symptom.focus();
  });
}

button.addEventListener("click", async () => {
  const text = symptom.value.trim();
  if (text.length < 10) {
    setHelp("Mô tả cần ít nhất 10 ký tự.", true);
    symptom.focus();
    return;
  }

  button.disabled = true; // one click = one request
  button.textContent = "Đang phân tích…";
  show("state-wait");
  try {
    const data = await fetchJson("/diagnose", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symptom_text: text }),
      signal: AbortSignal.timeout(60000), // never a spinner forever (3 tries × 15 s + waits)
    });
    showSuggestion(data.suggestion);
  } catch (error) {
    // The symptom stays in the box (FR-20); only the message changes.
    document.getElementById("error-text").textContent =
      error.status === 422 ? "Mô tả cần từ 10 đến 1000 ký tự."
        : error.name === "TimeoutError" ? "AI phản hồi quá lâu, vui lòng thử lại."
          : error.message;
    show("state-bad");
  } finally {
    button.disabled = false;
    button.textContent = "Chẩn đoán";
  }
});
