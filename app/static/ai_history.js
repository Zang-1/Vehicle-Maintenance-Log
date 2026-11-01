// S11 Các lần đã hỏi AI (FR-21): GET /api/diagnoses, newest first, filtered on the client.

const URGENCY_BADGE = {
  LOW: ["Mức thấp", "badge-ok"],
  MEDIUM: ["Mức trung bình", "badge-warn"],
  HIGH: ["Mức cao", "badge-bad"],
};

// Same words the user saw on the diagnosis page when the call failed (BR-10).
const ERROR_TEXT = {
  NO_KEY: "Lúc đó tính năng AI chưa được cấu hình.",
  RATE_LIMITED: "Lúc đó đã hết lượt hỏi AI miễn phí.",
  TIMEOUT: "Lúc đó AI phản hồi quá lâu.",
  UPSTREAM_ERROR: "Lúc đó không nhận được kết quả từ AI.",
};

let diagnoses = [];
let filter = "all";

function formatTime(iso) {
  const d = new Date(iso);
  return `${formatDate(iso)} lúc ${d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })}`;
}

function badgeFor(d) {
  if (d.status === "FAILED") return el("span", "badge badge-bad", "Bị lỗi");
  const [label, cls] = URGENCY_BADGE[d.urgency_level] || ["Có kết quả", "badge-neutral"];
  return el("span", `badge ${cls}`, label);
}

function bodyFor(d) {
  if (d.status === "FAILED") {
    return el("div", "history-body", el("p", "text-bad", ERROR_TEXT[d.error_code] || ERROR_TEXT.UPSTREAM_ERROR));
  }
  // The urgency is already in the badge; drop the prompt's last line from the text.
  const text = (d.ai_suggestion || "").replace(/^\s*(?:mức khẩn cấp|urgency)\s*:.*$/im, "").trim();
  return el("div", "history-body", el("p", "result-text", text), el("p", "row-sub", `Model: ${d.model || "không rõ"}`));
}

function render() {
  const list = document.getElementById("history-list");
  const shown = diagnoses.filter((d) => filter === "all" || d.status === filter);
  if (!shown.length) {
    list.replaceChildren(
      el("div", "card empty", el("p", "empty-title", diagnoses.length ? "Không có lần nào khớp bộ lọc" : "Bạn chưa hỏi AI lần nào"), el("p", "muted", "Mô tả triệu chứng của xe ở trang Hỏi AI về xe.")),
    );
    return;
  }
  list.replaceChildren(
    ...shown.map((d) => {
      const item = el("details", "card history-item");
      item.append(
        el("summary", "", badgeFor(d), el("div", "history-main", el("p", "history-symptom", d.symptom_text), el("p", "row-sub", formatTime(d.created_at))), icon("chevron-down")),
        bodyFor(d),
      );
      return item;
    }),
  );
}

for (const chip of document.querySelectorAll("[data-filter]")) {
  chip.addEventListener("click", () => {
    filter = chip.dataset.filter;
    document.querySelectorAll("[data-filter]").forEach((c) => c.setAttribute("aria-pressed", String(c === chip)));
    render();
  });
}

async function loadHistory() {
  try {
    diagnoses = await fetchJson("/api/diagnoses");
    render();
  } catch (error) {
    showError(error.message);
    document.getElementById("history-list").replaceChildren(el("p", "muted", "Không tải được lịch sử."));
  }
}

loadHistory();
