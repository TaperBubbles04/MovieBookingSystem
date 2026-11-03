// Small helpers used on every page. Each one only acts on elements that opt in
// with a class or data attribute, so pages without them are unaffected.
document.addEventListener("DOMContentLoaded", function () {
  // Inputs with data-match="otherId" must equal that field (confirm password).
  document.querySelectorAll("input[data-match]").forEach(function (input) {
    var other = document.getElementById(input.dataset.match);
    function check() {
      input.setCustomValidity(input.value === other.value ? "" : "Passwords do not match");
    }
    input.addEventListener("input", check);
    other.addEventListener("input", check);
  });

  // Required-field checks: forms with class "needs-validation" show Bootstrap's
  // red/green hints instead of submitting while a field is invalid.
  document.querySelectorAll("form.needs-validation").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
      }
      form.classList.add("was-validated");
    });
  });

  // Ask before submitting forms with data-confirm="question".
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (!window.confirm(form.dataset.confirm)) {
        event.preventDefault();
      }
    });
  });

  // Forms with data-single-submit disable their button after the first submit,
  // so a double click cannot send the same request twice.
  document.querySelectorAll("form[data-single-submit]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (event.defaultPrevented) return;
      var button = form.querySelector("[type=submit]");
      if (button) {
        button.disabled = true;
        if (button.dataset.busyText) button.textContent = button.dataset.busyText;
      }
    });
  });

  // Show YYYY-MM-DD values in elements with data-date as "Mon, 27 Oct".
  var today = new Date();
  today.setHours(0, 0, 0, 0);
  document.querySelectorAll("[data-date]").forEach(function (el) {
    var parts = el.dataset.date.split("-");
    if (parts.length !== 3) return;
    var d = new Date(parts[0], parts[1] - 1, parts[2]);
    var days = Math.round((d - today) / 86400000);
    var text = d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });
    if (el.hasAttribute("data-date-relative") && (days === 0 || days === 1)) {
      text = (days === 0 ? "Today, " : "Tomorrow, ") + d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
    }
    el.textContent = text;
  });
});

// When the browser restores a page from its back/forward cache, buttons that
// were disabled on submit would stay disabled. Turn them back on.
window.addEventListener("pageshow", function (event) {
  if (!event.persisted) return;
  document.querySelectorAll("form[data-single-submit] [type=submit]").forEach(function (button) {
    button.disabled = false;
    if (button.dataset.idleText) button.textContent = button.dataset.idleText;
  });
});
