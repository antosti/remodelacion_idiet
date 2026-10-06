document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('edit-intake-modal');
    if (!modal) {
        return;
    }

    const closeBtn = document.getElementById('edit-intake-close');
    const cancelBtn = document.getElementById('edit-intake-cancel');
    const saveBtn = document.getElementById('edit-intake-save');
    const copyBtn = document.getElementById('edit-intake-copy');
    const aliasLabel = document.getElementById('edit-intake-alias');
    const dishSelect = document.getElementById('edit-intake-dish');
    const quantityInput = document.getElementById('edit-intake-quantity');
    const freeMealCheckbox = document.getElementById('edit-intake-free-meal');
    const errorLabel = document.getElementById('edit-intake-error');

    const recipeLink = document.getElementById('edit-intake-recipe-link');

    function updateRecipeLink() {
        if (!recipeLink) return;
        const id = parseInt(dishSelect.value, 10);
        const isFree = freeMealCheckbox && freeMealCheckbox.checked;
        const selectedOption = dishSelect.options[dishSelect.selectedIndex];
        const isInactive = !!selectedOption && selectedOption.dataset.active === '0';
        if (isFree || isInactive || !(id > 0) || String(id) !== dishSelect.value) {
            recipeLink.classList.add('hidden');
            recipeLink.setAttribute('href', '#');
            return;
        }
        recipeLink.setAttribute(
            'href',
            recipeLink.dataset.urlTemplate.replace(/\/0\/edit\/$/, '/' + id + '/edit/')
        );
        recipeLink.classList.remove('hidden');
    }

    function applyFreeMealState(isFree) {
        dishSelect.disabled = isFree;
        quantityInput.disabled = isFree;
        updateRecipeLink();
    }

    dishSelect.addEventListener('change', updateRecipeLink);

    if (freeMealCheckbox) {
        freeMealCheckbox.addEventListener('change', function () {
            applyFreeMealState(freeMealCheckbox.checked);
        });
    }

    let activeCell = null;
    let lockMode = false;
    let pasteMode = false;
    let clipboard = null;

    const regenerateToggleBtn = document.getElementById('regenerate-toggle-btn');
    const regenerateBanner = document.getElementById('regenerate-banner');
    const regenerateCancelBtn = document.getElementById('regenerate-cancel-btn');
    const regenerateConfirmBtn = document.getElementById('regenerate-confirm-btn');
    const regenerateCount = document.getElementById('regenerate-count');

    const pasteBanner = document.getElementById('paste-banner');
    const pasteCancelBtn = document.getElementById('paste-cancel-btn');
    const pasteDishName = document.getElementById('paste-dish-name');
    const pasteTargetCount = document.getElementById('paste-target-count');
    const pasteError = document.getElementById('paste-error');

    function updateLockCount() {
        if (regenerateCount) {
            regenerateCount.textContent = document.querySelectorAll('.lock-checkbox:checked').length;
        }
    }

    function setLockMode(active) {
        if (active && pasteMode) {
            setPasteMode(false);
        }
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
        document.querySelectorAll('.row-lock-toggle').forEach(function (rowHeader) {
            rowHeader.classList.toggle('cursor-pointer', active);
            rowHeader.classList.toggle('hover:bg-idiet/5', active);
            rowHeader.title = active ? 'Bloquear/desbloquear toda la fila' : '';
        });
        if (regenerateBanner) regenerateBanner.classList.toggle('hidden', !active);
        if (regenerateToggleBtn) regenerateToggleBtn.textContent = active ? 'Salir del modo bloqueo' : 'Ajustar menú';
        updateLockCount();
    }

    function clearPasteHighlights() {
        document.querySelectorAll('.lock-cell[data-item-id]').forEach(function (cell) {
            cell.classList.remove('ring-2', 'ring-emerald-500', 'bg-emerald-50', 'opacity-40');
        });
    }

    function setPasteMode(active) {
        if (active && lockMode) {
            setLockMode(false);
        }
        pasteMode = active;

        if (active && clipboard) {
            if (pasteDishName) pasteDishName.textContent = clipboard.dishName;
            if (pasteTargetCount) pasteTargetCount.textContent = clipboard.targetIds.size;
            document.querySelectorAll('.lock-cell[data-item-id]').forEach(function (cell) {
                const isTarget = clipboard.targetIds.has(cell.dataset.itemId);
                cell.classList.toggle('ring-2', isTarget);
                cell.classList.toggle('ring-emerald-500', isTarget);
                cell.classList.toggle('bg-emerald-50', isTarget);
                cell.classList.toggle('opacity-40', !isTarget);
            });
            if (pasteError) pasteError.classList.add('hidden');
            if (pasteBanner) pasteBanner.classList.remove('hidden');
        }

        if (!active) {
            clipboard = null;
            clearPasteHighlights();
            if (pasteError) pasteError.classList.add('hidden');
            if (pasteBanner) pasteBanner.classList.add('hidden');
        }
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

    function setCellLock(cell, locked) {
        const checkbox = cell.querySelector('.lock-checkbox');
        const badge = cell.querySelector('.lock-badge');
        if (!checkbox || checkbox.checked === locked) {
            return;
        }
        checkbox.checked = locked;
        cell.classList.toggle('ring-2', locked);
        cell.classList.toggle('ring-idiet', locked);
        cell.classList.toggle('bg-idiet/10', locked);
        if (badge) badge.classList.toggle('hidden', !locked);
    }

    function toggleCellLock(cell) {
        const checkbox = cell.querySelector('.lock-checkbox');
        if (!checkbox) {
            return;
        }
        setCellLock(cell, !checkbox.checked);
        updateLockCount();
    }

    function toggleRowLock(rowHeader) {
        const row = rowHeader.closest('tr');
        const cells = row ? Array.from(row.querySelectorAll('.lock-cell[data-edit-url]')) : [];
        if (!cells.length) {
            return;
        }
        const allLocked = cells.every(function (cell) {
            const checkbox = cell.querySelector('.lock-checkbox');
            return checkbox && checkbox.checked;
        });
        cells.forEach(function (cell) {
            setCellLock(cell, !allLocked);
        });
        updateLockCount();
    }

    document.querySelectorAll('.row-lock-toggle').forEach(function (rowHeader) {
        rowHeader.addEventListener('click', function () {
            if (lockMode) {
                toggleRowLock(rowHeader);
            }
        });
    });

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
        if (freeMealCheckbox) freeMealCheckbox.checked = false;
        applyFreeMealState(false);
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
                    el.dataset.active = opt.active === false ? '0' : '1';
                    if (opt.id === data.dish_id) {
                        el.selected = true;
                    }
                    dishSelect.appendChild(el);
                });
                quantityInput.value = data.quantity;
                if (freeMealCheckbox) freeMealCheckbox.checked = !!data.is_free_meal;
                applyFreeMealState(!!data.is_free_meal);
            })
            .catch(function (err) {
                showError(err.message);
            });
    }

    function closeModal() {
        modal.classList.add('hidden');
        activeCell = null;
    }

    function patchCellFromResponse(cell, data) {
        cell.querySelector('[data-field="dish-name"]').textContent = data.dish_name;
        if (data.is_free_meal) {
            cell.querySelector('[data-field="quantity-kcal"]').textContent = '';
            cell.querySelector('[data-field="macros"]').textContent = '';
        } else {
            cell.querySelector('[data-field="quantity-kcal"]').textContent =
                data.quantity + ' g · ' + Math.round(data.kcal) + ' kcal';
            cell.querySelector('[data-field="macros"]').textContent =
                'P ' + data.prot + 'g · G ' + data.fat + 'g · H ' + data.carb + 'g';
        }

        const dayHeader = document.querySelector(
            'th[data-day-index="' + cell.dataset.dayIndex + '"] [data-field="day-kcal"]'
        );
        if (dayHeader) {
            dayHeader.textContent = Math.round(data.day_kcal) + ' kcal';
        }
    }

    function pasteIntoCell(cell) {
        if (pasteError) pasteError.classList.add('hidden');

        const payload = clipboard.isFreeMeal
            ? { is_free_meal: true }
            : { is_free_meal: false, dish_id: clipboard.dishId, quantity: clipboard.quantity };

        fetch(cell.dataset.editUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken(),
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify(payload),
        })
            .then(function (resp) {
                return resp.json().then(function (data) {
                    if (!resp.ok) {
                        throw new Error(data.error || 'No se ha podido pegar en esta celda.');
                    }
                    return data;
                });
            })
            .then(function (data) {
                patchCellFromResponse(cell, data);
            })
            .catch(function (err) {
                if (pasteError) {
                    pasteError.textContent = err.message;
                    pasteError.classList.remove('hidden');
                }
            });
    }

    function handleCellClickInPasteMode(cell) {
        const itemId = cell.dataset.itemId;
        if (!clipboard || !itemId || !clipboard.targetIds.has(itemId)) {
            setPasteMode(false);
            return;
        }
        pasteIntoCell(cell);
    }

    document.querySelectorAll('[data-edit-url]').forEach(function (cell) {
        cell.addEventListener('click', function (evt) {
            if (lockMode) {
                toggleCellLock(cell);
                return;
            }
            if (pasteMode) {
                evt.stopPropagation();
                handleCellClickInPasteMode(cell);
                return;
            }
            openModal(cell);
        });
    });

    document.addEventListener('click', function (evt) {
        if (!pasteMode) {
            return;
        }
        if (evt.target.closest('[data-edit-url]')) {
            return;
        }
        if (evt.target.closest('#paste-banner')) {
            return;
        }
        setPasteMode(false);
    });

    if (pasteCancelBtn) {
        pasteCancelBtn.addEventListener('click', function () {
            setPasteMode(false);
        });
    }

    if (copyBtn) {
        copyBtn.addEventListener('click', function () {
            if (!activeCell) {
                return;
            }
            errorLabel.classList.add('hidden');
            const cell = activeCell;

            fetch(cell.dataset.copyUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(function (resp) {
                    if (!resp.ok) {
                        throw new Error('No se ha podido copiar esta toma.');
                    }
                    return resp.json();
                })
                .then(function (data) {
                    if (!data.target_ids || !data.target_ids.length) {
                        showError('No hay celdas compatibles para pegar esta toma.');
                        return;
                    }
                    clipboard = {
                        dishId: data.dish_id,
                        dishName: data.dish_name,
                        quantity: data.quantity,
                        isFreeMeal: !!data.is_free_meal,
                        targetIds: new Set(data.target_ids.map(String)),
                    };
                    closeModal();
                    setPasteMode(true);
                })
                .catch(function (err) {
                    showError(err.message);
                });
        });
    }

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

        const isFreeMeal = !!(freeMealCheckbox && freeMealCheckbox.checked);
        let payload;
        if (isFreeMeal) {
            payload = { is_free_meal: true };
        } else {
            const quantity = parseInt(quantityInput.value, 10);
            if (!quantity || quantity <= 0) {
                showError('Indica una cantidad válida.');
                return;
            }
            payload = { is_free_meal: false, dish_id: dishSelect.value, quantity: quantity };
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
            body: JSON.stringify(payload),
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
                patchCellFromResponse(cell, data);
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

// Modal "Guardar como plantilla": solo abre/cierra; el envio es un POST normal.
document.addEventListener('DOMContentLoaded', function () {
    const openBtn = document.getElementById('save-template-btn');
    const modal = document.getElementById('save-template-modal');
    if (!openBtn || !modal) {
        return;
    }
    const cancelBtn = document.getElementById('save-template-cancel');
    const nameInput = document.getElementById('save-template-name');

    openBtn.addEventListener('click', function () {
        modal.classList.remove('hidden');
        if (nameInput) {
            nameInput.select();
        }
    });
    cancelBtn.addEventListener('click', function () {
        modal.classList.add('hidden');
    });
    modal.addEventListener('click', function (event) {
        if (event.target === modal) {
            modal.classList.add('hidden');
        }
    });
});
