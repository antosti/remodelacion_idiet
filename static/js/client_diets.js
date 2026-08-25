document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('delete-menu-modal');
    if (!modal) {
        return;
    }

    const cancelBtn = document.getElementById('delete-menu-cancel');
    const confirmBtn = document.getElementById('delete-menu-confirm');

    let pendingForm = null;

    function openModal(form) {
        pendingForm = form;
        modal.classList.remove('hidden');
    }

    function closeModal() {
        modal.classList.add('hidden');
        pendingForm = null;
    }

    document.querySelectorAll('.delete-menu-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            const form = document.getElementById(btn.dataset.formId);
            if (form) {
                openModal(form);
            }
        });
    });

    cancelBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', function (evt) {
        if (evt.target === modal) {
            closeModal();
        }
    });

    confirmBtn.addEventListener('click', function () {
        if (pendingForm) {
            pendingForm.submit();
        }
    });
});
