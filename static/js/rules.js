document.addEventListener('DOMContentLoaded', () => {
  const createModal = document.getElementById('ruleModal');
  const openCreateButton = document.getElementById('openRuleModal');
  const closeCreateButtons = document.querySelectorAll('[data-close-rule-modal]');

  const setBodyScroll = () => {
    const modalIsOpen = [createModal, document.getElementById('editRuleModal')]
      .some((modal) => modal && !modal.classList.contains('hidden'));
    document.body.classList.toggle('overflow-hidden', modalIsOpen);
  };

  const openCreateModal = () => {
    if (!createModal) return;
    createModal.classList.remove('hidden');
    setBodyScroll();
  };

  const closeCreateModal = () => {
    if (!createModal) return;
    createModal.classList.add('hidden');
    setBodyScroll();
  };

  if (openCreateButton) {
    openCreateButton.addEventListener('click', openCreateModal);
  }
  closeCreateButtons.forEach((button) => {
    button.addEventListener('click', closeCreateModal);
  });

  const selectAll = document.getElementById('selectAllRules');
  const checkboxes = Array.from(document.querySelectorAll('.rule-checkbox'));
  const bulkActionBar = document.getElementById('bulkActionBar');
  const selectedCount = document.getElementById('selectedCount');
  const bulkInputs = document.getElementById('bulkRuleInputs');
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
        input.name = 'selected_rules';
        input.value = checkbox.dataset.ruleId;
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

  const editModal = document.getElementById('editRuleModal');
  const editForm = document.getElementById('editRuleForm');
  const closeEditButtons = document.querySelectorAll('[data-close-edit-modal]');

  const closeEditModal = () => {
    if (!editModal) return;
    editModal.classList.add('hidden');
    setBodyScroll();
  };

  document.querySelectorAll('.edit-rule-btn').forEach((button) => {
    button.addEventListener('click', () => {
      editForm.action = button.dataset.action;
      document.getElementById('editSuperGroup').value = button.dataset.superGroup;
      document.getElementById('editMin').value = button.dataset.min.replace(',', '.');
      document.getElementById('editMax').value = button.dataset.max.replace(',', '.');
      document.getElementById('editFrequency').value = button.dataset.frequency;
      document.getElementById('editLevel').value = button.dataset.level;
      editModal.classList.remove('hidden');
      setBodyScroll();
    });
  });
  closeEditButtons.forEach((button) => {
    button.addEventListener('click', closeEditModal);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    closeCreateModal();
    closeEditModal();
  });

  setBodyScroll();
  updateBulkSelection();
});
