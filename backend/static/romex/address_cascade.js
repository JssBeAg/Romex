/* Cascading dropdowns of the address: state -> municipality.
   Choosing a state asks for its municipalities (INEGI's catalog, through the server). */
(function () {
  "use strict";

  function field(name) {
    return document.getElementById("id_" + name);
  }

  document.addEventListener("DOMContentLoaded", function () {
    var state = field("state");
    var municipality = field("municipality");
    if (!state || !municipality || !state.dataset.optionsUrl) return;

    state.addEventListener("change", function () {
      municipality.innerHTML = "";
      var empty = document.createElement("option");
      empty.value = "";
      empty.textContent = "---------";
      municipality.appendChild(empty);
      if (!state.value) return;

      fetch(state.dataset.optionsUrl + "?state=" + encodeURIComponent(state.value), {
        credentials: "same-origin",
      })
        .then(function (response) {
          return response.json();
        })
        .then(function (data) {
          (data.options || []).forEach(function (name) {
            var element = document.createElement("option");
            element.value = name;
            element.textContent = name;
            municipality.appendChild(element);
          });
        });
    });
  });
})();
