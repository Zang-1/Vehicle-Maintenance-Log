// Sign-in and sign-up pages (FR-23, FR-24). The server sets the session cookie; we only go to the next page.
(function () {
  "use strict";

  const form = document.getElementById("auth-form");
  const errorBox = document.getElementById("auth-error");
  const next = form.dataset.next || "/";

  function showProblem(message) {
    errorBox.textContent = message;
    errorBox.hidden = false;
  }

  // Checked here first so the common mistakes get a clear sentence; the server checks again (RegisterIn).
  function problem(data) {
    if (form.elements.display_name && !data.display_name) return "Hãy nhập tên của bạn.";
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(data.email)) return "Email chưa đúng, ví dụ: ban@gmail.com.";
    if (form.elements.display_name && data.password.length < 8) return "Mật khẩu cần ít nhất 8 ký tự.";
    if (!data.password) return "Hãy nhập mật khẩu.";
    return null;
  }

  async function send(url, data, button) {
    button.disabled = true;
    errorBox.hidden = true;
    try {
      await fetchJson(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: data ? JSON.stringify(data) : undefined,
      });
      location.href = next;
    } catch (error) {
      showProblem(error.status === 422 ? "Thông tin chưa hợp lệ. Hãy kiểm tra lại." : error.message);
      button.disabled = false;
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(form));
    data.email = (data.email || "").trim().toLowerCase();
    if (data.display_name !== undefined) data.display_name = data.display_name.trim();
    const message = problem(data);
    if (message) {
      showProblem(message);
      return;
    }
    send(form.dataset.url, data, form.querySelector("[type=submit]"));
  });

  const demo = document.getElementById("demo-btn");
  if (demo) demo.addEventListener("click", () => send("/api/auth/demo", null, demo));
})();
