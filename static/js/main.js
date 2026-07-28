document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-alert]").forEach((alert) => {
    setTimeout(() => {
      alert.classList.add("opacity-0", "translate-x-8");
      setTimeout(() => alert.remove(), 300);
    }, 4000);
  });

  document.querySelectorAll("[data-dismiss-alert]").forEach((button) => {
    button.addEventListener("click", () => {
      button.closest("[data-alert]")?.remove();
    });
  });

  document.querySelectorAll("[data-confirm]").forEach((element) => {
    const eventName = element.tagName === "FORM" ? "submit" : "click";
    element.addEventListener(eventName, (event) => {
      if (!window.confirm(element.dataset.confirm)) {
        event.preventDefault();
      }
    });
  });

  document.querySelectorAll("[data-stop-propagation]").forEach((element) => {
    element.addEventListener("click", (event) => event.stopPropagation());
  });

  const deactivatedAppointmentsTable = document.querySelector(
    "[data-deactivated-appointments-table]"
  );
  if (deactivatedAppointmentsTable) {
    const toggleAll = deactivatedAppointmentsTable.querySelector("thead input[type='checkbox']");
    const checkboxes = Array.from(
      deactivatedAppointmentsTable.querySelectorAll("tbody input[type='checkbox']")
    );
    const bulkActionBar = document.getElementById("bulkActionBar");
    const selectedCount = document.getElementById("selectedCount");
    const cancelButton = document.getElementById("cancelBulkActionBtn");
    const inputContainers = [
      document.getElementById("deleteBulkInputs"),
      document.getElementById("reactivateBulkInputs"),
    ];

    const updateAppointmentSelection = () => {
      const selected = checkboxes.filter((checkbox) => checkbox.checked);
      bulkActionBar.classList.toggle("hidden", selected.length === 0);
      selectedCount.textContent = selected.length
        ? `${selected.length} cita(s) seleccionada(s)`
        : "0 citas seleccionadas";

      inputContainers.forEach((container) => {
        container.innerHTML = "";
        selected.forEach((checkbox) => {
          const input = document.createElement("input");
          input.type = "hidden";
          input.name = "appointment_ids";
          input.value = checkbox.value;
          container.appendChild(input);
        });
      });
    };

    toggleAll?.addEventListener("change", () => {
      checkboxes.forEach((checkbox) => {
        checkbox.checked = toggleAll.checked;
      });
      updateAppointmentSelection();
    });
    checkboxes.forEach((checkbox) => {
      checkbox.addEventListener("change", updateAppointmentSelection);
    });
    cancelButton?.addEventListener("click", () => {
      if (toggleAll) toggleAll.checked = false;
      checkboxes.forEach((checkbox) => {
        checkbox.checked = false;
      });
      updateAppointmentSelection();
    });
  }
});
