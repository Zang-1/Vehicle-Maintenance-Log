// Shared helpers for every page (doc 07: app.js). Page scripts call fetchJson, el, icon and showError.

const moneyFormat = new Intl.NumberFormat("vi-VN");

function formatMoney(value) {
  return moneyFormat.format(Number(value)) + " đ"; // the API sends Decimal as a string
}

function formatNumber(value) {
  return moneyFormat.format(value);
}

function formatDate(isoDate) {
  const [year, month, day] = isoDate.slice(0, 10).split("-");
  return `${day}/${month}/${year}`;
}

// "hôm nay", "3 ngày trước", "2 tháng trước": reads faster than a date for recent events.
function formatAgo(isoDate) {
  const days = Math.round((Date.now() - new Date(isoDate.slice(0, 10) + "T00:00:00")) / 864e5);
  if (days <= 0) return "hôm nay";
  return days < 60 ? `${days} ngày trước` : `${Math.round(days / 30)} tháng trước`;
}

// Build DOM nodes with textContent only, never innerHTML: data from the API is never parsed as HTML.
function el(tag, className, ...children) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  for (const child of children) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : String(child));
  }
  return node;
}

const SVG_NS = "http://www.w3.org/2000/svg";

// An icon from the sprite in base.html, e.g. icon("car").
function icon(name, className = "ic") {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("class", className);
  svg.setAttribute("aria-hidden", "true");
  const use = document.createElementNS(SVG_NS, "use");
  use.setAttribute("href", `#i-${name}`);
  svg.append(use);
  return svg;
}

// A vehicle drawing from the sprite; the body takes the colour of its vehicle type.
const VEHICLE_DRAWING = { CAR: ["d-car", "#E5E7EB"], MOTORBIKE: ["d-scooter", "#F97316"], OTHER: ["d-scooter", "#94A3B8"] };

function vehicleDrawing(vehicleType, width) {
  const [symbol, colour] = VEHICLE_DRAWING[vehicleType] || VEHICLE_DRAWING.OTHER;
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("class", "drawing");
  svg.setAttribute("viewBox", "0 0 160 96");
  svg.setAttribute("width", width);
  svg.setAttribute("height", Math.round(width * 0.6));
  svg.setAttribute("aria-hidden", "true");
  svg.style.color = colour;
  const use = document.createElementNS(SVG_NS, "use");
  use.setAttribute("href", `#${symbol}`);
  svg.append(use);
  return svg;
}

// Service gauge: how much of the interval is used (0..1), drawn like the needle ring on a car dashboard.
function gauge(progress, status) {
  const tone = { OVERDUE: "bad", DUE_SOON: "warn", OK: "ok" }[status] || "neutral";
  const size = 64;
  const radius = 27;
  const circumference = 2 * Math.PI * radius;
  const used = status === "OVERDUE" ? 1 : Math.max(0, Math.min(1, progress));
  const box = el("div", `gauge gauge-${tone}`);
  box.setAttribute("role", "img");
  box.setAttribute("aria-label", `Đã dùng ${Math.round(used * 100)}% chu kỳ bảo dưỡng`);
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${size} ${size}`);
  for (const [cls, offset] of [["track", 0], ["value", circumference * (1 - used)]]) {
    const circle = document.createElementNS(SVG_NS, "circle");
    circle.setAttribute("class", cls);
    circle.setAttribute("cx", size / 2);
    circle.setAttribute("cy", size / 2);
    circle.setAttribute("r", radius);
    if (cls === "value") {
      circle.setAttribute("stroke-dasharray", circumference.toFixed(1));
      circle.setAttribute("stroke-dashoffset", offset.toFixed(1));
    }
    svg.append(circle);
  }
  box.append(svg, el("b", "", status === "OVERDUE" ? "!" : `${Math.round(used * 100)}%`));
  return box;
}

function showError(message) {
  const box = document.getElementById("error");
  box.textContent = message;
  box.hidden = false;
}

let toastTimer;
function showToast(message) {
  const box = document.getElementById("toast");
  box.replaceChildren(icon("check-circle"), el("span", "", message));
  box.classList.add("on");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => box.classList.remove("on"), 2600);
}

// Business errors come back as ErrorOut {error_code, message}; show that message as is.
async function fetchJson(url, options) {
  let response;
  try {
    response = await fetch(url, options);
  } catch {
    throw new Error("Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại.");
  }
  let body = null;
  try {
    body = await response.json();
  } catch {
    // not JSON (e.g. a proxy error page): keep body null
  }
  if (response.status === 401 && body && body.error_code === "NOT_SIGNED_IN") {
    // the session ended (signed out in another tab, or 30 days passed): sign in again, then come back here
    location.href = `/dang-nhap?next=${encodeURIComponent(location.pathname + location.search)}`;
  }
  if (!response.ok) {
    const error = new Error(body && body.message ? body.message : `Máy chủ báo lỗi ${response.status}.`);
    error.status = response.status;
    error.body = body;
    throw error;
  }
  return body;
}

const REMINDER_STATUS = {
  OVERDUE: ["Quá hạn", "badge-bad"],
  DUE_SOON: ["Sắp đến hạn", "badge-warn"],
  OK: ["Còn hạn", "badge-ok"],
};

function statusBadge(status) {
  const [label, className] = REMINDER_STATUS[status];
  return el("span", `badge ${className}`, label);
}

// "quá 3 ngày", "còn 5 ngày · còn 1.150 km": for an overdue reminder only the overdue part is shown.
function reminderDetail(reminder) {
  const parts = [];
  if (reminder.days_left !== null) {
    const days = reminder.days_left;
    parts.push(days < 0 ? `quá ${-days} ngày` : days === 0 ? "đến hạn hôm nay" : `còn ${days} ngày`);
  }
  if (reminder.km_left !== null) {
    const km = reminder.km_left;
    parts.push(km < 0 ? `quá ${formatNumber(-km)} km` : km === 0 ? "đến hạn theo km" : `còn ${formatNumber(km)} km`);
  }
  const due = parts.filter((part) => !part.startsWith("còn"));
  return (reminder.status === "OVERDUE" && due.length ? due : parts).join(" · ");
}

// Theme toggle (base.html sets the first value before paint) and the help dialog, on every page.
document.querySelectorAll("[data-theme-toggle]").forEach((button) =>
  button.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("vml-theme", next);
    } catch {
      // private mode: the choice lasts until the page closes
    }
  }),
);

document.querySelectorAll("[data-logout]").forEach((button) =>
  button.addEventListener("click", async () => {
    try {
      await fetchJson("/api/auth/logout", { method: "POST" });
    } finally {
      location.href = "/dang-nhap";
    }
  }),
);

document.querySelectorAll("[data-open-help]").forEach((button) =>
  button.addEventListener("click", () => document.getElementById("help-dialog").showModal()),
);

// Clicking the dimmed backdrop closes any dialog, like pressing Esc.
document.querySelectorAll("dialog").forEach((dialog) =>
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  }),
);
