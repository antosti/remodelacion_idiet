document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('diet-wizard-form');
    if (!form) {
        return;
    }

    const steps = Array.from(form.querySelectorAll('[data-step]'));
    const indicator = document.getElementById('diet-wizard-step-indicator');
    const prevBtn = document.getElementById('diet-wizard-prev');
    const nextBtn = document.getElementById('diet-wizard-next');
    const submitBtn = document.getElementById('diet-wizard-submit');
    let currentStep = 1;

    function showStep(stepNumber) {
        steps.forEach(function (stepEl) {
            const isCurrent = parseInt(stepEl.dataset.step, 10) === stepNumber;
            stepEl.classList.toggle('hidden', !isCurrent);
        });

        indicator.textContent = 'Paso ' + stepNumber + ' de ' + steps.length;
        prevBtn.classList.toggle('hidden', stepNumber === 1);
        const isLastStep = stepNumber === steps.length;
        nextBtn.classList.toggle('hidden', isLastStep);
        submitBtn.classList.toggle('hidden', !isLastStep);

        if (isLastStep) {
            renderSummary();
        }
    }

    nextBtn.addEventListener('click', function () {
        if (currentStep < steps.length) {
            currentStep += 1;
            showStep(currentStep);
        }
    });

    prevBtn.addEventListener('click', function () {
        if (currentStep > 1) {
            currentStep -= 1;
            showStep(currentStep);
        }
    });

    // Paso 2: mostrar/ocultar las opciones de comida/cena al marcar "Incluir".
    form.querySelectorAll('[data-meal-group]').forEach(function (group) {
        const toggle = group.querySelector('[data-meal-group-toggle]');
        const options = group.querySelector('[data-meal-group-options]');
        if (!toggle || !options) {
            return;
        }
        toggle.addEventListener('change', function () {
            options.classList.toggle('hidden', !toggle.checked);
        });
    });

    // Paso 3: mostrar el input de gramos máximos solo si se marca el check.
    const limitPortionCheckbox = document.getElementById('limit-portion-checkbox');
    const maxPortionWrapper = document.getElementById('max-portion-wrapper');
    if (limitPortionCheckbox && maxPortionWrapper) {
        limitPortionCheckbox.addEventListener('change', function () {
            maxPortionWrapper.classList.toggle('hidden', !limitPortionCheckbox.checked);
        });
    }

    function fieldValue(name) {
        const field = form.querySelector('[name="' + name + '"]');
        return field ? field.value : '';
    }

    function renderSummary() {
        const summary = document.getElementById('diet-wizard-summary');
        if (!summary) {
            return;
        }

        // Cualquier fallo aqui (campo inesperado, DOM desincronizado con una
        // version anterior cacheada del JS...) no debe dejar el resumen en
        // blanco sin explicacion: se captura y se avisa en vez de silenciarlo.
        try {
            const days = fieldValue('days') || '-';
            const startDate = fieldValue('start_date') || '-';

            const meals = [];
            form.querySelectorAll('[name="standalone_intakes"]:checked').forEach(function (input) {
                const label = input.closest('label');
                if (label) {
                    meals.push(label.textContent.trim());
                }
            });
            form.querySelectorAll('[data-meal-group-toggle]:checked').forEach(function (toggle) {
                const group = toggle.closest('[data-meal-group]');
                const groupKey = group ? group.dataset.mealGroup : '';
                if (groupKey) {
                    meals.push(groupKey.charAt(0).toUpperCase() + groupKey.slice(1));
                }
            });

            const kcal = fieldValue('target_kcal');
            const limitPortion = limitPortionCheckbox && limitPortionCheckbox.checked;
            const portionSize = limitPortion ? fieldValue('portion_size') : null;

            summary.innerHTML = '';
            const lines = [
                'Duración: ' + days + ' día(s), desde ' + startDate,
                'Tomas incluidas: ' + (meals.length ? meals.join(', ') : 'ninguna seleccionada'),
                'Objetivo kcal/día: ' + (kcal || 'calculado automáticamente'),
                'Tamaño de ración: ' + (limitPortion ? (portionSize || '-') : 'natural de cada plato'),
            ];
            lines.forEach(function (line) {
                const p = document.createElement('p');
                p.textContent = line;
                summary.appendChild(p);
            });
        } catch (err) {
            summary.textContent = 'No se ha podido generar el resumen. Revisa los datos de los pasos anteriores.';
        }
    }

    // Paso 4: mostrar un aviso mientras el servidor genera la dieta (puede
    // tardar varios segundos), para que no parezca que la pagina no responde.
    const loadingOverlay = document.getElementById('diet-wizard-loading-overlay');
    form.addEventListener('submit', function () {
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Generando…';
        }
        if (loadingOverlay) {
            loadingOverlay.classList.remove('hidden');
        }
    });

    showStep(currentStep);
});
