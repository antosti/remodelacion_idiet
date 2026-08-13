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

    function renderSummary() {
        const summary = document.getElementById('diet-wizard-summary');
        if (!summary) {
            return;
        }

        const days = form.querySelector('[name="days"]').value || '-';
        const startDate = form.querySelector('[name="start_date"]').value || '-';

        const meals = [];
        form.querySelectorAll('[name="standalone_intakes"]:checked').forEach(function (input) {
            meals.push(input.closest('label').textContent.trim());
        });
        form.querySelectorAll('[data-meal-group-toggle]:checked').forEach(function (toggle) {
            const groupKey = toggle.closest('[data-meal-group]').dataset.mealGroup;
            meals.push(groupKey.charAt(0).toUpperCase() + groupKey.slice(1));
        });

        const kcal = form.querySelector('[name="target_kcal"]').value;
        const limitPortion = limitPortionCheckbox && limitPortionCheckbox.checked;
        const maxGrams = limitPortion ? form.querySelector('[name="max_portion_grams"]').value : null;

        summary.innerHTML = '';
        const lines = [
            'Duración: ' + days + ' día(s), desde ' + startDate,
            'Tomas incluidas: ' + (meals.length ? meals.join(', ') : 'ninguna seleccionada'),
            'Objetivo kcal/día: ' + (kcal || 'calculado automáticamente'),
            'Límite de ración: ' + (limitPortion ? (maxGrams || '-') + ' g' : 'sin límite'),
        ];
        lines.forEach(function (line) {
            const p = document.createElement('p');
            p.textContent = line;
            summary.appendChild(p);
        });
    }

    showStep(currentStep);
});
