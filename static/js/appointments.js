let appointmentsTable = document.getElementById('appointmentsTable')
let toggleAllCheckbox = appointmentsTable.querySelector("thead input[type='checkbox']")
let checkboxes = appointmentsTable.querySelectorAll("tbody input[type='checkbox']")

// Bulk action functionality
const bulkActionBar = document.getElementById('bulkActionBar')
const selectedCount = document.getElementById('selectedCount')
const hiddenCheckboxes = document.getElementById('hiddenCheckboxes')
const cancelBulkActionBtn = document.getElementById('cancelBulkActionBtn')
const deactivateBulkForm = document.getElementById('deactivateBulkForm')

function updateBulkActionBar() {
    const checkedBoxes = appointmentsTable.querySelectorAll("tbody input[type='checkbox']:checked")
    const count = checkedBoxes.length

    if (count > 0) {
        bulkActionBar.classList.remove('hidden')
        selectedCount.textContent = `${count} cita${count !== 1 ? 's' : ''} seleccionada${count !== 1 ? 's' : ''}`
        
        // Update hidden inputs
        hiddenCheckboxes.innerHTML = ''
        checkedBoxes.forEach((checkbox) => {
            const input = document.createElement('input')
            input.type = 'hidden'
            input.name = 'appointment_ids'
            input.value = checkbox.dataset.appointmentId
            hiddenCheckboxes.appendChild(input)
        })
    } else {
        bulkActionBar.classList.add('hidden')
        hiddenCheckboxes.innerHTML = ''
    }
}

// Add event listeners to all checkboxes
checkboxes.forEach((checkbox) => {
    checkbox.addEventListener('change', updateBulkActionBar)
})

toggleAllCheckbox.addEventListener('change', (event) => {
    checkboxes.forEach((checkbox) => {
        checkbox.checked = event.target.checked
    })
    updateBulkActionBar()
})

cancelBulkActionBtn.addEventListener('click', () => {
    checkboxes.forEach((checkbox) => {
        checkbox.checked = false
    })
    toggleAllCheckbox.checked = false
    updateBulkActionBar()
})

const newAppointmentModal = document.getElementById('newAppointmentModal')
const openNewAppointmentModalButton = document.getElementById('openNewAppointmentModal')
const modalCloseButtons = newAppointmentModal ? newAppointmentModal.querySelectorAll('.modal-close') : []

if (openNewAppointmentModalButton && newAppointmentModal) {
    openNewAppointmentModalButton.addEventListener('click', () => {
        newAppointmentModal.classList.remove('hidden')
        newAppointmentModal.classList.add('flex')
    })
}

const closeNewAppointmentModal = () => {
    newAppointmentModal.classList.add('hidden')
    newAppointmentModal.classList.remove('flex')
}

modalCloseButtons.forEach((button) => {
    button.addEventListener('click', () => {
        closeNewAppointmentModal()
    })
})

if (newAppointmentModal) {
    newAppointmentModal.addEventListener('click', (event) => {
        if (event.target === newAppointmentModal) {
            closeNewAppointmentModal()
        }
    })
}

const clientSearchInput = document.getElementById('clientSearch')
const clientIdInput = document.getElementById('clientId')
const clientOptionsBox = document.getElementById('clientOptions')
const clientOptionButtons = clientOptionsBox ? Array.from(clientOptionsBox.querySelectorAll('button[data-id]')) : []
const appointmentForm = document.querySelector('#newAppointmentModal form')

// Edit modal elements
const editAppointmentModal = document.getElementById('editAppointmentModal')
const editAppointmentForm = document.getElementById('editAppointmentForm')
const editAppointmentIdInput = document.getElementById('editAppointmentId')
const editClientSearchInput = document.getElementById('editClientSearch')
const editClientIdInput = document.getElementById('editClientId')
const editClientOptionsBox = document.getElementById('editClientOptions')
const editClientOptionButtons = editClientOptionsBox ? Array.from(editClientOptionsBox.querySelectorAll('button[data-id]')) : []

const closeEditModal = () => {
    if (!editAppointmentModal) return
    editAppointmentModal.classList.add('hidden')
    editAppointmentModal.classList.remove('flex')
}

