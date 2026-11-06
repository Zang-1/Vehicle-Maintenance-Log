// S07 Thêm / Sửa nhắc lịch (FR-13, FR-14): POST /api/vehicles/{id}/reminders, or PUT /api/reminders/{id}.
// The service type never changes after creation; the start mark is left to the API (BR-07).
(function () {
  "use strict";

  const form = document.getElementById("reminder-form");
  const reminderId = form.dataset.reminderId;
  const editing = reminderId !== "";
  const save = document.getElementById("save");
  const input = (name) => form.elements[name];
  const select = editing ? null : input("service_type_id");

  let vehicleId = form.dataset.vehicleId ? Number(form.dataset.vehicleId) : null;
  let serviceTypes = [];
  let lockedTypeId = null; // edit: the reminder's own service type

  function backUrl() {
    return vehicleId ? `/xe/${vehicleId}` : "/xe";
  }

  function setVehicleLine(name, odometer) {
    document.getElementById("vehicle-line").textContent = `Xe: ${name} · đang ở ${formatNumber(odometer)} km`;
  }

  function setBackLinks() {
    document.getElementById("back-link").href = backUrl();
    document.getElementById("cancel-link").href = backUrl();
  }

  // The chosen type fills the interval boxes with its default (the user can still change them).
  function applyTypeDefaults() {
    const type = serviceTypes.find((t) => String(t.id) === select.value);
    input("interval_km").value = type && type.default_interval_km ? VmlForm.groupDigits(type.default_interval_km) : "";
    input("interval_months").value = type && type.default_interval_months ? String(type.default_interval_months) : "";
  }

  function fillTypes(vehicle, types, reminders) {
    const used = new Set(reminders.map((r) => r.service_type_id)); // BR-06: one reminder per type
    serviceTypes = types.filter(
      (t) => t.is_active && (t.applies_to === "ALL" || t.applies_to === vehicle.vehicle_type),
    );
    select.replaceChildren(
      ...serviceTypes.map((t) => {
        const option = new Option(used.has(t.id) ? `${t.name} (đã có nhắc lịch)` : t.name, String(t.id));
        option.disabled = used.has(t.id);
        return option;
      }),
    );
    const wanted = new URLSearchParams(location.search).get("loai");
    const preferred = serviceTypes.find((t) => String(t.id) === wanted && !used.has(t.id));
    const first = serviceTypes.find((t) => !used.has(t.id));
    const choice = preferred || first;
    if (choice) {
      select.value = String(choice.id);
      applyTypeDefaults();
    } else {
      save.disabled = true;
      VmlForm.setError(form, "service_type_id", "Xe này đã có nhắc lịch cho mọi việc bảo dưỡng phù hợp.");
    }
  }

  function fillReminder(r) {
    vehicleId = r.vehicle_id;
    lockedTypeId = r.service_type_id;
    document.getElementById("type-name").textContent = r.service_type_name;
    setVehicleLine(r.vehicle_name, r.current_odometer);
    input("interval_km").value = r.interval_km ? VmlForm.groupDigits(r.interval_km) : "";
    input("interval_months").value = r.interval_months ? String(r.interval_months) : "";
    input("notify_before_km").value = VmlForm.groupDigits(r.notify_before_km);
    input("notify_before_days").value = String(r.notify_before_days);
    setBackLinks();
  }

  // Returns the body to send, or null after marking every wrong field.
  function validate() {
    VmlForm.clearErrors(form);
    const km = VmlForm.toInt(input("interval_km").value);
    const months = VmlForm.toInt(input("interval_months").value);
    const nkm = VmlForm.toInt(input("notify_before_km").value);
    const ndays = VmlForm.toInt(input("notify_before_days").value);
    const typeId = editing ? lockedTypeId : Number(select.value);

    if (!typeId) VmlForm.setError(form, "service_type_id", "Hãy chọn việc bảo dưỡng.");
    if (km === null && months === null) {
      VmlForm.setError(form, "interval_km", "Nhập chu kỳ theo km hoặc theo tháng (ít nhất một).");
    }
    if (km !== null && (km < 1 || km > 1000000)) VmlForm.setError(form, "interval_km", "Chu kỳ km từ 1 đến 1.000.000.");
    if (months !== null && (months < 1 || months > 240)) {
      VmlForm.setError(form, "interval_months", "Chu kỳ tháng từ 1 đến 240.");
    }
    if (nkm === null || nkm > 100000) VmlForm.setError(form, "notify_before_km", "Báo trước từ 0 đến 100.000 km.");
    if (ndays === null || ndays > 365) VmlForm.setError(form, "notify_before_days", "Báo trước từ 0 đến 365 ngày.");
    if (form.querySelector("[aria-invalid='true']")) {
      VmlForm.focusFirstError(form);
      return null;
    }
    return {
      service_type_id: typeId,
      interval_km: km,
      interval_months: months,
      notify_before_km: nkm,
      notify_before_days: ndays,
    };
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const body = validate();
    if (!body) return;
    save.disabled = true;
    try {
      await VmlForm.sendJson(
        editing ? `/api/reminders/${reminderId}` : `/api/vehicles/${vehicleId}/reminders`,
        editing ? "PUT" : "POST",
        body,
      );
      location.href = backUrl();
    } catch (error) {
      save.disabled = false;
      const code = error.body && error.body.error_code;
      if (code === "DUPLICATE_REMINDER" || (code && code.startsWith("SERVICE_TYPE"))) {
        VmlForm.setError(form, "service_type_id", error.message);
      } else if (code === "VEHICLE_ARCHIVED" || code === "VEHICLE_NOT_FOUND" || code === "REMINDER_NOT_FOUND") {
        showError(error.message);
      } else {
        VmlForm.showServerError(form, error);
      }
      VmlForm.focusFirstError(form);
    }
  });

  VmlForm.clearErrorOnInput(form);
  ["interval_km", "interval_months", "notify_before_km", "notify_before_days"].forEach((name) =>
    VmlForm.bindDigits(input(name)),
  );
  if (select) select.addEventListener("change", applyTypeDefaults);

  async function init() {
    save.disabled = true;
    try {
      if (editing) {
        fillReminder(await fetchJson(`/api/reminders/${reminderId}`));
      } else {
        const [vehicle, types, reminders] = await Promise.all([
          fetchJson(`/api/vehicles/${vehicleId}`),
          fetchJson("/api/service-types"),
          fetchJson(`/api/vehicles/${vehicleId}/reminders`),
        ]);
        setVehicleLine(vehicle.name, vehicle.current_odometer);
        if (vehicle.is_archived) {
          showError("Xe đã lưu trữ. Hãy khôi phục xe trước khi đặt nhắc lịch.");
          return;
        }
        fillTypes(vehicle, types, reminders);
        if (serviceTypes.length === 0) return;
      }
      save.disabled = false;
    } catch (error) {
      showError(error.message);
    }
  }

  init();
})();
