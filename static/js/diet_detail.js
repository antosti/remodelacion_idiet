document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('edit-intake-modal');
    if (!modal) {
        return;
    }

    const closeBtn = document.getElementById('edit-intake-close');
    const cancelBtn = document.getElementById('edit-intake-cancel');
    const saveBtn = document.getElementById('edit-intake-save');
    const aliasLabel = document.getElementById('edit-intake-alias');
    const dishSelect = document.getElementById('edit-intake-dish');
    const quantityInput = document.getElementById('edit-intake-quantity');
    const errorLabel = document.getElementById('edit-intake-error');

    let activeCell = null;
    let lockMode = false;

    const regenerateToggleBtn = document.getElementById('regenerate-toggle-btn');
    const regenerateBanner = document.getElementById('regenerate-banner');
    const regenerateCancelBtn = document.getElementById('regenerate-cancel-btn');
    const regenerateConfirmBtn = document.getElementById('regenerate-confirm-btn');
    const regenerateCount = document.getElementById('regenerate-count');

    function updateLockCount() {
        if (regenerateCount) {
            regenerateCount.textContent = document.querySelectorAll('.lock-checkbox:checked').length;
        }
    }

    function setLockMode(active) {
        lockMode = active;
        document.querySelectorAll('.lock-cell').forEach(function (cell) {
            if (!active) {
                const checkbox = cell.querySelector('.lock-checkbox');
                const badge = cell.querySelector('.lock-badge');
                if (checkbox) checkbox.checked = false;
                if (badge) badge.classList.add('hidden');
                cell.classList.remove('ring-2', 'ring-idiet', 'bg-idiet/10');
            }
        });
        if (regenerateBanner) regenerateBanner.classList.toggle('hidden', !active);
        if (regenerateToggleBtn) regenerateToggleBtn.textContent = active ? 'Salir del modo bloqueo' : 'Rehacer menú';
        updateLockCount();
    }

    if (regenerateToggleBtn) {
        regenerateToggleBtn.addEventListener('click', function () {
            setLockMode(!lockMode);
        });
    }
    if (regenerateCancelBtn) {
        regenerateCancelBtn.addEventListener('click', function () {
            setLockMode(false);
        });
    }
    const regenerateConfirmModal = document.getElementById('regenerate-confirm-modal');
    const regenerateModalCancel = document.getElementById('regenerate-modal-cancel');
    const regenerateModalConfirm = document.getElementById('regenerate-modal-confirm');
    const regenerateForm = document.getElementById('regenerate-form');

    if (regenerateConfirmBtn && regenerateConfirmModal) {
        regenerateConfirmBtn.addEventListener('click', function () {
            regenerateConfirmModal.classList.remove('hidden');
        });
    }
    if (regenerateModalCancel) {
        regenerateModalCancel.addEventListener('click', function () {
            regenerateConfirmModal.classList.add('hidden');
        });
    }
    if (regenerateConfirmModal) {
        regenerateConfirmModal.addEventListener('click', function (evt) {
            if (evt.target === regenerateConfirmModal) {
                regenerateConfirmModal.classList.add('hidden');
            }
        });
    }
    if (regenerateModalConfirm && regenerateForm) {
        regenerateModalConfirm.addEventListener('click', function () {
            regenerateForm.submit();
        });
    }

    function toggleCellLock(cell) {
        const checkbox = cell.querySelector('.lock-checkbox');
        const badge = cell.querySelector('.lock-badge');
        if (!checkbox) {
            return;
        }
        checkbox.checked = !checkbox.checked;
        cell.classList.toggle('ring-2', checkbox.checked);
        cell.classList.toggle('ring-idiet', checkbox.checked);
        cell.classList.toggle('bg-idiet/10', checkbox.checked);
        if (badge) badge.classList.toggle('hidden', !checkbox.checked);
        updateLockCount();
    }

    function csrfToken() {
        const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    function showError(message) {
        errorLabel.textContent = message;
        errorLabel.classList.remove('hidden');
    }

    function openModal(cell) {
        activeCell = cell;
        errorLabel.classList.add('hidden');
        aliasLabel.textContent = cell.dataset.intakeAlias || 'Editar toma';
        dishSelect.innerHTML = '<option>Cargando…</option>';
        quantityInput.value = '';
        modal.classList.remove('hidden');

        fetch(cell.dataset.editUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(function (resp) {
                if (!resp.ok) {
                    throw new Error('No se ha podido cargar la información de esta toma.');
                }
                return resp.json();
            })
            .then(function (data) {
                dishSelect.innerHTML = '';
                data.options.forEach(function (opt) {
                    const el = document.createElement('option');
                    el.value = opt.id;
                    el.textContent = opt.name;
                    if (opt.id === data.dish_id) {
                        el.selected = true;
                    }
                    dishSelect.appendChild(el);
                });
                quantityInput.value = data.quantity;
            })
            .catch(function (err) {
                showError(err.message);
            });
    }

    function closeModal() {
        modal.classList.add('hidden');
        activeCell = null;
    }

    document.querySelectorAll('[data-edit-url]').forEach(function (cell) {
        cell.addEventListener('click', function () {
            if (lockMode) {
                toggleCellLock(cell);
                return;
            }
            openModal(cell);
        });
    });

    closeBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', function (evt) {
        if (evt.target === modal) {
            closeModal();
        }
    });

    saveBtn.addEventListener('click', function () {
        if (!activeCell) {
            return;
        }
        errorLabel.classList.add('hidden');

        const quantity = parseInt(quantityInput.value, 10);
        if (!quantity || quantity <= 0) {
            showError('Indica una cantidad válida.');
            return;
        }

        const cell = activeCell;
        saveBtn.disabled = true;
        saveBtn.textContent = 'Guardando…';

        fetch(cell.dataset.editUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken(),
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify({ dish_id: dishSelect.value, quantity: quantity }),
        })
            .then(function (resp) {
                return resp.json().then(function (data) {
                    if (!resp.ok) {
                        throw new Error(data.error || 'No se ha podido guardar el cambio.');
                    }
                    return data;
                });
            })
            .then(function (data) {
                cell.querySelector('[data-field="dish-name"]').textContent = data.dish_name;
                cell.querySelector('[data-field="quantity-kcal"]').textContent =
                    data.quantity + ' g · ' + Math.round(data.kcal) + ' kcal';
                cell.querySelector('[data-field="macros"]').textContent =
                    'P ' + data.prot + 'g · G ' + data.fat + 'g · H ' + data.carb + 'g';

                const dayHeader = document.querySelector(
                    'th[data-day-index="' + cell.dataset.dayIndex + '"] [data-field="day-kcal"]'
                );
                if (dayHeader) {
                    dayHeader.textContent = Math.round(data.day_kcal) + ' kcal';
                }

                closeModal();
            })
            .catch(function (err) {
                showError(err.message);
            })
            .finally(function () {
                saveBtn.disabled = false;
                saveBtn.textContent = 'Guardar';
            });
    });
});
