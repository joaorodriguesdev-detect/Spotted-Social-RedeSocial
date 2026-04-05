(function initEventosPage() {
    const MSG = {
        titleRequired: 'Informe um titulo para o evento.',
        descriptionRequired: 'Descreva o que vai acontecer no evento.',
        dateRequired: 'Selecione uma data.',
        timeRequired: 'Selecione um horario.',
        locationRequired: 'Informe o local do evento.',
        invalidDate: 'Data invalida.',
        invalidTime: 'Horario invalido.',
        pastDateTime: 'Nao e permitido usar data/horario no passado.'
    };

    const descInput = document.getElementById('event-desc-input');
    const counter = document.getElementById('char-counter');
    const eventForm = document.getElementById('create-event-form');
    const editEventForm = document.getElementById('edit-event-form');
    const createEventModal = document.getElementById('modal-evento');
    const editEventModal = document.getElementById('modal-editar-evento');
    const titleInput = document.getElementById('event-title-input');
    const dateInput = document.getElementById('event-date-input');
    const timeInput = document.getElementById('event-time-input');
    const locationInput = document.getElementById('event-location-input');
    const editTitleInput = document.getElementById('edit-event-title');
    const editDescriptionInput = document.getElementById('edit-event-description');
    const editDateInput = document.getElementById('edit-event-date');
    const editTimeInput = document.getElementById('edit-event-time');
    const editLocationInput = document.getElementById('edit-event-location');

    function setFieldError(inputEl, errorId, message) {
        const errorEl = document.getElementById(errorId);
        if (!inputEl || !errorEl) return;
        if (message) {
            errorEl.textContent = message;
            errorEl.classList.add('visible');
            inputEl.classList.add('border-red-400');
        } else {
            errorEl.textContent = '';
            errorEl.classList.remove('visible');
            inputEl.classList.remove('border-red-400');
        }
    }

    function getTodayISO() {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    function parseEventDateTime(dateValue, timeValue) {
        if (!dateValue || !timeValue) return null;
        const combined = new Date(`${dateValue}T${timeValue}`);
        if (Number.isNaN(combined.getTime())) return null;
        return combined;
    }

    function validateEventDateTime(dateInputEl, timeInputEl, dateErrorId, timeErrorId) {
        const dateValue = dateInputEl ? dateInputEl.value : '';
        const timeValue = timeInputEl ? timeInputEl.value : '';

        if (!dateValue || !timeValue) {
            return false;
        }

        const eventDateTime = parseEventDateTime(dateValue, timeValue);
        if (!eventDateTime) {
            setFieldError(dateInputEl, dateErrorId, MSG.invalidDate);
            setFieldError(timeInputEl, timeErrorId, MSG.invalidTime);
            return false;
        }

        if (eventDateTime < new Date()) {
            setFieldError(dateInputEl, dateErrorId, MSG.pastDateTime);
            setFieldError(timeInputEl, timeErrorId, MSG.pastDateTime);
            return false;
        }

        return true;
    }

    function validateCreateEventForm() {
        let isValid = true;

        const titleValue = titleInput ? titleInput.value.trim() : '';
        const descriptionValue = descInput ? descInput.value.trim() : '';
        const dateValue = dateInput ? dateInput.value : '';
        const timeValue = timeInput ? timeInput.value : '';
        const locationValue = locationInput ? locationInput.value.trim() : '';

        if (!titleValue) {
            setFieldError(titleInput, 'event-title-error', MSG.titleRequired);
            isValid = false;
        } else {
            setFieldError(titleInput, 'event-title-error', '');
        }

        if (!descriptionValue) {
            setFieldError(descInput, 'event-description-error', MSG.descriptionRequired);
            isValid = false;
        } else {
            setFieldError(descInput, 'event-description-error', '');
        }

        if (!dateValue) {
            setFieldError(dateInput, 'event-date-error', MSG.dateRequired);
            isValid = false;
        } else {
            setFieldError(dateInput, 'event-date-error', '');
        }

        if (!timeValue) {
            setFieldError(timeInput, 'event-time-error', MSG.timeRequired);
            isValid = false;
        } else {
            setFieldError(timeInput, 'event-time-error', '');
        }

        if (dateValue && timeValue) {
            const dateTimeValid = validateEventDateTime(
                dateInput,
                timeInput,
                'event-date-error',
                'event-time-error'
            );
            if (!dateTimeValid) {
                isValid = false;
            } else {
                setFieldError(dateInput, 'event-date-error', '');
                setFieldError(timeInput, 'event-time-error', '');
            }
        }

        if (!locationValue) {
            setFieldError(locationInput, 'event-location-error', MSG.locationRequired);
            isValid = false;
        } else {
            setFieldError(locationInput, 'event-location-error', '');
        }

        return isValid;
    }

    function validateEditEventForm() {
        let isValid = true;

        const titleValue = editTitleInput ? editTitleInput.value.trim() : '';
        const descriptionValue = editDescriptionInput ? editDescriptionInput.value.trim() : '';
        const dateValue = editDateInput ? editDateInput.value : '';
        const timeValue = editTimeInput ? editTimeInput.value : '';
        const locationValue = editLocationInput ? editLocationInput.value.trim() : '';

        if (!titleValue) {
            setFieldError(editTitleInput, 'edit-event-title-error', MSG.titleRequired);
            isValid = false;
        } else {
            setFieldError(editTitleInput, 'edit-event-title-error', '');
        }

        if (!descriptionValue) {
            setFieldError(editDescriptionInput, 'edit-event-description-error', MSG.descriptionRequired);
            isValid = false;
        } else {
            setFieldError(editDescriptionInput, 'edit-event-description-error', '');
        }

        if (!dateValue) {
            setFieldError(editDateInput, 'edit-event-date-error', MSG.dateRequired);
            isValid = false;
        } else {
            setFieldError(editDateInput, 'edit-event-date-error', '');
        }

        if (!timeValue) {
            setFieldError(editTimeInput, 'edit-event-time-error', MSG.timeRequired);
            isValid = false;
        } else {
            setFieldError(editTimeInput, 'edit-event-time-error', '');
        }

        if (dateValue && timeValue) {
            const dateTimeValid = validateEventDateTime(
                editDateInput,
                editTimeInput,
                'edit-event-date-error',
                'edit-event-time-error'
            );
            if (!dateTimeValid) {
                isValid = false;
            } else {
                setFieldError(editDateInput, 'edit-event-date-error', '');
                setFieldError(editTimeInput, 'edit-event-time-error', '');
            }
        }

        if (!locationValue) {
            setFieldError(editLocationInput, 'edit-event-location-error', MSG.locationRequired);
            isValid = false;
        } else {
            setFieldError(editLocationInput, 'edit-event-location-error', '');
        }

        return isValid;
    }

    const todayISO = getTodayISO();
    if (dateInput) dateInput.setAttribute('min', todayISO);
    if (editDateInput) editDateInput.setAttribute('min', todayISO);

    if (descInput && counter) {
        descInput.addEventListener('input', () => {
            counter.innerText = `${descInput.value.length} / 500`;
        });
    }

    if (eventForm && descInput) {
        eventForm.addEventListener('submit', (event) => {
            const isValid = validateCreateEventForm();
            if (!isValid) {
                event.preventDefault();
                return;
            }
            descInput.value = descInput.value
                .replace(/\r\n/g, '\n')
                .replace(/\n{3,}/g, '\n\n')
                .trim();
        });

        titleInput && titleInput.addEventListener('input', validateCreateEventForm);
        descInput.addEventListener('input', validateCreateEventForm);
        dateInput && dateInput.addEventListener('change', validateCreateEventForm);
        timeInput && timeInput.addEventListener('change', validateCreateEventForm);
        locationInput && locationInput.addEventListener('input', validateCreateEventForm);
    }

    window.toggleDescription = function toggleDescription(id, btn) {
        const container = document.getElementById('desc-' + id);
        if (!container) return;
        if (container.classList.contains('desc-expanded')) {
            container.classList.remove('desc-expanded');
            btn.innerText = 'Ver mais';
        } else {
            container.classList.add('desc-expanded');
            btn.innerText = 'Ver menos';
        }
    };

    function initDescriptionToggles() {
        const descBlocks = document.querySelectorAll('[id^="desc-"]');
        descBlocks.forEach((block) => {
            const id = block.id.replace('desc-', '');
            const toggleBtn = document.querySelector(`[data-desc-toggle="${id}"]`);
            if (!toggleBtn) return;

            if (block.scrollHeight > block.clientHeight + 4) {
                toggleBtn.classList.remove('hidden');
                toggleBtn.innerText = 'Ver mais';
            } else {
                toggleBtn.classList.add('hidden');
            }
        });
    }

    window.addEventListener('load', initDescriptionToggles);

    window.previewEventImage = function previewEventImage(input) {
        const preview = document.getElementById('event-image-preview');
        const removeBtn = document.getElementById('remove-preview');
        if (input.files && input.files[0]) {
            const reader = new FileReader();
            reader.onload = function (e) {
                preview.src = e.target.result;
                preview.style.display = 'block';
                removeBtn.classList.remove('hidden');
            };
            reader.readAsDataURL(input.files[0]);
        }
    };

    window.removeImagePreview = function removeImagePreview() {
        const input = document.getElementById('event-file-input');
        const preview = document.getElementById('event-image-preview');
        const removeBtn = document.getElementById('remove-preview');
        input.value = '';
        preview.src = '#';
        preview.style.display = 'none';
        removeBtn.classList.add('hidden');
    };

    window.closeEventModal = function closeEventModal() {
        const modal = document.getElementById('modal-evento');
        if (modal) modal.classList.remove('active');
        window.removeImagePreview();
    };

    function openEditEventModal(eventId, title, description, date, time, location) {
        const modal = document.getElementById('modal-editar-evento');
        const form = document.getElementById('edit-event-form');
        if (!modal || !form) return;

        form.setAttribute('action', `/editar_evento/${eventId}`);
        document.getElementById('edit-event-title').value = title || '';
        document.getElementById('edit-event-description').value = description || '';
        document.getElementById('edit-event-date').value = date || '';
        document.getElementById('edit-event-time').value = time || '';
        document.getElementById('edit-event-location').value = location || '';
        modal.classList.add('active');
    }

    window.closeEditEventModal = function closeEditEventModal() {
        const modal = document.getElementById('modal-editar-evento');
        if (modal) modal.classList.remove('active');
    };

    if (createEventModal) {
        createEventModal.addEventListener('click', (event) => {
            if (event.target === createEventModal) {
                window.closeEventModal();
            }
        });
    }

    if (editEventModal) {
        editEventModal.addEventListener('click', (event) => {
            if (event.target === editEventModal) {
                window.closeEditEventModal();
            }
        });
    }

    document.addEventListener('click', (event) => {
        const trigger = event.target.closest('[data-edit-event="true"]');
        if (!trigger) return;
        event.preventDefault();
        openEditEventModal(
            trigger.getAttribute('data-event-id') || '',
            trigger.getAttribute('data-event-title') || '',
            trigger.getAttribute('data-event-description') || '',
            trigger.getAttribute('data-event-date') || '',
            trigger.getAttribute('data-event-time') || '',
            trigger.getAttribute('data-event-location') || ''
        );
    });

    if (editEventForm) {
        editEventForm.addEventListener('submit', (event) => {
            const isValid = validateEditEventForm();
            if (!isValid) {
                event.preventDefault();
                return;
            }
            if (!editDescriptionInput) return;
            editDescriptionInput.value = editDescriptionInput.value
                .replace(/\r\n/g, '\n')
                .replace(/\n{3,}/g, '\n\n')
                .trim();
        });

        editTitleInput && editTitleInput.addEventListener('input', validateEditEventForm);
        editDescriptionInput && editDescriptionInput.addEventListener('input', validateEditEventForm);
        editDateInput && editDateInput.addEventListener('change', validateEditEventForm);
        editTimeInput && editTimeInput.addEventListener('change', validateEditEventForm);
        editLocationInput && editLocationInput.addEventListener('input', validateEditEventForm);
    }
})();
``