if (editAppointmentModal) {
    editAppointmentModal.addEventListener('click', (event) => {
        if (event.target === editAppointmentModal) closeEditModal()
    })
    // wire close buttons inside edit modal
    const editCloseButtons = editAppointmentModal.querySelectorAll('.modal-close')
    editCloseButtons.forEach((btn) => btn.addEventListener('click', closeEditModal))
}

const closeClientOptions = () => {
    if (clientOptionsBox) clientOptionsBox.classList.add('hidden')
}

if (clientSearchInput && clientOptionsBox) {
    clientSearchInput.addEventListener('input', () => {
        const searchTerm = clientSearchInput.value.toLowerCase().trim()
        clientOptionButtons.forEach((button) => {
            const optionText = button.textContent.toLowerCase()
            button.classList.toggle('hidden', !optionText.includes(searchTerm))
        })
        clientOptionsBox.classList.remove('hidden')
        if (clientIdInput) clientIdInput.value = ''
    })

    clientOptionButtons.forEach((button) => {
        button.addEventListener('click', () => {
            clientSearchInput.value = button.textContent.trim()
            if (clientIdInput) clientIdInput.value = button.dataset.id || ''
            closeClientOptions()
        })
    })

// edit modal client options
if (editClientSearchInput && editClientOptionsBox) {
    editClientSearchInput.addEventListener('input', () => {
        const searchTerm = editClientSearchInput.value.toLowerCase().trim()
        editClientOptionButtons.forEach((button) => {
            const optionText = button.textContent.toLowerCase()
            button.classList.toggle('hidden', !optionText.includes(searchTerm))
        })
        editClientOptionsBox.classList.remove('hidden')
        if (editClientIdInput) editClientIdInput.value = ''
    })
    editClientOptionButtons.forEach((button) => {
        button.addEventListener('click', () => {
            editClientSearchInput.value = button.textContent.trim()
            if (editClientIdInput) editClientIdInput.value = button.dataset.id || ''
            editClientOptionsBox.classList.add('hidden')
        })
    })
    editClientSearchInput.addEventListener('focus', () => {
        editClientOptionsBox.classList.remove('hidden')
    })
}

    clientSearchInput.addEventListener('focus', () => {
        clientOptionsBox.classList.remove('hidden')
    })

    document.addEventListener('click', (event) => {
        if (!clientOptionsBox.contains(event.target) && event.target !== clientSearchInput) {
            closeClientOptions()
        }
    })
}

if (appointmentForm && clientIdInput) {
    appointmentForm.addEventListener('submit', (event) => {
        if (!clientIdInput.value) {
            event.preventDefault()
            alert('Selecciona un cliente válido de la lista.')
            clientSearchInput?.focus()
        }
    })
}

// validate edit form submit
if (editAppointmentForm && editClientIdInput) {
    editAppointmentForm.addEventListener('submit', (event) => {
        if (!editClientIdInput.value) {
            event.preventDefault()
            alert('Selecciona un cliente válido de la lista.')
            editClientSearchInput?.focus()
        }
    })
}

