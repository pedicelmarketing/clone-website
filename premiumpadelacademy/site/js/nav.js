/* Mobile navigation.
   The panel itself is positioned and centred in CSS; this only tracks open
   state, so with JS disabled the links still render as a normal nav row. */
(function () {
  "use strict";

  var toggle = document.querySelector(".nav-toggle");
  var nav = document.getElementById("primary-nav");
  if (!toggle || !nav) return;

  function setOpen(open) {
    document.body.classList.toggle("nav-open", open);
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "Cerrar menú" : "Abrir menú");
  }

  toggle.addEventListener("click", function () {
    setOpen(!document.body.classList.contains("nav-open"));
  });

  // Following a link should close the panel — including same-page hashes,
  // which do not trigger a reload.
  nav.addEventListener("click", function (e) {
    if (e.target.closest("a")) setOpen(false);
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && document.body.classList.contains("nav-open")) {
      setOpen(false);
      toggle.focus();
    }
  });

  // Resizing past the breakpoint must not leave a hidden panel holding the
  // body scroll lock.
  var wide = window.matchMedia("(min-width: 861px)");
  (wide.addEventListener ? wide.addEventListener.bind(wide, "change") : wide.addListener.bind(wide))(
    function (e) { if (e.matches) setOpen(false); }
  );

  setOpen(false);
})();
