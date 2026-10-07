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

    // Paso 2: activar las opciones de comida/cena (platos/postre) solo si se
    // marca la comida; estan en la misma linea, sin desplegable.
    form.querySelectorAll('[data-meal-group]').forEach(function (group) {
        const toggle = group.querySelector('[data-meal-group-toggle]');
        const options = group.querySelector('[data-meal-group-options]');
        if (!toggle || !options) {
            return;
        }
        toggle.addEventListener('change', function () {
            options.disabled = !toggle.checked;
            options.classList.toggle('opacity-50', !toggle.checked);
        });
    });

    // Paso 2: mostrar el input de gramos máximos solo si se marca el check.
    const limitPortionCheckbox = document.getElementById('limit-portion-checkbox');
    const maxPortionWrapper = document.getElementById('max-portion-wrapper');
    if (limitPortionCheckbox && maxPortionWrapper) {
        limitPortionCheckbox.addEventListener('change', function () {
            maxPortionWrapper.classList.toggle('hidden', !limitPortionCheckbox.checked);
        });
    }

    // Paso 3: mostrar el selector de plantilla solo si se marca "Usar plantilla existente".
    const useTemplateCheckbox = document.getElementById('use-template-checkbox');
    const templateSelectWrapper = document.getElementById('template-select-wrapper');
    if (useTemplateCheckbox && templateSelectWrapper) {
        useTemplateCheckbox.addEventListener('change', function () {
            templateSelectWrapper.classList.toggle('hidden', !useTemplateCheckbox.checked);
        });
    }

    function fieldValue(name) {
        const field = form.querySelector('[name="' + name + '"]');
        return field ? field.value : '';
    }

    // Paso 3: porcentajes de macros <-> gramos <-> kcal. Los porcentajes no se
    // envian (sin name); el servidor solo recibe kcal y gramos.
    (function initMacroPercentages() {
        const kcalInput = document.getElementById('macro-kcal');
        const kcalHint = document.getElementById('macro-kcal-auto-hint');
        const pctHint = document.getElementById('macro-pct-hint');
        const totalValue = document.querySelector('[data-macro-total]');
        const totalWarning = document.querySelector('[data-macro-total-warning]');
        const totalBox = document.getElementById('macro-pct-total');
        const macros = Array.from(form.querySelectorAll('[data-macro-pct]')).map(function (pct) {
            return {
                pct: pct,
                grams: document.getElementById('macro-' + pct.dataset.macroPct + '-g'),
                factor: parseFloat(pct.dataset.factor),
            };
        });
        if (!kcalInput || macros.length === 0 || macros.some(function (m) { return !m.grams; })) {
            return;
        }

        function num(el) {
            if (el.value === '') {
                return null;
            }
            const n = parseFloat(el.value);
            return isNaN(n) || n < 0 ? null : n;
        }
        function templateOn() {
            return !!(useTemplateCheckbox && useTemplateCheckbox.checked);
        }
        function kcalBase() {
            const k = num(kcalInput);
            return k !== null && k > 0 ? k : null;
        }
        function isAuto() {
            return kcalInput.dataset.auto === '1';
        }
        function setAuto(on) {
            if (on) {
                kcalInput.dataset.auto = '1';
            } else {
                delete kcalInput.dataset.auto;
            }
        }
        function round1(n) {
            return String(Math.round(n * 10) / 10);
        }
        function pctFromGrams(m, base) {
            const g = num(m.grams);
            m.pct.value = g === null ? '' : round1(g * m.factor / base * 100);
        }
        function gramsFromPct(m, base) {
            const p = num(m.pct);
            m.grams.value = p === null ? '' : String(Math.round(base * p / 100 / m.factor));
        }
        function allPctFromGrams() {
            const base = kcalBase();
            macros.forEach(function (m) {
                if (base) { pctFromGrams(m, base); } else { m.pct.value = ''; }
            });
        }
        // Con las kcal vacias (o automaticas) y los tres gramos rellenos,
        // las kcal se derivan de los gramos; si faltan gramos, se vacian.
        function syncAuto() {
            const filled = macros.every(function (m) { return num(m.grams) !== null; });
            if (filled && !templateOn()) {
                const total = Math.round(macros.reduce(function (s, m) { return s + num(m.grams) * m.factor; }, 0));
                if (total > 0) {
                    kcalInput.value = String(total);
                    setAuto(true);
                    allPctFromGrams();
                    return;
                }
            }
            if (isAuto()) {
                kcalInput.value = '';
                setAuto(false);
            }
            allPctFromGrams();
        }
        function refresh() {
            const base = kcalBase();
            macros.forEach(function (m) { m.pct.disabled = !base; });
            if (pctHint) { pctHint.classList.toggle('hidden', !!base); }
            if (kcalHint) { kcalHint.classList.toggle('hidden', !(isAuto() && base)); }
            let total = 0;
            let any = false;
            macros.forEach(function (m) {
                const p = num(m.pct);
                if (p !== null) { any = true; total += p; }
            });
            const off = any && Math.abs(total - 100) > 0.5;
            if (totalValue) { totalValue.textContent = round1(total); }
            if (totalWarning) { totalWarning.classList.toggle('hidden', !off); }
            if (totalBox) {
                totalBox.classList.toggle('text-amber-600', off);
                totalBox.classList.toggle('text-gray-600', !off);
            }
        }

        // Mientras se escribe no se tocan los gramos (evita perder datos al
        // borrar cifras); el recalculo se confirma en 'change'.
        kcalInput.addEventListener('input', function () {
            setAuto(false);
            refresh();
        });
        kcalInput.addEventListener('change', function () {
            const base = kcalBase();
            if (kcalInput.value === '' || !base) {
                syncAuto();
            } else {
                macros.forEach(function (m) {
                    if (num(m.pct) !== null) { gramsFromPct(m, base); } else if (num(m.grams) !== null) { pctFromGrams(m, base); }
                });
            }
            refresh();
        });

        // En modo plantilla el servidor escala con target_kcal: no se deriva
        // automaticamente; si estaba en auto, se vacia al activar la plantilla.
        if (useTemplateCheckbox) {
            useTemplateCheckbox.addEventListener('change', function () {
                if (templateOn()) {
                    if (isAuto()) {
                        kcalInput.value = '';
                        setAuto(false);
                        allPctFromGrams();
                    }
                } else if (kcalInput.value === '') {
                    syncAuto();
                }
                refresh();
            });
        }

        macros.forEach(function (m) {
            m.grams.addEventListener('input', function () {
                if (num(m.grams) === null) { m.pct.value = ''; }
                if (kcalInput.value === '' || isAuto()) {
                    syncAuto();
                } else if (kcalBase() && num(m.grams) !== null) {
                    pctFromGrams(m, kcalBase());
                }
                refresh();
            });
            m.pct.addEventListener('input', function () {
                const base = kcalBase();
                if (!base) { return; }
                setAuto(false); // congelar las kcal actuales como manuales
                if (num(m.pct) === null) { m.grams.value = ''; } else { gramsFromPct(m, base); }
                refresh();
            });
        });

        if (kcalInput.value === '') {
            syncAuto();
        } else {
            allPctFromGrams();
        }
        refresh();
    })();

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

            summary.innerHTML = '';

            const useTemplate = useTemplateCheckbox && useTemplateCheckbox.checked;
            let lines;

            if (useTemplate) {
                const templateSelect = document.getElementById('template-select');
                const selectedOption = templateSelect ? templateSelect.options[templateSelect.selectedIndex] : null;
                const templateName = selectedOption ? selectedOption.textContent.trim() : '-';

                const templateKcal = fieldValue('target_kcal');

                lines = [
                    'Fecha de inicio: ' + startDate,
                    'Se creará a partir de la plantilla: ' + templateName,
                    'Objetivo kcal/día: ' + (templateKcal ? templateKcal + ' (cantidades escaladas proporcionalmente)' : 'el de la plantilla'),
                ];
            } else {
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

                lines = [
                    'Duración: ' + days + ' día(s), desde ' + startDate,
                    'Tomas incluidas: ' + (meals.length ? meals.join(', ') : 'ninguna seleccionada'),
                    'Objetivo kcal/día: ' + (kcal || 'calculado automáticamente'),
                    'Tamaño de ración: ' + (limitPortion ? (portionSize || '-') : 'natural de cada plato'),
                ];
            }

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
