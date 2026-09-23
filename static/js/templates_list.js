document.addEventListener('DOMContentLoaded', () => {
  const selectAll = document.getElementById('selectAllTemplates');
  const checkboxes = Array.from(document.querySelectorAll('.template-checkbox'));
  const bulkActionBar = document.getElementById('bulkActionBar');
  const selectedCount = document.getElementById('selectedCount');
  const bulkInputs = document.getElementById('bulkTemplateInputs');
  const cancelBulk = document.getElementById('cancelBulkSelectionBtn');

  const updateBulkSelection = () => {
    const selected = checkboxes.filter((checkbox) => checkbox.checked);
    if (bulkActionBar) {
      bulkActionBar.classList.toggle('hidden', selected.length === 0);
    }
    if (selectedCount) {
      selectedCount.textContent = selected.length;
    }
    if (bulkInputs) {
      bulkInputs.innerHTML = '';
      selected.forEach((checkbox) => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'selected_templates';
        input.value = checkbox.dataset.templateId;
        bulkInputs.appendChild(input);
      });
    }
    if (selectAll) {
      selectAll.checked = selected.length > 0 && selected.length === checkboxes.length;
      selectAll.indeterminate = selected.length > 0 && selected.length < checkboxes.length;
    }
  };

  if (selectAll) {
    selectAll.addEventListener('change', () => {
      checkboxes.forEach((checkbox) => {
        checkbox.checked = selectAll.checked;
      });
      updateBulkSelection();
    });
  }
  checkboxes.forEach((checkbox) => {
    checkbox.addEventListener('change', updateBulkSelection);
  });
  if (cancelBulk) {
    cancelBulk.addEventListener('click', () => {
      checkboxes.forEach((checkbox) => {
        checkbox.checked = false;
      });
      updateBulkSelection();
    });
  }

  const setBodyScroll = () => {
    const editModal = document.getElementById('editTemplateModal');
    document.body.classList.toggle('overflow-hidden', !!editModal && !editModal.classList.contains('hidden'));
  };

  const editModal = document.getElementById('editTemplateModal');
  const editForm = document.getElementById('editTemplateForm');
  const closeEditButtons = document.querySelectorAll('[data-close-edit-modal]');

  const closeEditModal = () => {
    if (!editModal) return;
    editModal.classList.add('hidden');
    setBodyScroll();
  };

  document.querySelectorAll('.edit-template-btn').forEach((button) => {
    button.addEventListener('click', () => {
      editForm.action = button.dataset.action;
      document.getElementById('editTemplateName').value = button.dataset.name;
      editModal.classList.remove('hidden');
      setBodyScroll();
    });
  });
  closeEditButtons.forEach((button) => {
    button.addEventListener('click', closeEditModal);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    closeEditModal();
  });

  setBodyScroll();
  updateBulkSelection();
});
