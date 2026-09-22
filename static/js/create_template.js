document.addEventListener('DOMContentLoaded', function () {
    // Muestra/oculta las opciones de un grupo de comidas (platos/postre) al
    // marcar "Incluir <grupo>", igual que el paso 2 del wizard de dietas
    // (ver static/js/diet_wizard.js).
    document.querySelectorAll('[data-meal-group]').forEach(function (group) {
        const toggle = group.querySelector('[data-meal-group-toggle]');
        const options = group.querySelector('[data-meal-group-options]');
        if (!toggle || !options) {
            return;
        }
        toggle.addEventListener('change', function () {
            options.classList.toggle('hidden', !toggle.checked);
        });
    });
});
