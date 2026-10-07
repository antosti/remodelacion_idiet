document.addEventListener('DOMContentLoaded', function () {
    // Habilita el borrado solo cuando el email escrito coincide con el del
    // usuario (el servidor lo vuelve a comprobar).
    const input = document.getElementById('confirm-email');
    const button = document.getElementById('purge-confirm-btn');
    if (!input || !button) {
        return;
    }
    input.addEventListener('input', function () {
        button.disabled = input.value.trim().toLowerCase() !== input.dataset.expected;
    });
});
