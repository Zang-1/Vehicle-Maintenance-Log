// Shared helpers for every page (doc 07: app.js). Page scripts call fetchJson and showError.

const moneyFormat = new Intl.NumberFormat("vi-VN");

function formatMoney(value) {
  return moneyFormat.format(Number(value)) + " đ"; // the API sends Decimal as a string
}

function formatNumber(value) {
  return moneyFormat.format(value);
}

function formatDate(isoDate) {
  const [year, month, day] = isoDate.split("-");
  return `${day}/${month}/${year}`;
}

// Build DOM nodes with textContent only, never innerHTML: data from the API is never parsed as HTML.
function el(tag, className, ...children) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  for (const child of children) {
    node.append(child instanceof Node ? child : String(child));
  }
  return node;
}

function showError(message) {
  const box = document.getElementById("error");
  box.textContent = message;
  box.hidden = false;
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
