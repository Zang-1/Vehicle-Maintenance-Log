// Helpers for the forms of Xe and Bảo dưỡng (Lâm, M2 and M3). Pages use them as window.VmlForm.
// They build on app.js (el, fetchJson, showError, formatNumber). Nothing here is global except VmlForm.
(function () {
  "use strict";

  const TYPE_LABEL = { MOTORBIKE: "Xe máy", CAR: "Ô tô", OTHER: "Loại khác" };

  function digits(text) {
    return String(text ?? "").replace(/\D/g, "");
  }

  // "135000" -> "135.000": the way Vietnamese write amounts and kilometres. "" stays "".
  function groupDigits(text) {
    const d = digits(text);
    return d ? formatNumber(Number(d)) : "";
  }

  // "135.000" -> 135000, "" -> null
  function toInt(text) {
    const d = digits(text);
    return d ? Number(d) : null;
  }

  // Quantity: "2", "0,5" or "0.5" -> number, anything else -> null (at most 2 decimals, like the database)
  function toQuantity(text) {
    const s = String(text ?? "").trim().replace(",", ".");
    return /^\d+(\.\d{1,2})?$/.test(s) ? Number(s) : null;
  }

  // Keep a number box grouped while typing and keep the caret next to the digit being edited.
  function bindDigits(input) {
    input.addEventListener("input", () => {
      const caret = input.selectionStart ?? input.value.length;
      const before = digits(input.value.slice(0, caret)).length;
      input.value = groupDigits(input.value);
      let pos = 0;
      let seen = 0;
      while (pos < input.value.length && seen < before) {
        if (/\d/.test(input.value[pos])) seen += 1;
        pos += 1;
      }
      input.setSelectionRange(pos, pos);
    });
  }

  function todayIso() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  }

  function fieldOf(form, name) {
    return form.querySelector(`[data-field="${name}"]`);
  }

  // Put a message under the field; returns false when the form has no such field.
  function setError(form, name, message) {
    const field = fieldOf(form, name);
    if (!field) return false;
    const control = field.querySelector(".control");
    if (control) control.setAttribute("aria-invalid", "true");
    let box = field.querySelector(".field-error");
    if (!box) {
      box = el("span", "field-error");
      box.setAttribute("role", "alert");
      field.append(box);
    }
    box.textContent = message;
    const disc = field.closest("details");
    if (disc) disc.open = true; // never hide an error inside a closed "more details" section
    return true;
  }

  function clearErrors(form) {
    form.querySelectorAll("[aria-invalid]").forEach((node) => node.removeAttribute("aria-invalid"));
    form.querySelectorAll(".field-error").forEach((node) => node.remove());
    document.getElementById("error").hidden = true;
  }

  // The message of a field goes away as soon as the user edits that field.
  function clearErrorOnInput(form) {
    const clear = (event) => {
      const field = event.target.closest("[data-field]");
      if (!field) return;
      field.querySelectorAll("[aria-invalid]").forEach((node) => node.removeAttribute("aria-invalid"));
      field.querySelectorAll(".field-error").forEach((node) => node.remove());
    };
    form.addEventListener("input", clear);
    form.addEventListener("change", clear);
  }

  function focusFirstError(form) {
    const bad = form.querySelector("[aria-invalid='true']");
    if (bad) {
      bad.focus();
      bad.scrollIntoView({ block: "center" });
    }
  }

  async function sendJson(url, method, body) {
    return fetchJson(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  }

  // FastAPI's 422 body is {detail: [{loc: ["body", "field"], msg}]}. Put each message under its own field;
  // resolve(loc) may map a location to another field name (the record form has one row per item).
  function showServerError(form, error, resolve) {
    const detail = error.body && Array.isArray(error.body.detail) ? error.body.detail : null;
    if (!detail) {
      showError(error.message);
      return;
    }
    let placed = 0;
    for (const item of detail) {
      const name = resolve ? resolve(item.loc) : item.loc.filter((p) => typeof p === "string").pop();
      const text = item.msg.startsWith("Value error, ") ? item.msg.slice(13) : "Giá trị chưa hợp lệ.";
      if (name && setError(form, name, text)) placed += 1;
    }
    if (placed) focusFirstError(form);
    else showError("Dữ liệu chưa hợp lệ, hãy kiểm tra lại các ô đã nhập.");
  }

  // Show "saved" once on the page the form sent the user to (?saved=1), then clean the address.
  function toastIfSaved(message) {
    const params = new URLSearchParams(location.search);
    if (!params.has("saved")) return;
    showToast(message);
    params.delete("saved");
    const query = params.toString();
    history.replaceState(null, "", location.pathname + (query ? `?${query}` : "") + location.hash);
  }

  // "Honda Wave Alpha · 2020"
  function vehicleSubtitle(v) {
    const name = [v.brand, v.model].filter(Boolean).join(" ");
    return [name, v.manufacture_year].filter(Boolean).join(" · ");
  }

  window.VmlForm = {
    TYPE_LABEL,
    digits,
    groupDigits,
    toInt,
    toQuantity,
    bindDigits,
    todayIso,
    setError,
    clearErrors,
    clearErrorOnInput,
    focusFirstError,
    sendJson,
    showServerError,
    toastIfSaved,
    vehicleSubtitle,
  };
})();
