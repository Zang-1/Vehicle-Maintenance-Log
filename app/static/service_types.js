// Loại việc bảo dưỡng (FR-11, FR-12): one table, filtered in the browser.
// A type that records or reminders use can only be retired; an unused one can be deleted (BR-09).
(function () {
  "use strict";

  const list = document.getElementById("st-list");
  const chips = document.querySelectorAll("#filter .chip");
  const appliesChips = document.querySelectorAll("#applies-chips .chip");
  const dialog = document.getElementById("st-dialog");
  const deleteDialog = document.getElementById("st-delete-dialog");
  const form = document.getElementById("st-form");
  const formError = document.getElementById("st-error");
  const saveButton = document.getElementById("st-save");

  const APPLIES = { ALL: "Mọi loại xe", MOTORBIKE: "Xe máy", CAR: "Ô tô" };
  const MATCH = {
    all: () => true,
    MOTORBIKE: (t) => t.applies_to !== "CAR",
    CAR: (t) => t.applies_to !== "MOTORBIKE",
    active: (t) => t.is_active,
    inactive: (t) => !t.is_active,
  };
  const HEADERS = [["Loại việc", ""], ["Áp dụng cho", ""], ["Chu kỳ km", "r"], ["Chu kỳ tháng", "r"], ["Trạng thái", ""], ["", ""]];

  let types = [];
  let filter = "all";
  let applies = "ALL";
  let editingId = null;
  let deleting = null;

  function cell(label, className, ...children) {
    const td = el("td", className, ...children);
    td.dataset.label = label; // the phone layout prints it in front of the value
    return td;
  }

  function button(label, className, handler) {
    const node = el("button", `btn btn-sm ${className}`, label);
    node.type = "button";
    node.addEventListener("click", handler);
    return node;
  }

  function row(t) {
    const used = t.used_count ? `Đã dùng ${t.used_count} lần` : "Chưa dùng";
    const second = t.used_count
      ? button(t.is_active ? "Ngừng dùng" : "Dùng lại", "btn-ghost", () => setActive(t))
      : button("Xóa", "btn-ghost text-bad", () => askDelete(t));
    return el(
      "tr",
      "",
      cell("", "first", el("b", "", t.name), el("span", "sub", [t.description, used].filter(Boolean).join(" · "))),
      cell("Áp dụng cho", "", el("span", "badge badge-neutral nodot", APPLIES[t.applies_to])),
      cell("Chu kỳ km", "r num", t.default_interval_km ? `${formatNumber(t.default_interval_km)} km` : "—"),
      cell("Chu kỳ tháng", "r num", t.default_interval_months ? `${t.default_interval_months} tháng` : "—"),
      cell("Trạng thái", "", el("span", `badge ${t.is_active ? "badge-ok" : "badge-neutral"}`, t.is_active ? "Đang dùng" : "Ngừng dùng")),
      cell("", "", el("div", "st-actions", button("Sửa", "btn-ghost", () => openDialog(t)), second)),
    );
  }

  function render() {
    document.getElementById("count-all").textContent = types.length;
    const rows = types.filter(MATCH[filter]);
    if (!rows.length) {
      list.replaceChildren(
        el("div", "empty", icon("wrench"), el("p", "empty-title", "Không có loại việc nào"), el("p", "muted", "Thử đổi bộ lọc hoặc thêm loại việc mới.")),
      );
      return;
    }
    const head = el("thead", "", el("tr", "", ...HEADERS.map(([label, className]) => el("th", className, label))));
    list.replaceChildren(el("table", "data-table", head, el("tbody", "", ...rows.map(row))));
  }

  async function load() {
    document.getElementById("error").hidden = true;
    try {
      types = await fetchJson("/api/service-types");
      render();
    } catch (error) {
      showError(error.message);
      list.replaceChildren(el("p", "muted", "Không tải được danh sách loại việc."));
    }
  }

  async function setActive(t) {
    try {
      await VmlForm.sendJson(`/api/service-types/${t.id}/active`, "PATCH", { active: !t.is_active });
      showToast(t.is_active ? "Đã ngừng dùng loại việc này." : "Đã dùng lại loại việc này.");
    } catch (error) {
      showError(error.message);
    }
    load();
  }

  function askDelete(t) {
    deleting = t;
    document.getElementById("st-delete-name").textContent = t.name;
    deleteDialog.showModal();
  }

  document.getElementById("st-delete-confirm").addEventListener("click", async () => {
    deleteDialog.close();
    try {
      await fetchJson(`/api/service-types/${deleting.id}`, { method: "DELETE" });
      showToast("Đã xóa loại việc.");
    } catch (error) {
      showError(error.message); // e.g. a record started using it meanwhile
    }
    load();
  });
  document.getElementById("st-delete-cancel").addEventListener("click", () => deleteDialog.close());

  function setApplies(value) {
    applies = value;
    appliesChips.forEach((chip) => {
      const on = chip.dataset.applies === value;
      chip.classList.toggle("active", on);
      chip.setAttribute("aria-pressed", String(on));
    });
  }

  function openDialog(t) {
    editingId = t ? t.id : null;
    VmlForm.clearErrors(form);
    formError.hidden = true;
    document.getElementById("st-title").textContent = t ? "Sửa loại việc" : "Thêm loại việc";
    document.getElementById("f-name").value = t ? t.name : "";
    document.getElementById("f-desc").value = t && t.description ? t.description : "";
    document.getElementById("f-km").value = t && t.default_interval_km ? VmlForm.groupDigits(t.default_interval_km) : "";
    document.getElementById("f-months").value = t && t.default_interval_months ? String(t.default_interval_months) : "";
    setApplies(t ? t.applies_to : "ALL");
    dialog.showModal();
    document.getElementById("f-name").focus();
  }

  function readForm() {
    VmlForm.clearErrors(form);
    formError.hidden = true;
    const name = document.getElementById("f-name").value.trim();
    const km = VmlForm.toInt(document.getElementById("f-km").value);
    const months = VmlForm.toInt(document.getElementById("f-months").value);
    let ok = true;
    if (!name) {
      VmlForm.setError(form, "name", "Hãy nhập tên loại việc.");
      ok = false;
    }
    if (km === 0) {
      VmlForm.setError(form, "default_interval_km", "Chu kỳ phải lớn hơn 0.");
      ok = false;
    }
    if (months === 0) {
      VmlForm.setError(form, "default_interval_months", "Chu kỳ phải lớn hơn 0.");
      ok = false;
    }
    if (!ok) {
      VmlForm.focusFirstError(form);
      return null;
    }
    return {
      name,
      description: document.getElementById("f-desc").value,
      applies_to: applies,
      default_interval_km: km,
      default_interval_months: months,
    };
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const body = readForm();
    if (!body) return;
    saveButton.disabled = true;
    try {
      const url = editingId ? `/api/service-types/${editingId}` : "/api/service-types";
      await VmlForm.sendJson(url, editingId ? "PUT" : "POST", body);
      dialog.close();
      showToast(editingId ? "Đã lưu thay đổi." : "Đã thêm loại việc.");
      load();
    } catch (error) {
      if (error.status === 409) {
        VmlForm.setError(form, "name", error.message);
        VmlForm.focusFirstError(form);
      } else if (error.body && Array.isArray(error.body.detail)) {
        VmlForm.showServerError(form, error);
      } else {
        formError.textContent = error.message; // #error sits behind the dialog, so show it inside
        formError.hidden = false;
      }
    } finally {
      saveButton.disabled = false;
    }
  });

  VmlForm.bindDigits(document.getElementById("f-km"));
  VmlForm.bindDigits(document.getElementById("f-months"));
  VmlForm.clearErrorOnInput(form);
  appliesChips.forEach((chip) => chip.addEventListener("click", () => setApplies(chip.dataset.applies)));
  document.getElementById("add").addEventListener("click", () => openDialog(null));
  document.getElementById("st-cancel").addEventListener("click", () => dialog.close());
  chips.forEach((chip) =>
    chip.addEventListener("click", () => {
      filter = chip.dataset.filter;
      chips.forEach((other) => {
        const on = other === chip;
        other.classList.toggle("active", on);
        other.setAttribute("aria-pressed", String(on));
      });
      render();
    }),
  );

  load();
})();