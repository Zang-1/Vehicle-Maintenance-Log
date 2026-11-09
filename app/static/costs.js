// Chi phí (FR-17): GET /api/stats/costs?year=&vehicle_id=.
// Four numbers, columns by month, a donut by service type and a table by vehicle. No chart library.
(function () {
  "use strict";

const body = document.getElementById("cost-body");
const vehicleSelect = document.getElementById("f-vehicle");
const chips = document.querySelectorAll("#range .chip");

const fromDateInput = document.getElementById("f-from-date");
const toDateInput = document.getElementById("f-to-date");
const clearDateButton = document.getElementById("clear-date");
const now = new Date();
const thisYear = now.getFullYear();
const PALETTE = ["#0891B2", "#F59E0B", "#10B981", "#0EA5E9", "#F43F5E", "#84CC16", "#94A3B8", "#14B8A6", "#EAB308", "#64748B", "#FB7185", "#22D3EE"];

  let range = "year";
  let requestId = 0;

const percent = (part, whole) => `${(Math.round((part / whole) * 1000) / 10).toString().replace(".", ",")}%`;

  function stat(label, value, sub, tone, isText) {
    return el(
      "div",
      "card cost-stat",
      el("span", "muted", label),
      el("b", `cost-value${isText ? " cost-value-text" : ""}`, value),
      el("span", `cost-sub ${tone}`, sub),
    );
  }

  function section(title, sub, content) {
    return el(
      "div",
      "card cost-section",
      el("div", "cost-section-head", el("h2", "card-heading", title), sub ? el("span", "muted cost-section-sub", sub) : null),
      content,
    );
  }

  function monthBars(months) {
    const values = months.map((m) => Number(m.total));
    const max = Math.max(1, ...values);
    return el(
      "div",
      "cost-bars",
      ...months.map((m, i) => {
        const v = values[i];
        const bar = el("div", `cost-bar${v === 0 ? " zero" : v < max ? " lo" : ""}`);
        bar.style.height = `${v ? Math.max(8, Math.round((196 * v) / max)) : 6}px`;
        bar.dataset.v = v ? formatMoney(v) : "0 đ";
        bar.title = `T${m.month}: ${bar.dataset.v}`;
        return el("div", "cost-bar-col", bar, el("span", "muted cost-bar-label", `T${m.month}`));
      }),
    );
  }

  function donut(types, total) {
    let acc = 0;
    const stops = types.map((t, i) => {
      const from = acc;
      acc += (Number(t.total) / total) * 100;
      return `${PALETTE[i % PALETTE.length]} ${from.toFixed(2)}% ${acc.toFixed(2)}%`;
    });
    const ring = el(
      "div",
      "donut",
      el("div", "donut-center", el("div", "", el("b", "", formatMoney(total)), el("div", "muted", `${types.length} loại`))),
    );
    ring.style.background = `conic-gradient(${stops.join(", ")})`;
    ring.setAttribute("role", "img");
    ring.setAttribute("aria-label", "Tỉ trọng chi phí theo loại việc");
    const legend = el(
      "div",
      "legend",
      ...types.map((t, i) => {
        const swatch = el("span", "legend-swatch");
        swatch.style.background = PALETTE[i % PALETTE.length];
        return el("div", "legend-item", swatch, el("span", "legend-name", t.service_type_name), el("b", "num", percent(Number(t.total), total)));
      }),
    );
    return el("div", "donut-wrap", ring, legend);
  }

  function cell(label, className, ...children) {
    const td = el("td", className, ...children);
    td.dataset.label = label; // the phone layout prints it in front of the value
    return td;
  }

  function vehicleRow(v, total) {
    const thumb = el("span", "thumb cost-thumb", vehicleDrawing(v.vehicle_type, 46));
    const name = el(
      "a",
      "cost-vehicle",
      thumb,
      el("span", "cost-vehicle-name", el("b", "", v.vehicle_name), v.license_plate ? el("span", "sub", v.license_plate) : null),
    );
    name.href = `/xe/${v.vehicle_id}`;
    const share = total ? (Number(v.total) / total) * 100 : 0;
    const fill = el("span");
    fill.style.width = `${Math.round(share)}%`;
    const tr = el(
      "tr",
      "click",
      cell("", "first", name),
      cell("Số lần", "r", String(v.record_count)),
      cell("Tỉ trọng", "", el("div", "cost-share", el("div", "progress", fill), el("span", "muted", total ? percent(Number(v.total), total) : "0%"))),
      cell("Tổng chi phí", "r num strong", formatMoney(v.total)),
    );
    tr.addEventListener("click", () => {
      location.href = `/xe/${v.vehicle_id}`;
    });
    return tr;
  }

  function vehicleTable(vehicles, total) {
    const head = el(
      "thead",
      "",
      el("tr", "", ...[["Xe", ""], ["Số lần", "r"], ["Tỉ trọng", ""], ["Tổng chi phí", "r"]].map(([label, className]) => el("th", className, label))),
    );
    const table = el("table", "data-table", head, el("tbody", "", ...vehicles.map((v) => vehicleRow(v, total))));
    return el("div", "card table-card", el("h2", "card-heading cost-table-title", "Theo xe"), table);
  }

  function render(data) {
    const total = Number(data.total);
    if (!data.record_count) {
      body.replaceChildren(
        el(
          "div",
          "card empty",
          icon("chart"),
          el("p", "empty-title", "Chưa có dữ liệu trong khoảng này"),
          el("p", "muted", "Ghi lần bảo dưỡng để xem chi phí tại đây."),
        ),
      );
      return;
    }

    const topVehicle = data.by_vehicle[0];
    const topType = data.by_service_type[0];
    const allVehicles = !vehicleSelect.value;
    const stats = el(
      "div",
      "cost-stats",
      stat("Tổng chi phí", formatMoney(total), `${data.item_count} hạng mục`, "text-accent", false),
      stat("Số lần bảo dưỡng", String(data.record_count), `${data.by_service_type.length} loại việc`, "text-primary", false),
      stat(
        "Trung bình mỗi lần",
        formatMoney(Math.round(total / data.record_count)),
        topVehicle && allVehicles && total ? `${topVehicle.vehicle_name} · ${percent(Number(topVehicle.total), total)}` : "",
        "text-ok",
        false,
      ),
      stat(
        "Hạng mục tốn nhất",
        topType ? topType.service_type_name : "—",
        topType && total ? `${formatMoney(topType.total)} · ${percent(Number(topType.total), total)}` : "",
        "text-warn",
        true,
      ),
    );

    // this year: stop at the current month, so the empty future months do not look like zero spending
    const months = data.year === thisYear ? data.months.slice(0, now.getMonth() + 1) : data.months;
    const monthSub = data.year ? `Năm ${data.year} · rê chuột lên cột để xem số tiền` : "Cộng các năm theo tháng · rê chuột lên cột để xem số tiền";
    const typeContent = total
      ? donut(data.by_service_type, total)
      : el("p", "muted", "Các lần bảo dưỡng trong khoảng này chưa nhập giá tiền.");

    body.replaceChildren(
      stats,
      el("div", "split", section("Chi phí theo tháng", monthSub, monthBars(months)), section("Theo loại việc", null, typeContent)),
      vehicleTable(data.by_vehicle, total),
    );
  }

  async function load() {
  const current = ++requestId;
  document.getElementById("error").hidden = true;

  const fromDate = fromDateInput.value;
  const toDate = toDateInput.value;

  // Phải chọn đủ cả hai ngày
  if (Boolean(fromDate) !== Boolean(toDate)) {
    showError("Vui lòng chọn cả ngày bắt đầu và ngày kết thúc.");
    return;
  }

  // Ngày bắt đầu không được sau ngày kết thúc
  if (fromDate && toDate && fromDate > toDate) {
    showError("Ngày bắt đầu không được lớn hơn ngày kết thúc.");
    return;
  }

  const query = new URLSearchParams();

  // Nếu có khoảng ngày tùy chỉnh thì ưu tiên lọc theo ngày
  if (fromDate && toDate) {
    query.set("from_date", fromDate);
    query.set("to_date", toDate);
  } else if (range === "year") {
    query.set("year", String(thisYear));
  }

  if (vehicleSelect.value) {
    query.set("vehicle_id", vehicleSelect.value);
  }

  try {
    const data = await fetchJson(`/api/stats/costs?${query}`);

    if (current === requestId) {
      render(data);
    }
  } catch (error) {
    if (current !== requestId) return;

    showError(error.message);
    body.replaceChildren(
      el("p", "muted", "Không tải được số liệu chi phí."),
    );
  }
}

  async function init() {
    chips[0].textContent = `Năm ${thisYear}`;
    try {
      const vehicles = await fetchJson("/api/vehicles?archived=all");
      for (const v of vehicles) {
        vehicleSelect.append(new Option(v.is_archived ? `${v.name} (đã lưu trữ)` : v.name, String(v.id)));
      }
    } catch (error) {
      showError(error.message);
    }
    load();
  }

  chips.forEach((chip) =>
    chip.addEventListener("click", () => {
      range = chip.dataset.range;
      chips.forEach((other) => {
        const on = other === chip;
        other.classList.toggle("active", on);
        other.setAttribute("aria-pressed", String(on));
      });
      load();
    }),
  );
  vehicleSelect.addEventListener("change", load);

fromDateInput.addEventListener("change", load);
toDateInput.addEventListener("change", load);

clearDateButton.addEventListener("click", () => {
  fromDateInput.value = "";
  toDateInput.value = "";
  load();
});

init();
})();