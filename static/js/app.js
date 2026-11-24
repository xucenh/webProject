(function () {
  "use strict";

  // Show doctor-specific signup fields only for the doctor role.
  var roleInputs = document.querySelectorAll('input[name="role"]');
  var doctorFields = document.getElementById("doctor-fields");

  function syncDoctorFields() {
    if (!doctorFields) return;
    var selected = document.querySelector('input[name="role"]:checked');
    doctorFields.hidden = !selected || selected.value !== "doctor";
  }

  roleInputs.forEach(function (input) {
    input.addEventListener("change", syncDoctorFields);
  });
  syncDoctorFields();

  // Confirmation dialog for destructive forms.
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (!window.confirm(form.getAttribute("data-confirm"))) {
        event.preventDefault();
      }
    });
  });
})();
