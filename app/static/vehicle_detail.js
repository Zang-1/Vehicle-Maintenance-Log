// S04 Chi tiết xe (FR-03, FR-05, FR-07, FR-10): header, tabs Thông tin / Lịch sử / Nhắc bảo dưỡng.
(function () {
  "use strict";

  const head = document.getElementById("vd-head");
  const vehicleId = head.dataset.vehicleId;
  const panes = { "thong-tin": "pane-info", "lich-su": "pane-history", "nhac-bao-duong": "pane-reminders" };
  const tabs = document.querySelectorAll(".tabs .tab");
  const fromDate = document.getElementById("from-date");
  const toDate = document.getElementById("to-date");

  let vehicle = null;
  let remindersMounted = false;

  // ---------- header ----------
  function headerBadge(v) {
    if (v.is_archived) return el("span", "badge badge-neutral", "Đã lưu trữ");
    if (v.overdue_count) return el("span", "badge badge-bad", `${v.overdue_count} việc quá hạn`);
    if (v.due_soon_count) return el("span", "badge badge-warn", `${v.due_soon_count} việc sắp đến hạn`);
    return el("span", "badge badge-ok", "Đều ổn");
  }

  function kpi(label, value) {
    return el("div", "kpi", el("small", "", label), el("b", "", value));
  }

  function action(label, iconName, className, handler) {
    const button = el("button", `btn ${className}`, icon(iconName), label);
    button.type = "button";
    button.addEventListener("click", handler);
    return button;
  }

  function linkAction(label, iconName, className, href) {
    const link = el("a", `btn ${className}`, icon(iconName), label);
    link.href = href;
    return link;
  }

  function renderHead(v) {
    const subtitle = VmlForm.vehicleSubtitle(v);
    const actions = [];
    if (v.is_archived) actions.push(action("Khôi phục", "history", "btn-secondary", () => setArchived(false)));
    else actions.push(action("Lưu trữ", "shield", "btn-secondary", () => document.getElementById("archive-dialog").showModal()));
    if (!v.record_count) actions.push(action("Xóa xe", "x", "btn-ghost text-bad", () => document.getElementById("delete-dialog").showModal()));
    actions.push(linkAction("Sửa", "wrench", "btn-secondary", `/xe/${v.id}/sua`));
    if (!v.is_archived) actions.push(linkAction("Ghi lần bảo dưỡng", "plus", "btn-primary", `/bao-duong/moi?xe=${v.id}`));

    head.replaceChildren(
      el(
        "div",
        "vd-top",
        el("div", "thumb vd-thumb", vehicleDrawing(v.vehicle_type, 210)),
        el(
          "div",
          "vd-main",
          el("div", "vd-title", el("h2", "", v.name), headerBadge(v)),
          el("p", "muted", [subtitle, VmlForm.TYPE_LABEL[v.vehicle_type]].filter(Boolean).join(" · ")),
          el("div", "vd-chips", v.license_plate ? el("span", "plate", v.license_plate) : null, el("span", "badge badge-neutral nodot", `${formatNumber(v.current_odometer)} km`)),
        ),
        el("div", "vd-actions", ...actions),
      ),
      el(
        "div",
        "kpis",
        kpi("Tổng chi phí", formatMoney(v.total_cost)),
        kpi("Số lần bảo dưỡng", `${v.record_count} lần`),
        kpi("Lần gần nhất", v.last_service_date ? formatDate(v.last_service_date) : "—"),
        kpi("Số km hiện tại", `${formatNumber(v.current_odometer)} km`),
      ),
    );
    document.querySelector(".page-head h1").textContent = v.name;
    document.title = `${v.name} · Sổ Bảo Dưỡng Xe`;
    document.getElementById("count-history").textContent = v.record_count;
  }

  // ---------- tab: thông tin ----------
  function renderInfo(v) {
    const pairs = [
      ["Tên gọi", v.name],
      ["Loại xe", VmlForm.TYPE_LABEL[v.vehicle_type]],
      ["Hãng · Dòng xe", [v.brand, v.model].filter(Boolean).join(" ") || "—"],
      ["Năm sản xuất", v.manufacture_year || "—"],
      ["Biển số", v.license_plate || "—"],
      ["Số km hiện tại", `${formatNumber(v.current_odometer)} km`],
      ["Ngày mua", v.purchase_date ? formatDate(v.purchase_date) : "—"],
      ["Trạng thái", v.is_archived ? "Đã lưu trữ" : "Đang dùng"],
    ];
    document.getElementById("pane-info").replaceChildren(
      el("div", "info-grid", ...pairs.map(([label, value]) => el("div", "info-item", el("small", "", label), el("b", "", String(value))))),
    );
  }

  // ---------- tab: lịch sử ----------
  function recordRow(r) {
    const link = el(
      "a",
      "history-row",
      el("span", "history-dot", icon("wrench")),
      el(
        "div",
        "row-main",
        el("p", "row-title", `${formatDate(r.service_date)} · ${formatNumber(r.odometer)} km`),
        el("p", "row-sub", [r.garage_name, `${r.item_count} việc`, r.note].filter(Boolean).join(" · ")),
        r.items_summary ? el("p", "row-sub history-items", r.items_summary) : null,
      ),
      el("b", "row-amount", formatMoney(r.total_cost)),
      icon("chevron-right"),
    );
    link.href = `/bao-duong/${r.record_id}`;
    return link;
  }

  function filterQuery() {
    const params = new URLSearchParams();
    if (fromDate.value) params.set("from_date", fromDate.value);
    if (toDate.value) params.set("to_date", toDate.value);
    return params.toString();
  }

  async function loadHistory() {
    const list = document.getElementById("history-list");
    const query = filterQuery();
    document.getElementById("clear-filter").hidden = !query;
    document.getElementById("csv-link").href = `/api/vehicles/${vehicleId}/records.csv${query ? `?${query}` : ""}`;
    try {
      const records = await fetchJson(`/api/vehicles/${vehicleId}/records${query ? `?${query}` : ""}`);
      if (!records.length) {
        const log = linkAction("Ghi lần bảo dưỡng", "plus", "btn-primary", `/bao-duong/moi?xe=${vehicleId}`);
        list.replaceChildren(
          el(
            "div",
            "empty",
            icon("wrench"),
            el("p", "empty-title", query ? "Không có lần bảo dưỡng nào trong khoảng này" : "Chưa có lần bảo dưỡng nào"),
            el("p", "muted", query ? "Thử mở rộng khoảng ngày." : "Ghi lần bảo dưỡng đầu tiên để theo dõi chi phí và nhận nhắc nhở."),
            vehicle && !vehicle.is_archived && !query ? log : null,
          ),
        );
        return;
      }
      list.replaceChildren(...records.map(recordRow));
    } catch (error) {
      showError(error.message);
      list.replaceChildren(el("p", "muted", "Không tải được lịch sử bảo dưỡng."));
    }
  }

  // ---------- tab: nhắc bảo dưỡng (Khoa) ----------
  function mountReminders() {
    if (remindersMounted) return;
    remindersMounted = true;
    const mount = document.getElementById("reminders-mount");
    if (typeof window.renderVehicleReminders === "function") {
      window.renderVehicleReminders(mount, vehicle);
      return;
    }
    mount.replaceChildren(el("div", "card empty", icon("alert"), el("p", "empty-title", "Phần Nhắc bảo dưỡng đang được làm"), el("p", "muted", "Trang sẽ hiện các nhắc nhở của xe này khi phần đó hoàn tất.")));
  }

  // ---------- tabs ----------
  function showTab(name) {
    if (!panes[name]) name = "thong-tin";
    tabs.forEach((tab) => {
      const on = tab.dataset.tab === name;
      tab.classList.toggle("on", on);
      tab.setAttribute("aria-selected", String(on));
    });
    for (const [key, id] of Object.entries(panes)) document.getElementById(id).hidden = key !== name;
    if (name === "lich-su") loadHistory();
    if (name === "nhac-bao-duong" && vehicle) mountReminders();
    history.replaceState(null, "", location.pathname + location.search + (name === "thong-tin" ? "" : `#${name}`));
  }

  tabs.forEach((tab) => tab.addEventListener("click", () => showTab(tab.dataset.tab)));
  [fromDate, toDate].forEach((input) => input.addEventListener("change", loadHistory));
  document.getElementById("clear-filter").addEventListener("click", () => {
    fromDate.value = "";
    toDate.value = "";
    loadHistory();
  });

  // ---------- archive / delete ----------
  async function setArchived(archived) {
    try {
      vehicle = await VmlForm.sendJson(`/api/vehicles/${vehicleId}/archive`, "PATCH", { archived });
      document.getElementById("archive-dialog").close();
      renderHead(vehicle);
      renderInfo(vehicle);
      showToast(archived ? "Đã lưu trữ xe" : "Đã khôi phục xe");
    } catch (error) {
      document.getElementById("archive-dialog").close();
      showError(error.message);
    }
  }

  document.getElementById("archive-confirm").addEventListener("click", () => setArchived(true));

  document.getElementById("delete-confirm").addEventListener("click", async () => {
    try {
      await fetchJson(`/api/vehicles/${vehicleId}`, { method: "DELETE" });
      location.href = "/xe";
    } catch (error) {
      document.getElementById("delete-dialog").close();
      showError(error.message);
    }
  });

  document.querySelectorAll("dialog [data-close]").forEach((button) =>
    button.addEventListener("click", () => button.closest("dialog").close()),
  );

  // ---------- start ----------
  async function init() {
    fromDate.max = VmlForm.todayIso();
    toDate.max = VmlForm.todayIso();
    try {
      vehicle = await fetchJson(`/api/vehicles/${vehicleId}`);
    } catch (error) {
      showError(error.message);
      head.replaceChildren(
        el("div", "empty", icon("alert"), el("p", "empty-title", "Không mở được xe này"), el("p", "muted", error.message), linkAction("Về danh sách xe", "car", "btn-primary", "/xe")),
      );
      return;
    }
    renderHead(vehicle);
    renderInfo(vehicle);
    showTab(location.hash.slice(1));
    VmlForm.toastIfSaved("Đã lưu thông tin xe");
  }

  init();
})();
