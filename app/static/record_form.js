// S05 Ghi / Sửa lần bảo dưỡng (FR-06, FR-09): POST /api/vehicles/{id}/records, or PUT /api/records/{id}.
// Quick chips pick the services done, then the user types a price for each (135000 is typed as 135.000).
(function () {
  "use strict";

  const form = document.getElementById("record-form");
  const recordId = form.dataset.recordId;
  const editing = recordId !== "";
  const itemsBox = document.getElementById("items");
  const chipsBox = document.getElementById("quick-chips");
  const vehicleSelect = document.getElementById("f-vehicle");
  const dateInput = document.getElementById("f-date");
  const odoInput = document.getElementById("f-odo");
  const more = document.getElementById("more");
  const save = document.getElementById("save");
  const formAlert = document.getElementById("form-alert");
  const query = new URLSearchParams(location.search);

  let vehicles = []; // active vehicles (new record) or just the record's vehicle (edit)
  let serviceTypes = []; // active service types
  let keptTypes = []; // types already on the record being edited: they stay selectable even if retired since
  let rows = [];
  let nextId = 0;
  let odoTouched = false;

  const currentVehicle = () => vehicles.find((v) => String(v.id) === vehicleSelect.value) || null;

  // ---------- service types ----------
  function applicableTypes() {
    const vehicle = currentVehicle();
    const list = serviceTypes.filter((t) => !vehicle || t.applies_to === "ALL" || t.applies_to === vehicle.vehicle_type);
    const have = new Set(list.map((t) => t.id));
    return [...list, ...keptTypes.filter((t) => !have.has(t.id))];
  }

  function fillTypeOptions(row) {
    const keep = row.typeSelect.value;
    const placeholder = el("option", "", "Chọn việc đã làm…");
    placeholder.value = "";
    row.typeSelect.replaceChildren(
      placeholder,
      ...applicableTypes().map((t) => {
        const option = el("option", "", t.name);
        option.value = String(t.id);
        return option;
      }),
    );
    row.typeSelect.value = keep;
  }

  // ---------- rows ----------
  function cell(row, name, className, ...children) {
    const box = el("div", `field ${className}`, ...children);
    box.dataset.field = `item-${row.id}-${name}`;
    return box;
  }

  function addRow(data = {}) {
    const row = { id: ++nextId };
    row.typeSelect = el("select", "control");
    row.typeSelect.setAttribute("aria-label", "Việc đã làm");
    row.descInput = el("input", "control");
    row.descInput.maxLength = 255;
    row.descInput.placeholder = "Mô tả, ví dụ: Nhớt Castrol 0.8L";
    row.descInput.setAttribute("aria-label", "Mô tả");
    row.qtyInput = el("input", "control");
    row.qtyInput.inputMode = "decimal";
    row.qtyInput.placeholder = "SL";
    row.qtyInput.setAttribute("aria-label", "Số lượng");
    row.priceInput = el("input", "control");
    row.priceInput.inputMode = "numeric";
    row.priceInput.placeholder = "Ví dụ 135.000";
    row.priceInput.setAttribute("aria-label", "Giá tiền");
    row.totalCell = el("div", "line-total");
    row.removeButton = el("button", "icon-btn plain item-del", icon("x"));
    row.removeButton.type = "button";
    row.removeButton.setAttribute("aria-label", "Bỏ việc này");

    fillTypeOptions(row);
    row.typeSelect.value = data.typeId ? String(data.typeId) : "";
    row.descInput.value = data.description || "";
    row.qtyInput.value = data.quantity !== undefined ? String(data.quantity).replace(".", ",") : "1";
    row.priceInput.value = data.price !== undefined ? VmlForm.groupDigits(data.price) : "";
    VmlForm.bindDigits(row.priceInput);

    row.node = el(
      "div",
      "item-row",
      cell(row, "type", "f-type", row.typeSelect),
      cell(row, "desc", "f-desc", row.descInput),
      cell(row, "qty", "f-qty", row.qtyInput),
      cell(row, "price", "f-price", el("div", "input-wrap", row.priceInput, el("span", "suffix", "đ"))),
      row.totalCell,
      row.removeButton,
    );

    row.typeSelect.addEventListener("change", afterChange);
    [row.qtyInput, row.priceInput].forEach((input) => input.addEventListener("input", recalc));
    row.removeButton.addEventListener("click", () => removeRow(row));
    rows.push(row);
    itemsBox.append(row.node);
    return row;
  }

  function removeRow(row) {
    row.node.remove();
    rows = rows.filter((r) => r !== row);
    if (!rows.length) addRow();
    afterChange();
  }

  function toggleType(typeId) {
    const existing = rows.find((r) => r.typeSelect.value === String(typeId));
    if (existing) {
      removeRow(existing);
      return;
    }
    const blank = rows.find((r) => !r.typeSelect.value && !r.priceInput.value);
    const row = blank || addRow();
    row.typeSelect.value = String(typeId);
    afterChange();
    row.priceInput.focus();
  }

  function renderChips() {
    const picked = new Set(rows.map((r) => r.typeSelect.value).filter(Boolean));
    // The jobs done most often come first (short km interval), then the rest; a picked job always shows.
    const byInterval = (t) => t.default_interval_km || Number.MAX_SAFE_INTEGER;
    const all = applicableTypes();
    const common = all.filter((t) => t.default_interval_km || t.default_interval_months).sort((a, b) => byInterval(a) - byInterval(b)).slice(0, 8);
    const shown = [...common, ...all.filter((t) => picked.has(String(t.id)) && !common.includes(t))];
    chipsBox.replaceChildren(
      ...shown.map((t) => {
        const on = picked.has(String(t.id));
        const chip = el("button", `chip big${on ? " active" : ""}`, icon(on ? "check" : "plus"), t.name);
        chip.type = "button";
        chip.setAttribute("aria-pressed", String(on));
        chip.addEventListener("click", () => toggleType(t.id));
        return chip;
      }),
    );
  }

  // ---------- numbers ----------
  function lineTotal(row) {
    const quantity = VmlForm.toQuantity(row.qtyInput.value);
    const price = VmlForm.toInt(row.priceInput.value);
    return quantity === null || price === null ? null : Math.round(quantity * price);
  }

  function recalc() {
    let total = 0;
    for (const row of rows) {
      const line = lineTotal(row);
      row.totalCell.textContent = line === null ? "—" : formatMoney(line);
      total += line || 0;
    }
    document.getElementById("sum-count").textContent = rows.filter((r) => r.typeSelect.value).length;
    document.getElementById("sum-total").textContent = formatMoney(total);
  }

  function afterChange() {
    renderChips();
    recalc();
  }

  // ---------- vehicle ----------
  function renderVehicle() {
    const vehicle = currentVehicle();
    const box = document.getElementById("summary-vehicle");
    const help = document.getElementById("odo-help");
    if (!vehicle) {
      box.replaceChildren();
      help.textContent = "";
      return;
    }
    const link = el(
      "a",
      "summary-vehicle-link",
      el("div", "thumb", vehicleDrawing(vehicle.vehicle_type, 64)),
      el("div", "", el("b", "", vehicle.name), el("p", "row-sub", [vehicle.license_plate, `${formatNumber(vehicle.current_odometer)} km`].filter(Boolean).join(" · "))),
    );
    link.href = `/xe/${vehicle.id}`;
    box.replaceChildren(link);
    help.textContent = `Số km hiện tại của xe: ${formatNumber(vehicle.current_odometer)} km. Ghi bù lần cũ thì nhập số km lúc đó.`;
    document.getElementById("cancel").href = editing ? `/bao-duong/${recordId}` : `/xe/${vehicle.id}`;
    document.getElementById("back-link").href = editing ? `/bao-duong/${recordId}` : `/xe/${vehicle.id}`;
    document.getElementById("back-link").textContent = editing ? "← Chi tiết lần bảo dưỡng" : `← ${vehicle.name}`;
  }

  function onVehicleChange() {
    const vehicle = currentVehicle();
    if (vehicle && !odoTouched && !editing) odoInput.value = VmlForm.groupDigits(vehicle.current_odometer);
    renderVehicle();
    rows.forEach(fillTypeOptions);
    afterChange();
  }

  // ---------- save ----------
  function validate() {
    VmlForm.clearErrors(form);
    formAlert.hidden = true;
    const vehicle = currentVehicle();
    const odo = VmlForm.toInt(odoInput.value);
    if (!vehicle) VmlForm.setError(form, "vehicle_id", "Chọn xe đã được bảo dưỡng.");
    if (!dateInput.value) VmlForm.setError(form, "service_date", "Chọn ngày làm.");
    else if (dateInput.value > VmlForm.todayIso()) VmlForm.setError(form, "service_date", "Ngày làm không được ở tương lai.");
    if (odo === null) VmlForm.setError(form, "odometer", "Nhập số km trên đồng hồ lúc làm.");

    const items = [];
    for (const row of rows) {
      const quantity = VmlForm.toQuantity(row.qtyInput.value);
      const price = VmlForm.toInt(row.priceInput.value);
      let ok = true;
      if (!row.typeSelect.value) {
        VmlForm.setError(form, `item-${row.id}-type`, "Chọn việc đã làm.");
        ok = false;
      }
      if (quantity === null || quantity <= 0) {
        VmlForm.setError(form, `item-${row.id}-qty`, "Số lượng lớn hơn 0.");
        ok = false;
      }
      if (price === null) {
        VmlForm.setError(form, `item-${row.id}-price`, "Nhập giá tiền (0 nếu miễn phí).");
        ok = false;
      } else if (quantity !== null && quantity * price >= 1e14) {
        VmlForm.setError(form, `item-${row.id}-price`, "Thành tiền quá lớn.");
        ok = false;
      }
      if (ok) {
        items.push({
          service_type_id: Number(row.typeSelect.value),
          description: row.descInput.value.trim() || null,
          quantity,
          unit_price: price,
        });
      }
    }
    if (form.querySelector("[aria-invalid='true']")) {
      if (form.querySelector(".f-desc [aria-invalid], .f-qty [aria-invalid]")) more.open = true;
      VmlForm.focusFirstError(form);
      return null;
    }
    return {
      vehicleId: vehicle.id,
      body: {
        service_date: dateInput.value,
        odometer: odo,
        garage_name: document.getElementById("f-garage").value.trim() || null,
        note: document.getElementById("f-note").value.trim() || null,
        items,
      },
    };
  }

  function resolveField(loc) {
    const parts = loc.filter((p) => p !== "body");
    if (parts[0] === "items") {
      const row = rows[parts[1]];
      const name = { service_type_id: "type", description: "desc", quantity: "qty", unit_price: "price" }[parts[2]];
      return row ? `item-${row.id}-${name || "type"}` : null;
    }
    return typeof parts[0] === "string" ? parts[0] : null;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = validate();
    if (!data) return;
    save.disabled = true;
    try {
      const url = editing ? `/api/records/${recordId}` : `/api/vehicles/${data.vehicleId}/records`;
      const saved = await VmlForm.sendJson(url, editing ? "PUT" : "POST", data.body);
      location.href = `/bao-duong/${saved.record_id}?saved=1`;
    } catch (error) {
      save.disabled = false;
      const code = error.body && error.body.error_code;
      if (code === "DUPLICATE_RECORD") {
        VmlForm.setError(form, "service_date", "Đã có lần bảo dưỡng cùng ngày và số km.");
        VmlForm.setError(form, "odometer", "Đã có lần bảo dưỡng cùng ngày và số km.");
      }
      if (error.status === 422 && Array.isArray(error.body && error.body.detail)) VmlForm.showServerError(form, error, resolveField);
      else {
        formAlert.textContent = error.message;
        formAlert.hidden = false;
      }
    }
  });

  document.getElementById("add-item").addEventListener("click", () => {
    addRow().typeSelect.focus();
    afterChange();
  });
  vehicleSelect.addEventListener("change", onVehicleChange);
  odoInput.addEventListener("input", () => {
    odoTouched = true;
  });
  more.addEventListener("toggle", () => itemsBox.classList.toggle("simple", !more.open));
  VmlForm.bindDigits(odoInput);
  VmlForm.clearErrorOnInput(form);

  // ---------- start ----------
  async function init() {
    dateInput.max = VmlForm.todayIso();
    dateInput.value = VmlForm.todayIso();
    let record = null;
    try {
      serviceTypes = await fetchJson("/api/service-types?active=true");
      if (editing) {
        record = await fetchJson(`/api/records/${recordId}`);
        vehicles = [await fetchJson(`/api/vehicles/${record.vehicle_id}`)];
        keptTypes = record.items.map((i) => ({ id: i.service_type_id, name: i.service_type_name, applies_to: "ALL", default_interval_km: null, default_interval_months: null }));
      } else {
        vehicles = await fetchJson("/api/vehicles?archived=active");
      }
    } catch (error) {
      showError(error.message);
      return;
    }

    if (!vehicles.length) {
      document.getElementById("no-vehicle").hidden = false;
      return;
    }
    vehicleSelect.replaceChildren(
      ...vehicles.map((v) => {
        const option = el("option", "", `${v.name}${v.license_plate ? ` · ${v.license_plate}` : ""}`);
        option.value = String(v.id);
        return option;
      }),
    );
    const wanted = editing ? record.vehicle_id : Number(query.get("xe"));
    if (vehicles.some((v) => v.id === wanted)) vehicleSelect.value = String(wanted);
    vehicleSelect.disabled = editing; // a record stays with its vehicle

    if (editing) {
      dateInput.value = record.service_date;
      odoInput.value = VmlForm.groupDigits(record.odometer);
      document.getElementById("f-garage").value = record.garage_name || "";
      document.getElementById("f-note").value = record.note || "";
      record.items.forEach((i) => addRow({ typeId: i.service_type_id, description: i.description, quantity: Number(i.quantity), price: Number(i.unit_price) }));
      if (record.garage_name || record.note || record.items.some((i) => i.description || Number(i.quantity) !== 1)) more.open = true;
    } else {
      odoInput.value = VmlForm.groupDigits(currentVehicle().current_odometer);
      const type = Number(query.get("loai"));
      addRow(applicableTypes().some((t) => t.id === type) ? { typeId: type } : {});
    }
    itemsBox.classList.toggle("simple", !more.open);
    form.hidden = false;
    onVehicleChange();
    if (!editing && query.get("loai")) rows[0].priceInput.focus();
  }

  init();
})();
