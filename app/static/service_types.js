// Loại việc bảo dưỡng (FR-11, FR-12): GET /api/service-types, then add/edit in a dialog, retire instead of delete (BR-09).
(function () {
  "use strict";

  const list = document.getElementById("st-list");
  const chips = document.querySelectorAll("#filter .chip");
  const appliesChips = document.querySelectorAll("#applies-chips .chip");
  const dialog = document.getElementById("st-dialog");
  const form = document.getElementById("st-form");
  const formError = document.getElementById("st-error");
  const saveButton = document.getElementById("st-save");

  const APPLIES = { ALL: "Mọi loại xe", MOTORBIKE: "Xe máy", CAR: "Ô tô" };
  const QUERY = { active: "?active=true", inactive: "?active=false", all: "" };
  const EMPTY = {
    active: ["Chưa có loại việc nào", "Thêm loại việc đầu tiên để dùng khi ghi bảo dưỡng và đặt nhắc."],
    inactive: ["Chưa có loại việc nào ngừng dùng", "Loại việc đã ngừng dùng hiện ở đây; lịch sử cũ vẫn giữ nguyên."],
    all: ["Chưa có loại việc nào", "Thêm loại việc đầu tiên để dùng khi ghi bảo dưỡng và đặt nhắc."],
  };

  let filter = "active";
  let applies = "ALL";
  let editingId = null;

  function intervalText(t) {
    const parts = [];
    if (t.default_interval_km) parts.push(`${formatNumber(t.default_interval_km)} km`);
    if (t.default_interval_months) parts.push(`${t.default_interval_months} tháng`);
    return parts.length ? `Chu kỳ: ${parts.join(" hoặc ")}` : "Chưa đặt chu kỳ";
  }

  function row(t) {
    const edit = el("button", "btn btn-secondary", "Sửa");
    edit.type = "button";
    edit.addEventListener("click", () => openDialog(t));
    const toggle = el("button", "btn btn-secondary", t.is_active ? "Ngừng dùng" : "Dùng lại");
    toggle.type = "button";
    toggle.addEventListener("click", () => setActive(t));
    return el(
      "div",
      `card st-row${t.is_active ? "" : " is-archived"}`,
      el(
        "div",
        "st-main",
        el("b", "", t.name),
        el("span", "row-sub", `${APPLIES[t.applies_to]} · ${intervalText(t)}`),
        t.description ? el("span", "muted", t.description) : null,
      ),
      t.is_active ? null : el("span", "badge badge-neutral", "Ngừng dùng"),
      el("div", "st-actions", edit, toggle),
    );
  }

  function render(items) {
    if (!items.length) {
      const [title, sub] = EMPTY[filter];
      list.replaceChildren(el("div", "card empty", el("p", "empty-title", title), el("p", "muted", sub)));
      return;
    }
    list.replaceChildren(...items.map(row));
  }

  async function load() {
    document.getElementById("error").hidden = true;
    try {
      render(await fetchJson(`/api/service-types${QUERY[filter]}`));
    } catch (error) {
      showError(error.message);
      list.replaceChildren(el("p", "muted", "Không tải được danh sách loại việc."));
    }
  }

  async function setActive(t) {
    try {
      await VmlForm.sendJson(`/api/service-types/${t.id}/active`, "PATCH", { active: !t.is_active });
      showToast(t.is_active ? "Đã ngừng dùng loại việc này." : "Đã dùng lại loại việc này.");
      load();
    } catch (error) {
      showError(error.message);
    }
  }

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
        formError.textContent = error.message; // #error sits behind the modal, so show it inside
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
      load();
    }),
  );

  load();
})();