// S03 Thêm / Sửa xe (FR-01, FR-04): POST /api/vehicles, or PUT /api/vehicles/{id} when the page has an id.
(function () {
  "use strict";

  const form = document.getElementById("vehicle-form");
  const vehicleId = form.dataset.vehicleId;
  const editing = vehicleId !== "";
  const save = document.getElementById("save");
  const typeChips = document.querySelectorAll("#type-chips .chip");
  const input = (name) => form.elements[name];

  let vehicleType = "MOTORBIKE";
  let currentOdometer = 0; // the stored value while editing: the odometer never goes down (BR-02)

  function setType(type) {
    vehicleType = type;
    typeChips.forEach((chip) => {
      const on = chip.dataset.type === type;
      chip.classList.toggle("active", on);
      chip.setAttribute("aria-pressed", String(on));
    });
    updatePreview();
  }

  function updatePreview() {
    document.getElementById("preview-thumb").replaceChildren(vehicleDrawing(vehicleType, 180));
    document.getElementById("preview-name").textContent = input("name").value.trim() || "Tên xe";
    const subtitle = VmlForm.vehicleSubtitle({
      brand: input("brand").value.trim(),
      model: input("model").value.trim(),
      manufacture_year: input("manufacture_year").value.trim(),
    });
    document.getElementById("preview-sub").textContent = subtitle || VmlForm.TYPE_LABEL[vehicleType];
    const plate = input("license_plate").value.trim().toUpperCase();
    const plateBox = document.getElementById("preview-plate");
    plateBox.textContent = plate;
    plateBox.hidden = !plate;
  }

  function fill(v) {
    currentOdometer = v.current_odometer;
    input("name").value = v.name;
    input("current_odometer").value = VmlForm.groupDigits(v.current_odometer);
    input("license_plate").value = v.license_plate || "";
    input("brand").value = v.brand || "";
    input("model").value = v.model || "";
    input("manufacture_year").value = v.manufacture_year || "";
    input("purchase_date").value = v.purchase_date || "";
    document.getElementById("odo-help").textContent = `Số km hiện tại đang lưu: ${formatNumber(v.current_odometer)} km. Không nhập số nhỏ hơn.`;
    if (v.license_plate || v.brand || v.model || v.manufacture_year || v.purchase_date) document.getElementById("more").open = true;
    setType(v.vehicle_type);
  }

  // Returns the body to send, or null after marking every wrong field.
  function validate() {
    VmlForm.clearErrors(form);
    const name = input("name").value.trim();
    const odo = VmlForm.toInt(input("current_odometer").value);
    const yearText = input("manufacture_year").value.trim();
    const year = yearText ? Number(yearText) : null;
    const purchase = input("purchase_date").value;

    if (!name) VmlForm.setError(form, "name", "Hãy đặt tên gọi cho xe.");
    if (odo === null) VmlForm.setError(form, "current_odometer", "Nhập số km hiện tại của xe.");
    else if (editing && odo < currentOdometer) {
      VmlForm.setError(form, "current_odometer", `Số km không được nhỏ hơn số hiện tại (${formatNumber(currentOdometer)} km).`);
    }
    if (year !== null && (!/^\d{4}$/.test(yearText) || year < 1950 || year > 2100)) {
      VmlForm.setError(form, "manufacture_year", "Năm sản xuất từ 1950 đến 2100.");
    }
    if (purchase && purchase > VmlForm.todayIso()) VmlForm.setError(form, "purchase_date", "Ngày mua không được ở tương lai.");
    if (form.querySelector("[aria-invalid='true']")) {
      VmlForm.focusFirstError(form);
      return null;
    }
    return {
      name,
      vehicle_type: vehicleType,
      brand: input("brand").value.trim() || null,
      model: input("model").value.trim() || null,
      manufacture_year: year,
      license_plate: input("license_plate").value.trim() || null,
      current_odometer: odo,
      purchase_date: purchase || null,
    };
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const body = validate();
    if (!body) return;
    save.disabled = true;
    try {
      const saved = await VmlForm.sendJson(editing ? `/api/vehicles/${vehicleId}` : "/api/vehicles", editing ? "PUT" : "POST", body);
      location.href = `/xe/${saved.id}?saved=1`;
    } catch (error) {
      save.disabled = false;
      const code = error.body && error.body.error_code;
      if (code === "DUPLICATE_PLATE") VmlForm.setError(form, "license_plate", error.message);
      else if (code === "ODOMETER_DECREASE") VmlForm.setError(form, "current_odometer", error.message);
      else if (code === "VEHICLE_NOT_FOUND") showError(error.message);
      else VmlForm.showServerError(form, error);
      VmlForm.focusFirstError(form);
    }
  });

  typeChips.forEach((chip) => chip.addEventListener("click", () => setType(chip.dataset.type)));
  form.addEventListener("input", updatePreview);
  VmlForm.clearErrorOnInput(form);
  VmlForm.bindDigits(input("current_odometer"));
  input("purchase_date").max = VmlForm.todayIso();

  async function init() {
    updatePreview();
    if (!editing) return;
    save.disabled = true;
    try {
      fill(await fetchJson(`/api/vehicles/${vehicleId}`));
      save.disabled = false;
    } catch (error) {
      showError(error.message);
    }
  }

  init();
})();
