/* Scroll motion.

   Client: "anade mas movimiento, las partes no tienen que moverse todas a la
   misma velocidad o direccion... deberia sentirse muy suave."

   Two systems:
     1. entrance   — elements carry data-anim="up|left|right|scale|blur|fade|..."
                     and reveal once, each with its own distance and duration
     2. parallax   — elements carry data-parallax="<rate>" and drift at that
                     fraction of scroll distance, so nothing tracks together

   Safety: the CSS only hides things under `.js`, so a script failure leaves the
   page fully visible; a sweep guarantees nothing stays hidden after it has been
   scrolled past; and prefers-reduced-motion disables all of it. */
(function () {
  "use strict";

  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
  var animated = function () { return document.querySelectorAll("[data-anim], .stagger"); };

  function showAll() {
    var els = animated();
    for (var i = 0; i < els.length; i++) els[i].classList.add("is-in");
  }

  if (reduce.matches || !("IntersectionObserver" in window)) {
    showAll();
    return;
  }

  // ---- entrances -------------------------------------------------------
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (!e.isIntersecting) return;
      e.target.classList.add("is-in");
      io.unobserve(e.target);
    });
  }, { rootMargin: "0px 0px -8% 0px", threshold: 0 });

  animated().forEach(function (el) { io.observe(el); });

  // Batched observer callbacks can be outrun by a fast flick, which would leave
  // a section stranded at opacity 0. Anything already past the viewport bottom
  // is revealed regardless.
  function sweep() {
    var pending = document.querySelectorAll("[data-anim]:not(.is-in), .stagger:not(.is-in)");
    for (var i = 0; i < pending.length; i++) {
      if (pending[i].getBoundingClientRect().top < window.innerHeight) {
        pending[i].classList.add("is-in");
        io.unobserve(pending[i]);
      }
    }
  }
  window.addEventListener("load", sweep);

  // ---- parallax --------------------------------------------------------
  // Rate is per element, so a section's image, heading and card all travel at
  // different speeds. Kept small: the largest is 0.18 of scroll distance.
  var layers = [].slice.call(document.querySelectorAll("[data-parallax]")).map(function (el) {
    return { el: el, rate: parseFloat(el.getAttribute("data-parallax")) || 0.08 };
  });
  var heroes = [].slice.call(document.querySelectorAll(".hero-media"));

  var ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(function () {
      var y = window.pageYOffset;
      var vh = window.innerHeight;

      heroes.forEach(function (h) {
        var top = h.getBoundingClientRect().top + y;
        var d = (y - top) * 0.14;
        if (d > -80 && d < 300) h.style.setProperty("--drift", d.toFixed(1) + "px");
      });

      layers.forEach(function (l) {
        var r = l.el.getBoundingClientRect();
        if (r.bottom < -200 || r.top > vh + 200) return;   // skip far-offscreen work
        // 0 when the element is centred in the viewport, signed either side
        var fromCentre = (r.top + r.height / 2) - vh / 2;
        l.el.style.setProperty("--py", (-fromCentre * l.rate).toFixed(1) + "px");
      });

      sweep();
      ticking = false;
    });
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll, { passive: true });
  onScroll();

  var onChange = function (e) {
    if (!e.matches) return;
    window.removeEventListener("scroll", onScroll);
    heroes.forEach(function (h) { h.style.removeProperty("--drift"); });
    layers.forEach(function (l) { l.el.style.removeProperty("--py"); });
    showAll();
  };
  if (reduce.addEventListener) reduce.addEventListener("change", onChange);
  else if (reduce.addListener) reduce.addListener(onChange);
})();
