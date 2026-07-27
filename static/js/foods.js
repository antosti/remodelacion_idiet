document.addEventListener('DOMContentLoaded', () => {
  const selectAllCheckbox = document.getElementById('selectAllFoods');
  const foodCheckboxes = Array.from(document.querySelectorAll('.food-checkbox'));
  const bulkActionBar = document.getElementById('bulkActionBar');
  const selectedCount = document.getElementById('selectedCount');
  const bulkFoodInputs = document.getElementById('bulkFoodInputs');
  const bulkDeleteFoodInputs = document.getElementById('bulkDeleteFoodInputs');
  const cancelBulkSelectionBtn = document.getElementById('cancelBulkSelectionBtn');

  const updateBulkSelection = () => {
    const selectedCheckboxes = foodCheckboxes.filter((checkbox) => checkbox.checked);
    const selectedCountValue = selectedCheckboxes.length;

    if (bulkActionBar) {
      bulkActionBar.classList.toggle('hidden', selectedCountValue === 0);
    }

    if (selectedCount) {
      selectedCount.textContent = selectedCountValue;
    }

    const bulkInputContainers = [bulkFoodInputs, bulkDeleteFoodInputs].filter(Boolean);
    bulkInputContainers.forEach((container) => {
      container.innerHTML = '';
      selectedCheckboxes.forEach((checkbox) => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'selected_foods';
        input.value = checkbox.dataset.foodId;
        container.appendChild(input);
      });
    });

    if (selectAllCheckbox) {
      selectAllCheckbox.checked =
        selectedCountValue > 0 && selectedCountValue === foodCheckboxes.length;
      selectAllCheckbox.indeterminate =
        selectedCountValue > 0 && selectedCountValue < foodCheckboxes.length;
    }
  };

  if (selectAllCheckbox) {
    selectAllCheckbox.addEventListener('change', () => {
      foodCheckboxes.forEach((checkbox) => {
        checkbox.checked = selectAllCheckbox.checked;
      });
      updateBulkSelection();
    });
  }

  foodCheckboxes.forEach((checkbox) => {
    checkbox.addEventListener('change', updateBulkSelection);
  });

  if (cancelBulkSelectionBtn) {
    cancelBulkSelectionBtn.addEventListener('click', () => {
      foodCheckboxes.forEach((checkbox) => {
        checkbox.checked = false;
      });
      updateBulkSelection();
    });
  }

  updateBulkSelection();
});
