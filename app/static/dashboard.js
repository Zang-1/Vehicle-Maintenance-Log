// S01 Trang chủ (FR-16): one call to GET /api/stats/dashboard, then fill the blocks.

// Link to the screen where a done service is logged (Lâm, M3), with the vehicle and service prefilled.
function logServiceUrl(reminder) {
  return `/bao-duong/moi?xe=${reminder.vehicle_id}&loai=${reminder.service_type_id}`;
}

function renderStatus(reminders) {
  const status = document.getElementById("dash-status");
  const bad = reminders.length > 0;
  status.className = `dash-status ${bad ? "bad" : "ok"}`;
  status.replaceChildren(
    icon(bad ? "alert" : "check-circle"),
    el("span", "", bad ? `Có ${reminders.length} việc cần làm cho xe của bạn` : "Xe của bạn đều ổn"),
  );
}

function renderNext(reminders, vehicles) {
  const card = document.getElementById("next-card");
  const first = reminders[0];
  card.hidden = !first;
  if (!first) return;
  const vehicle = vehicles.find((v) => v.id === first.vehicle_id);
  document.getElementById("next-thumb").replaceChildren(vehicleDrawing(vehicle ? vehicle.vehicle_type : "OTHER", 110));
  document.getElementById("next-title").textContent = first.service_type_name;
  const tone = first.status === "OVERDUE" ? "text-bad" : "text-warn";
  document.getElementById("next-detail").replaceChildren(`${first.vehicle_name} · `, el("span", tone, reminderDetail(first)));
  document.getElementById("next-action").href = logServiceUrl(first);
}

function renderTiles(data) {
  const todo = document.getElementById("stat-todo");
  todo.textContent = data.attention_reminders.length;
  todo.className = `tile-value ${data.attention_reminders.length ? "text-bad" : "text-ok"}`;
  document.getElementById("stat-cost-label").textContent = `Chi phí năm ${new Date().getFullYear()}`;
  document.getElementById("stat-cost").textContent = formatMoney(data.cost_this_year);

  const last = data.recent_records[0];
  document.getElementById("stat-last").textContent = last ? formatAgo(last.service_date) : "Chưa có";
  document.getElementById("stat-last-more").textContent = last ? `${last.vehicle_name} · Xem phiếu` : "Ghi lần đầu tiên";
  document.getElementById("tile-last").href = last ? `/bao-duong/${last.record_id}` : "/bao-duong/moi";
}

function vehicleLine(vehicle) {
  const r = vehicle.reminder;
  if (!r) return el("span", "row-sub", "Chưa có nhắc bảo dưỡng");
  if (r.status === "OK") {
    const when = r.next_due_date ? formatDate(r.next_due_date) : `${formatNumber(r.next_due_odometer)} km`;
    return el("span", "row-sub", `Lần tới: ${r.service_type_name.toLowerCase()}, ${when}`);
  }
  const tone = r.status === "OVERDUE" ? "text-bad" : "text-warn";
  return el("span", `row-sub ${tone}`, `${r.service_type_name} · ${reminderDetail(r)}`);
}

function renderVehicles(vehicles) {
  const list = document.getElementById("vehicle-list");
  const cards = vehicles.map((v) => {
    const r = v.reminder;
    const card = el(
      "a",
      "card vehicle-card",
      el("div", "thumb", vehicleDrawing(v.vehicle_type, 110)),
      el(
        "div",
        "vehicle-main",
        el("span", "vehicle-name", v.name), // no badge: the gauge and the coloured line already say it
        el("span", "row-sub", `${v.license_plate ? v.license_plate + " · " : ""}${formatNumber(v.current_odometer)} km`),
        vehicleLine(v),
      ),
      r ? gauge(r.progress, r.status) : null,
    );
    card.href = `/xe/${v.id}`;
    return card;
  });
  const add = el("a", "card vehicle-card vehicle-add", icon("plus"), "Thêm xe mới");
  add.href = "/xe";
  list.replaceChildren(...cards, add);
}

function renderTodo(reminders) {
  const list = document.getElementById("todo-list");
  if (!reminders.length) {
    list.replaceChildren(el("li", "row muted", "Không có việc nào cần làm. Xe của bạn đều ổn."));
    return;
  }
  list.replaceChildren(
    ...reminders.map((r) => {
      const done = el("a", "btn btn-primary btn-sm", icon("check"), "Đã làm");
      done.href = logServiceUrl(r);
      const tone = r.status === "OVERDUE" ? "text-bad" : "text-warn";
      return el(
        "li",
        "row",
        el("div", "row-main", el("p", "row-title", r.service_type_name), el("p", "row-sub", `${r.vehicle_name} · `, el("span", tone, reminderDetail(r)))),
        done,
      );
    }),
  );
}

document.getElementById("today").textContent = new Date().toLocaleDateString("vi-VN", {
  weekday: "long",
  day: "numeric",
  month: "numeric",
  year: "numeric",
});
document.getElementById("tile-todo").addEventListener("click", () => document.getElementById("todo-dialog").showModal());

async function loadDashboard() {
  try {
    const data = await fetchJson("/api/stats/dashboard");
    renderStatus(data.attention_reminders);
    renderNext(data.attention_reminders, data.vehicles);
    renderTiles(data);
    renderVehicles(data.vehicles);
    renderTodo(data.attention_reminders);
  } catch (error) {
    showError(error.message);
    document.getElementById("dash-status").replaceChildren(icon("alert"), el("span", "", "Không tải được dữ liệu"));
    document.getElementById("vehicle-list").replaceChildren(el("p", "muted", "Không tải được danh sách xe."));
  }
}

loadDashboard();
