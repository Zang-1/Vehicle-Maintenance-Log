// S01 Dashboard (FR-16): one call to GET /api/stats/dashboard, then fill the cards.

// "quá 2 ngày", "còn 5 ngày · còn 1.150 km": for an overdue reminder only the overdue part is shown.
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

function renderAttention(reminders) {
  const list = document.getElementById("attention-list");
  if (!reminders.length) {
    list.replaceChildren(el("li", "row muted", "Không có nhắc lịch nào cần chú ý."));
    return;
  }
  list.replaceChildren(
    ...reminders.map((r) =>
      el(
        "li",
        "row",
        el("div", "", el("p", "row-title", r.vehicle_name), el("p", "row-sub", `${r.service_type_name} · ${reminderDetail(r)}`)),
        statusBadge(r.status),
      ),
    ),
  );
}

function renderRecent(records) {
  const list = document.getElementById("recent-list");
  if (!records.length) {
    list.replaceChildren(el("li", "row muted", "Chưa có lần bảo dưỡng nào."));
    return;
  }
  list.replaceChildren(
    ...records.map((r) =>
      el(
        "li",
        "row",
        el(
          "div",
          "",
          el("p", "row-title", `${formatDate(r.service_date)} · ${r.vehicle_name}`),
          el("p", "row-sub", r.items_summary || `${r.item_count} hạng mục`),
        ),
        el("span", "row-amount", formatMoney(r.total_cost)),
      ),
    ),
  );
}

async function loadDashboard() {
  try {
    const data = await fetchJson("/api/stats/dashboard");
    const reminders = data.attention_reminders;
    document.getElementById("stat-vehicles").textContent = data.vehicle_count;
    document.getElementById("stat-overdue").textContent = reminders.filter((r) => r.status === "OVERDUE").length;
    document.getElementById("stat-due-soon").textContent = reminders.filter((r) => r.status === "DUE_SOON").length;
    document.getElementById("stat-cost").textContent = formatMoney(data.cost_this_month);
    renderAttention(reminders);
    renderRecent(data.recent_records);
  } catch (error) {
    showError(error.message);
    for (const id of ["attention-list", "recent-list"]) {
      document.getElementById(id).replaceChildren(el("li", "row muted", "Không tải được dữ liệu."));
    }
  }
}

loadDashboard();
