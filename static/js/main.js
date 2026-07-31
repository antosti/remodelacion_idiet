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

  const confirmModal = document.getElementById("confirmActionModal");
  const confirmTitle = document.getElementById("confirmActionTitle");
  const confirmMessage = document.getElementById("confirmActionMessage");
  const confirmAcceptBtn = document.getElementById("confirmActionAccept");
  const confirmCancelBtn = document.getElementById("confirmActionCancel");
  const confirmCloseBtn = document.getElementById("confirmActionClose");
  const confirmBackdrop = document.getElementById("confirmActionBackdrop");
  let pendingAcceptAction = null;
  let pendingCloseAction = null;

  const closeConfirmModal = () => {
    confirmModal?.classList.add("hidden");
    const onClose = pendingCloseAction;
    pendingAcceptAction = null;
    pendingCloseAction = null;
    onClose?.();
  };

  const openModal = (mode, message, { title, onAccept, onClose } = {}) => {
    if (!confirmModal || !confirmMessage) {
      if (mode === "alert") {
        window.alert(message);
        onClose?.();
      } else if (window.confirm(message)) {
        onAccept?.();
      }
      return;
    }

    confirmMessage.textContent = message;
    pendingAcceptAction = onAccept || null;
    pendingCloseAction = onClose || null;

    if (mode === "alert") {
      confirmTitle.textContent = title || "Aviso";
      confirmAcceptBtn.textContent = "Aceptar";
      confirmCancelBtn?.classList.add("hidden");
    } else {
      confirmTitle.textContent = title || "Confirmar acción";
      confirmAcceptBtn.textContent = "Confirmar";
      confirmCancelBtn?.classList.remove("hidden");
    }

    confirmModal.classList.remove("hidden");
  };

  const openConfirmModal = (message, onAccept) => {
    openModal("confirm", message, { onAccept });
  };

  window.showAlertModal = (message, onClose) => {
    openModal("alert", message, { onClose });
  };

  confirmAcceptBtn?.addEventListener("click", () => {
    const action = pendingAcceptAction;
    closeConfirmModal();
    action?.();
  });
  confirmCancelBtn?.addEventListener("click", closeConfirmModal);
  confirmCloseBtn?.addEventListener("click", closeConfirmModal);
  confirmBackdrop?.addEventListener("click", closeConfirmModal);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeConfirmModal();
  });

  document.querySelectorAll("[data-confirm]").forEach((element) => {
    const eventName = element.tagName === "FORM" ? "submit" : "click";
    element.addEventListener(eventName, (event) => {
      event.preventDefault();
      openConfirmModal(element.dataset.confirm, () => {
        if (element.tagName === "FORM") {
          element.submit();
        } else if (element.tagName === "A") {
          window.location.href = element.href;
        } else if (element.form) {
          element.form.requestSubmit(element);
        }
      });
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
