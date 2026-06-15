let appointmentsTable = document.getElementById('appointmentsTable')
let toggleAllCheckbox = appointmentsTable.querySelector("thead input[type='checkbox']")
let checkboxes = appointmentsTable.querySelectorAll("tbody input[type='checkbox']")
toggleAllCheckbox.addEventListener('change', (event) => {
    checkboxes.forEach((checkbox) => {
        checkbox.checked = event.target.checked
    })
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
        alert(
        info.event.title + "\n" +
        info.event.start.toLocaleString() +
        "\n\n" +
        (info.event.extendedProps.description || "")
        );
    }
    });

    calendar.render();
    });