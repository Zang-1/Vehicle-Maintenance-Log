// S04 Chi tiết xe, tab "Nhắc bảo dưỡng" (Lâm, M5, FR-13, FR-14).
// vehicle_detail.js calls window.renderVehicleReminders(container, vehicle) the first time the tab opens.
// After a pause, resume or delete this file fires "vml:reminders-changed" so the page header redraws its badge.
// The add and edit forms are Khoa's: /xe/{vehicle_id}/nhac-lich/moi and /nhac-lich/{reminder_id}/sua.
(function () {
  "use strict";

  const PROGRESS_TONE = { OVERDUE: "bad", DUE_SOON: "warn", OK: "ok" };

  let container = null;
  let vehicle = null;
  let pendingDelete = null;

  function linkButton(label, iconName, className, href) {
    const link = el("a", `btn ${className}`, icon(iconName), label);
    link.href = href;
    return link;
  }

  function button(label, iconName, className, handler) {
    const node = el("button", `btn ${className}`, iconName ? icon(iconName) : null, label);
    node.type = "button";
    node.addEventListener("click", handler);
    return node;
  }

  // "Mỗi 4.000 km hoặc 6 tháng"
  function intervalText(r) {
    const parts = [];
    if (r.interval_km) parts.push(`${formatNumber(r.interval_km)} km`);
    if (r.interval_months) parts.push(`${r.interval_months} tháng`);
    return `Mỗi ${parts.join(" hoặc ")}`;
  }

  // "Đến hạn 20/02/2027 hoặc ở 16.500 km", whichever comes first
  function dueText(r) {
    const parts = [];
    if (r.next_due_date) parts.push(formatDate(r.next_due_date));
    if (r.next_due_odometer !== null) parts.push(`ở ${formatNumber(r.next_due_odometer)} km`);
    return `Đến hạn ${parts.join(" hoặc ")}`;
  }

  function progressBar(r) {
    const percent = Math.round(r.progress * 100);
    const bar = el("div", `progress ${r.is_active ? PROGRESS_TONE[r.status] : ""}`, el("span"));
    bar.firstChild.style.width = `${percent}%`;
    bar.setAttribute("role", "progressbar");
    bar.setAttribute("aria-valuemin", "0");
    bar.setAttribute("aria-valuemax", "100");
    bar.setAttribute("aria-valuenow", String(percent));
    bar.setAttribute("aria-label", `Đã dùng ${percent}% chu kỳ ${r.service_type_name}`);
    return bar;
  }

  function reminderCard(r) {
    const badge = r.is_active ? statusBadge(r.status) : el("span", "badge badge-neutral", "Tạm dừng");
    const lastDone = `Tính từ ${formatDate(r.base_date)} ở ${formatNumber(r.base_odometer)} km`;
    return el(
      "article",
      `card rem-card${r.is_active ? "" : " paused"}`,
      el("div", "rem-top", el("h3", "rem-name", r.service_type_name), badge),
      el("p", `rem-left ${r.is_active ? `rem-${PROGRESS_TONE[r.status]}` : "muted"}`, r.is_active ? reminderDetail(r) : "Không nhắc trên Trang chủ cho tới khi bật lại"),
      progressBar(r),
      el("p", "row-sub", dueText(r)),
      el("p", "row-sub", `${intervalText(r)} · ${lastDone}`),
      el(
        "div",
        "rem-actions",
        linkButton("Sửa", "wrench", "btn-secondary btn-sm", `/nhac-lich/${r.reminder_id}/sua`),
        r.is_active
          ? button("Tạm dừng", null, "btn-secondary btn-sm", () => setActive(r, false))
          : button("Bật lại", null, "btn-secondary btn-sm", () => setActive(r, true)),
        button("Xóa", "x", "btn-ghost btn-sm text-bad", () => askDelete(r)),
      ),
    );
  }

  function addButton() {
    return vehicle.is_archived ? null : linkButton("Thêm nhắc lịch", "plus", "btn-primary", `/xe/${vehicle.id}/nhac-lich/moi`);
  }

  function summary(reminders) {
    const active = reminders.filter((r) => r.is_active);
    const overdue = active.filter((r) => r.status === "OVERDUE").length;
    const soon = active.filter((r) => r.status === "DUE_SOON").length;
    const parts = [`${reminders.length} nhắc lịch`];
    if (overdue) parts.push(`${overdue} quá hạn`);
    if (soon) parts.push(`${soon} sắp đến hạn`);
    if (reminders.length > active.length) parts.push(`${reminders.length - active.length} tạm dừng`);
    return parts.join(", ");
  }

  function render(reminders) {
    if (!reminders.length) {
      container.replaceChildren(
        el(
          "div",
          "card empty",
          icon("history"),
          el("p", "empty-title", "Xe này chưa có nhắc lịch"),
          el(
            "p",
            "muted",
            vehicle.is_archived
              ? "Xe đã lưu trữ. Khôi phục xe để đặt nhắc lịch."
              : "Chọn một việc bảo dưỡng và chu kỳ, trang sẽ báo khi sắp đến hạn theo ngày hoặc theo km.",
          ),
          addButton(),
        ),
      );
      return;
    }
    container.replaceChildren(
      el("div", "rem-tools", el("p", "muted", summary(reminders)), addButton()),
      el("div", "rem-grid", ...reminders.map(reminderCard)),
    );
  }

  async function load() {
    try {
      render(await fetchJson(`/api/vehicles/${vehicle.id}/reminders`));
    } catch (error) {
      showError(error.message);
      container.replaceChildren(el("div", "card empty", icon("alert"), el("p", "empty-title", "Không tải được nhắc lịch"), el("p", "muted", error.message)));
    }
  }

  function changed() {
    document.dispatchEvent(new CustomEvent("vml:reminders-changed"));
  }

  async function setActive(r, active) {
    try {
      await VmlForm.sendJson(`/api/reminders/${r.reminder_id}/active`, "PATCH", { active });
      showToast(active ? `Đã bật lại nhắc ${r.service_type_name}` : `Đã tạm dừng nhắc ${r.service_type_name}`);
      changed();
      await load();
    } catch (error) {
      showError(error.message);
    }
  }

  function askDelete(r) {
    pendingDelete = r;
    document.getElementById("reminder-delete-name").textContent = r.service_type_name;
    document.getElementById("reminder-delete-dialog").showModal();
  }

  document.getElementById("reminder-delete-confirm").addEventListener("click", async () => {
    const dialog = document.getElementById("reminder-delete-dialog");
    const r = pendingDelete;
    if (!r) return;
    try {
      await fetchJson(`/api/reminders/${r.reminder_id}`, { method: "DELETE" });
      dialog.close();
      showToast(`Đã xóa nhắc ${r.service_type_name}`);
      changed();
      await load();
    } catch (error) {
      dialog.close();
      showError(error.message);
    }
  });

  window.renderVehicleReminders = function (mount, currentVehicle) {
    container = mount;
    vehicle = currentVehicle;
    container.replaceChildren(el("div", "rem-grid", el("div", "card skel skel-block"), el("div", "card skel skel-block")));
    load();
  };
})();
