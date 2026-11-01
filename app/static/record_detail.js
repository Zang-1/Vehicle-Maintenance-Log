// S06 Chi tiết lần bảo dưỡng (FR-08, FR-09): the receipt of one record, with edit and delete.
(function () {
  "use strict";

  const layout = document.getElementById("record-layout");
  const recordId = layout.dataset.recordId;
  const receipt = document.getElementById("receipt");
  const dialog = document.getElementById("delete-dialog");
  let record = null;

  function box(label, value) {
    return el("div", "info-box", el("small", "", label), el("b", "", value));
  }

  function itemRow(item) {
    const quantity = Number(item.quantity);
    return el(
      "tr",
      "",
      el("td", "first", el("b", "", item.description || item.service_type_name), item.description ? el("span", "sub", item.service_type_name) : null),
      el("td", "r", String(quantity).replace(".", ",")),
      el("td", "r num", formatMoney(item.unit_price)),
      el("td", "r num strong", formatMoney(item.line_total)),
    );
  }

  // Cells carry their column name for the phone layout, where the header row is hidden.
  function labelled(row) {
    const names = ["", "Số lượng", "Đơn giá", "Thành tiền"];
    row.querySelectorAll("td").forEach((cell, i) => cell.setAttribute("data-label", names[i]));
    return row;
  }

  function render(r) {
    const done = [...new Set(r.items.map((i) => i.service_type_name))].join(", ");
    const vehicleLink = el("a", "", r.vehicle_name);
    vehicleLink.href = `/xe/${r.vehicle_id}`;
    const table = el(
      "table",
      "receipt-table",
      el("thead", "", el("tr", "", el("th", "", "Việc đã làm"), el("th", "r", "Số lượng"), el("th", "r", "Đơn giá"), el("th", "r", "Thành tiền"))),
      el("tbody", "", ...r.items.map((i) => labelled(itemRow(i)))),
    );
    const scroll = el("div", "table-scroll", table);
    receipt.replaceChildren(
      el(
        "div",
        "receipt-head",
        el("div", "", el("span", "eyebrow", "Phiếu bảo dưỡng"), el("h2", "receipt-title", r.note || done), el("p", "muted", vehicleLink, r.license_plate ? ` · ${r.license_plate}` : "")),
      ),
      el("div", "info-boxes", box("Ngày làm", formatDate(r.service_date)), box("Số km lúc làm", `${formatNumber(r.odometer)} km`), box("Nơi làm", r.garage_name || "—")),
      scroll,
      el("div", "receipt-total", el("span", "muted", `Tổng cộng (${r.item_count} việc)`), el("b", "sum-total", formatMoney(r.total_cost))),
    );
    document.getElementById("note-text").textContent = r.note || "Không có ghi chú.";
    document.getElementById("back-link").href = `/xe/${r.vehicle_id}#lich-su`;
    document.getElementById("back-link").textContent = `← ${r.vehicle_name}`;
    document.title = `Bảo dưỡng ${formatDate(r.service_date)} · Sổ Bảo Dưỡng Xe`;
  }

  document.getElementById("delete-open").addEventListener("click", () => {
    if (record) {
      document.getElementById("delete-text").textContent =
        `Xóa lần bảo dưỡng ngày ${formatDate(record.service_date)} (${formatMoney(record.total_cost)}) cùng các việc trong đó. Số km hiện tại của xe không đổi. Không thể hoàn tác.`;
    }
    dialog.showModal();
  });

  document.getElementById("delete-confirm").addEventListener("click", async () => {
    try {
      await fetchJson(`/api/records/${recordId}`, { method: "DELETE" });
      location.href = `/xe/${record.vehicle_id}#lich-su`;
    } catch (error) {
      dialog.close();
      showError(error.message);
    }
  });

  dialog.querySelectorAll("[data-close]").forEach((button) => button.addEventListener("click", () => dialog.close()));

  async function init() {
    try {
      record = await fetchJson(`/api/records/${recordId}`);
    } catch (error) {
      showError(error.message);
      const back = el("a", "btn btn-primary", icon("car"), "Về danh sách xe");
      back.href = "/xe";
      receipt.replaceChildren(el("div", "empty", icon("alert"), el("p", "empty-title", "Không mở được lần bảo dưỡng này"), el("p", "muted", error.message), back));
      document.querySelector(".record-side").hidden = true;
      return;
    }
    render(record);
    VmlForm.toastIfSaved("Đã lưu lần bảo dưỡng");
  }

  init();
})();