// table rows click -> open edit modal
try {
    const rows = document.querySelectorAll('#appointmentsTable tbody tr[data-appointment-id]')
    rows.forEach((row) => {
        row.addEventListener('click', (e) => {
            if (e.target && (e.target.tagName === 'INPUT' || e.target.closest('input'))) return
            const id = row.dataset.appointmentId
            const cells = row.querySelectorAll('td')
            if (!cells || cells.length < 5) return
            const firstName = cells[1].textContent.trim()
            const lastName = cells[2].textContent.trim()
            const email = cells[3].textContent.trim()
            const rowMotive = row.dataset.motive || ''
            const rowStartDate = row.dataset.startDate || ''
            const rowEndDate = row.dataset.endDate || ''

            let startDate = ''
            if (rowStartDate) {
                const parsed = new Date(rowStartDate)
                if (!isNaN(parsed)) {
                    const dt = parsed
                    const pad = (n) => n.toString().padStart(2, '0')
                    startDate = dt.getFullYear() + '-' + pad(dt.getMonth() + 1) + '-' + pad(dt.getDate()) + 'T' + pad(dt.getHours()) + ':' + pad(dt.getMinutes())
                }
            }

            let duration = ''
            if (rowStartDate && rowEndDate) {
                const start = new Date(rowStartDate)
                const end = new Date(rowEndDate)
                if (!isNaN(start) && !isNaN(end) && end > start) {
                    duration = Math.round((end - start) / (1000 * 60))
                }
            }

            if (editAppointmentForm) {
                if (editAppointmentIdInput) editAppointmentIdInput.value = id
                if (editClientSearchInput) editClientSearchInput.value = `${firstName} ${lastName}`
                if (editClientIdInput) editClientIdInput.value = row.dataset.clientId || ''
                const motiveInput = editAppointmentForm.querySelector('[name="motive"]')
                if (motiveInput) motiveInput.value = rowMotive
                const startInput = editAppointmentForm.querySelector('[name="start_date"]')
                if (startInput) startInput.value = startDate
                const durationInput = editAppointmentForm.querySelector('[name="duration_minutes"]')
                if (durationInput) durationInput.value = duration
                if (editAppointmentForm && id) editAppointmentForm.action = `/appointments/${id}/update/`
                editAppointmentModal.classList.remove('hidden')
                editAppointmentModal.classList.add('flex')
            }
        })
    })
} catch (err) {
    // ignore
}

document.addEventListener("DOMContentLoaded", function () {
const appointmentEvents = window.appointmentEvents || [];
const calendarEl = document.getElementById("calendar");

const calendar = new FullCalendar.Calendar(calendarEl, {
initialView: "dayGridMonth",
locale: "es",
firstDay: 1,
height: "auto",

headerToolbar: {
    left: "prev,next today",
    center: "title",
    right: "dayGridMonth,timeGridWeek,timeGridDay"
},

buttonText: {
    today: "Hoy",
    month: "Mes",
    week: "Semana",
    day: "Día"
},

events: appointmentEvents,
eventBackgroundColor: '#d1fae5',
eventBorderColor: '#d1fae5',
eventTextColor: '#064e3b',
eventDisplay: 'block',
eventContent: function(arg) {
    const eventStart = arg.event.start ? arg.event.start.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
    return {
        html: `<div class="inline-flex w-full items-center overflow-hidden rounded-full bg-emerald-200 px-2 py-1 text-[10px] font-semibold text-slate-900">
                    <span style="display:inline-block; width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${eventStart} ${arg.event.title}">${eventStart} ${arg.event.title}</span>
                </div>`
    };
},

eventClick: function(info) {
    // abrir edit modal y rellenar datos
    if (editAppointmentModal && editAppointmentForm) {
        const appointmentId = info.event.extendedProps?.appointment_id || info.event.id || ''
        if (editAppointmentIdInput) editAppointmentIdInput.value = appointmentId

        if (editClientSearchInput) editClientSearchInput.value = info.event.title || ''
        const clientId = info.event.extendedProps?.client_id || info.event._def?.extendedProps?.client_id || ''
        if (editClientIdInput) editClientIdInput.value = clientId
        const motiveInput = editAppointmentForm.querySelector('[name="motive"]')
        if (motiveInput) motiveInput.value = info.event.extendedProps?.description || ''
        const startInput = editAppointmentForm.querySelector('[name="start_date"]')
        if (startInput && info.event.start) {
            const dt = new Date(info.event.start)
            const pad = (n) => n.toString().padStart(2, '0')
            const local = dt.getFullYear() + '-' + pad(dt.getMonth() + 1) + '-' + pad(dt.getDate()) + 'T' + pad(dt.getHours()) + ':' + pad(dt.getMinutes())
            startInput.value = local
        }

        const durationInput = editAppointmentForm.querySelector('[name="duration_minutes"]')
        if (durationInput && info.event.start && info.event.end) {
            const duration = Math.round((info.event.end - info.event.start) / (1000 * 60))
            durationInput.value = duration > 0 ? duration : ''
        }

        // set action to update URL
        if (editAppointmentForm && appointmentId) {
            editAppointmentForm.action = `/appointments/${appointmentId}/update/`
        }

        editAppointmentModal.classList.remove('hidden')
        editAppointmentModal.classList.add('flex')
    }
}
});

calendar.render();
});