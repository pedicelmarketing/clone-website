/* Contact form.

   There is no server behind this build, and the source's form was backed by
   Wix. Rather than ship a form that silently swallows enquiries, the submit
   handler composes a mailto: so the message always reaches the academy.

   Swap this for a real endpoint (Formspree, Brevo, a serverless function)
   when one exists — the markup does not need to change. */
(function () {
  "use strict";

  var TO = "info@nexumpadel.es";
  var form = document.getElementById("contact-form");
  if (!form) return;

  var note = form.querySelector(".form-note");

  function fail(message) {
    if (note) {
      note.textContent = message;
      note.style.color = "#9B3B2E";
    }
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();

    var name = form.elements.name.value.trim();
    var email = form.elements.email.value.trim();
    var message = form.elements.message.value.trim();

    if (!name || !email || !message) {
      fail("Rellena nombre, email y mensaje para continuar.");
      return;
    }

    var subject = "Solicitud de programa — " + name;
    var body =
      "Nombre: " + name + "\n" +
      "Email: " + email + "\n\n" +
      message + "\n";

    window.location.href =
      "mailto:" + TO +
      "?subject=" + encodeURIComponent(subject) +
      "&body=" + encodeURIComponent(body);

    if (note) {
      note.textContent = "Abriendo tu aplicación de correo…";
      note.style.color = "";
    }
  });
})();
