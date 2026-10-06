/* Pedicel Marketing - form submit shim.
 *
 * The captured Webflow forms declare method="get" with no action. On Webflow hosting,
 * webflow.js intercepts submit and AJAX-POSTs to Webflow's endpoint keyed on data-wf-site.
 * Self-hosted that binding is gone and the failure is SILENT: the browser falls back to
 * method="get", reloads the page with the fields in the query string, and the visitor
 * believes it worked. This shim routes the submit to our own relay instead.
 *
 * It listens on the CAPTURE phase at document level so it runs before webflow.js's
 * jQuery-delegated bubble-phase handler, then stops propagation so webflow.js never sees
 * the event. Webflow's own .w-form-done / .w-form-fail elements are reused, so success and
 * error states look and behave exactly as they did on Webflow.
 */
(function () {
  "use strict";

  var ENDPOINTS = {
    "wf-form-Audit-Form": "/api/forms/ch-audit",
    "wf-form-Email-Form-Version-Two": "/api/forms/ch-contact"
  };

  function wrapperOf(form) {
    var node = form.parentNode;
    while (node && node !== document.body) {
      if (node.classList && node.classList.contains("w-form")) return node;
      node = node.parentNode;
    }
    return form.parentNode;
  }

  function show(form, which) {
    var wrap = wrapperOf(form);
    if (!wrap) return;
    var done = wrap.querySelector(".w-form-done");
    var fail = wrap.querySelector(".w-form-fail");
    if (which === "done") {
      form.style.display = "none";
      if (done) done.style.display = "block";
      if (fail) fail.style.display = "none";
    } else {
      if (fail) fail.style.display = "block";
      if (done) done.style.display = "none";
    }
  }

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!form || form.tagName !== "FORM") return;

    var endpoint = ENDPOINTS[form.getAttribute("id")] || ENDPOINTS[form.getAttribute("name")];
    if (!endpoint) return;

    event.preventDefault();
    event.stopPropagation();
    if (event.stopImmediatePropagation) event.stopImmediatePropagation();

    var button = form.querySelector('input[type="submit"], button[type="submit"]');
    var original = "";
    if (button) {
      original = button.value || button.textContent;
      var waiting = button.getAttribute("data-wait") || "Please wait...";
      if (button.value !== undefined && button.tagName === "INPUT") button.value = waiting;
      else button.textContent = waiting;
      button.disabled = true;
    }

    var body = new URLSearchParams(new FormData(form)).toString();

    fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8" },
      body: body
    })
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (data) {
        if (!data || data.ok !== true) throw new Error("relay rejected");
        show(form, "done");
      })
      .catch(function (error) {
        // Surfacing the real reason beats a silent failure - this is the exact bug the
        // shim exists to fix, so never fail quietly here.
        if (window.console && console.error) console.error("form submit failed:", error);
        show(form, "fail");
      })
      .finally(function () {
        if (button) {
          button.disabled = false;
          if (button.value !== undefined && button.tagName === "INPUT") button.value = original;
          else button.textContent = original;
        }
      });
  }, true); // capture phase - must beat webflow.js
})();
