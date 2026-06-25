document.addEventListener('DOMContentLoaded', () => {
  const selectAllCheckbox = document.getElementById('selectAllClients');
  const clientCheckboxes = Array.from(document.querySelectorAll('.client-checkbox'));
  const bulkActionBar = document.getElementById('bulkActionBar');
  const selectedCount = document.getElementById('selectedCount');
  const bulkClientInputs = document.getElementById('bulkClientInputs');
  const cancelBulkSelectionBtn = document.getElementById('cancelBulkSelectionBtn');

  const updateBulkSelection = () => {
    const selectedCheckboxes = clientCheckboxes.filter((checkbox) => checkbox.checked);
    const selectedCountValue = selectedCheckboxes.length;

    if (bulkActionBar) {
      bulkActionBar.classList.toggle('hidden', selectedCountValue === 0);
    }

    if (selectedCount) {
      selectedCount.textContent = selectedCountValue;
    }

    if (bulkClientInputs) {
      bulkClientInputs.innerHTML = '';
      selectedCheckboxes.forEach((checkbox) => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'selected_clients';
        input.value = checkbox.dataset.clientId;
        bulkClientInputs.appendChild(input);
      });
    }

    if (selectAllCheckbox) {
      selectAllCheckbox.checked = selectedCountValue > 0 && selectedCountValue === clientCheckboxes.length;
    }
  };

  if (selectAllCheckbox) {
    selectAllCheckbox.addEventListener('change', () => {
      clientCheckboxes.forEach((checkbox) => {
        checkbox.checked = selectAllCheckbox.checked;
      });
      updateBulkSelection();
    });
  }

  clientCheckboxes.forEach((checkbox) => {
    checkbox.addEventListener('change', updateBulkSelection);
  });

  if (cancelBulkSelectionBtn) {
    cancelBulkSelectionBtn.addEventListener('click', () => {
      clientCheckboxes.forEach((checkbox) => {
        checkbox.checked = false;
      });
      updateBulkSelection();
    });
  }

  updateBulkSelection();
});
