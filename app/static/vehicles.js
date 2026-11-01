// S02 Xe của tôi (FR-02, FR-05): GET /api/vehicles?archived=active|archived|all, then one card per vehicle.
(function () {
  "use strict";

  const list = document.getElementById("vehicle-list");
  const chips = document.querySelectorAll("#filter .chip");
  const EMPTY = {
    active: ["Chưa có xe nào", "Thêm xe đầu tiên: chỉ cần tên gọi và số km hiện tại."],
    archived: ["Chưa có xe nào được lưu trữ", "Xe đã bán có thể được lưu trữ để giữ lại lịch sử bảo dưỡng."],
    all: ["Chưa có xe nào", "Thêm xe đầu tiên: chỉ cần tên gọi và số km hiện tại."],
  };

  function statusBadge(v) {
    if (v.is_archived) return el("span", "badge badge-neutral", "Đã lưu trữ");
    if (v.overdue_count) return el("span", "badge badge-bad", `${v.overdue_count} việc quá hạn`);
    if (v.due_soon_count) return el("span", "badge badge-warn", `${v.due_soon_count} việc sắp đến hạn`);
    return el("span", "badge badge-ok", "Đều ổn");
  }

  function metric(label, value) {
    return el("div", "metric", el("small", "", label), el("b", "", value));
  }

  function card(v) {
    const subtitle = VmlForm.vehicleSubtitle(v);
    const link = el(
      "a",
      `card vcard${v.is_archived ? " is-archived" : ""}`,
      el("div", "thumb", vehicleDrawing(v.vehicle_type, 150)),
      el(
        "div",
        "vcard-body",
        el(
          "div",
          "vcard-top",
          el("div", "vcard-name", el("b", "", v.name), el("span", "row-sub", subtitle || VmlForm.TYPE_LABEL[v.vehicle_type])),
          v.license_plate ? el("span", "plate", v.license_plate) : null,
        ),
        statusBadge(v),
        el(
          "div",
          "vcard-meta",
          metric("Số km", `${formatNumber(v.current_odometer)} km`),
          metric("Gần nhất", v.last_service_date ? formatDate(v.last_service_date) : "—"),
          metric("Đã chi", formatMoney(v.total_cost)),
          metric("Số lần", `${v.record_count} lần`),
        ),
      ),
    );
    link.href = `/xe/${v.id}`;
    return link;
  }

  function addCard() {
    const link = el("a", "card vehicle-card vehicle-add", icon("plus"), "Thêm xe mới");
    link.href = "/xe/moi";
    return link;
  }

  function render(vehicles, filter) {
    if (!vehicles.length) {
      const [title, sub] = EMPTY[filter];
      const add = el("a", "btn btn-primary", icon("plus"), "Thêm xe");
      add.href = "/xe/moi";
      list.replaceChildren(
        el("div", "card empty", vehicleDrawing("OTHER", 120), el("p", "empty-title", title), el("p", "muted", sub), filter === "archived" ? null : add),
      );
      return;
    }
    list.replaceChildren(...vehicles.map(card), ...(filter === "archived" ? [] : [addCard()]));
  }

  async function load(filter) {
    document.getElementById("error").hidden = true;
    try {
      render(await fetchJson(`/api/vehicles?archived=${filter}`), filter);
    } catch (error) {
      showError(error.message);
      list.replaceChildren(el("p", "muted", "Không tải được danh sách xe."));
    }
  }

  chips.forEach((chip) =>
    chip.addEventListener("click", () => {
      chips.forEach((other) => {
        const on = other === chip;
        other.classList.toggle("active", on);
        other.setAttribute("aria-pressed", String(on));
      });
      load(chip.dataset.filter);
    }),
  );

  load("active");
})();
