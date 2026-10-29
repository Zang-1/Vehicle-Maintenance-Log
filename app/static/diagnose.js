// S10 Chẩn đoán AI (FR-18 → FR-20): the browser calls only POST /diagnose on our own server.

const symptom = document.getElementById("symptom");
const button = document.getElementById("diagnose-btn");
const result = document.getElementById("result");
const help = document.getElementById("symptom-help");

symptom.addEventListener("input", () => {
  document.getElementById("symptom-count").textContent = `${symptom.value.length}/1000`;
});

function showResult(className, ...children) {
  result.className = `result ${className}`;
  result.replaceChildren(...children);
  result.hidden = false;
}

button.addEventListener("click", async () => {
  const text = symptom.value.trim();
  if (text.length < 10) {
    help.textContent = "Mô tả cần ít nhất 10 ký tự.";
    help.className = "text-bad";
    symptom.focus();
    return;
  }
  help.textContent = "Từ 10 đến 1000 ký tự";
  help.className = "muted";

  button.disabled = true; // one click = one request
  button.textContent = "Đang phân tích…";
  showResult("result-wait", "AI đang phân tích, thường mất vài giây…");
  try {
    const data = await fetchJson("/diagnose", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symptom_text: text }),
      signal: AbortSignal.timeout(60000), // never a spinner forever (3 tries × 15 s + waits)
    });
    showResult("result-ok", el("p", "result-title", "Kết quả chẩn đoán"), el("p", "result-text", data.suggestion));
  } catch (error) {
    // The symptom stays in the box (FR-20); only the message changes.
    const message = error.status === 422 ? "Mô tả cần từ 10 đến 1000 ký tự." : error.name === "TimeoutError"
      ? "AI phản hồi quá lâu, vui lòng thử lại." : error.message;
    showResult("result-bad", message);
  } finally {
    button.disabled = false;
    button.textContent = "Chẩn đoán";
  }
});
