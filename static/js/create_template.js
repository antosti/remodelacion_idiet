document.addEventListener('DOMContentLoaded', function () {
    // Activa las opciones de un grupo de comidas (platos/postre) solo al
    // marcar el grupo; estan en la misma linea, sin desplegable, igual que el
    // paso 2 del wizard de dietas (ver static/js/diet_wizard.js).
    document.querySelectorAll('[data-meal-group]').forEach(function (group) {
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
});
