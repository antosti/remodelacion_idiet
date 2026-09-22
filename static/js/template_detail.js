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

    function applyFreeMealState(isFree) {
        dishSelect.disabled = isFree;
        quantityInput.disabled = isFree;
    }

    if (freeMealCheckbox) {
        freeMealCheckbox.addEventListener('change', function () {
            applyFreeMealState(freeMealCheckbox.checked);
        });
    }

    let activeCell = null;
    let pasteMode = false;
    let clipboard = null;

    const pasteBanner = document.getElementById('paste-banner');
    const pasteCancelBtn = document.getElementById('paste-cancel-btn');
    const pasteDishName = document.getElementById('paste-dish-name');
    const pasteTargetCount = document.getElementById('paste-target-count');
    const pasteError = document.getElementById('paste-error');

    function clearPasteHighlights() {
        document.querySelectorAll('[data-item-id]').forEach(function (cell) {
            cell.classList.remove('ring-2', 'ring-emerald-500', 'bg-emerald-50', 'opacity-40');
        });
    }

    function setPasteMode(active) {
        pasteMode = active;

        if (active && clipboard) {
            if (pasteDishName) pasteDishName.textContent = clipboard.dishName;
            if (pasteTargetCount) pasteTargetCount.textContent = clipboard.targetIds.size;
            document.querySelectorAll('[data-item-id]').forEach(function (cell) {
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
