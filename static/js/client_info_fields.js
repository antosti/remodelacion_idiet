document.addEventListener('DOMContentLoaded', () => {
  const unlockBtn = document.getElementById('unlockInfoFieldsBtn');
  if (!unlockBtn) return;

  const fields = document.querySelectorAll('.client-info-field');

  unlockBtn.addEventListener('click', () => {
    fields.forEach((field) => {
      field.readOnly = false;
      field.classList.remove('bg-gray-100', 'text-gray-500', 'cursor-not-allowed');
      field.classList.add('focus:ring-2', 'focus:ring-secondary/30');
    });

    unlockBtn.textContent = 'Editando';
    unlockBtn.disabled = true;
    unlockBtn.classList.add('opacity-60', 'cursor-not-allowed');

    if (fields.length) {
      fields[0].focus();
    }
  });
});
