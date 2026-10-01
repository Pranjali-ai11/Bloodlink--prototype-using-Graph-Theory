const MEDICAL_HISTORY_API = '/api/medical-history';
const MEDICAL_HISTORY_FIELDS = [
    'allergies', 'chronic_conditions', 'current_medications', 'previous_surgeries',
    'previous_major_illnesses', 'recent_illness', 'last_checkup_date', 'additional_notes'
];

document.addEventListener('DOMContentLoaded', () => {
    loadMedicalHistory();
    document.getElementById('medical-history-form').addEventListener('submit', saveMedicalHistory);
});

async function loadMedicalHistory() {
    const saveButton = document.getElementById('save-medical-history');
    saveButton.disabled = true;
    try {
        const response = await fetch(MEDICAL_HISTORY_API);
        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Could not load your medical history.');
        const history = result.medical_history;
        if (history) {
            MEDICAL_HISTORY_FIELDS.forEach(field => {
                document.getElementById(field).value = history[field] || '';
            });
            document.getElementById('medical-history-updated').textContent = history.updated_at
                ? `Medical History Updated ${new Date(history.updated_at).toLocaleString()}`
                : 'Your saved information is shown below.';
        }
    } catch (error) {
        showMedicalHistoryMessage(error.message, 'error');
    } finally {
        saveButton.disabled = false;
    }
}

async function saveMedicalHistory(event) {
    event.preventDefault();
    const saveButton = document.getElementById('save-medical-history');
    const originalLabel = saveButton.innerHTML;
    saveButton.disabled = true;
    saveButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving…';
    const medicalHistory = Object.fromEntries(MEDICAL_HISTORY_FIELDS.map(field => [
        field,
        document.getElementById(field).value.trim() || null
    ]));

    try {
        const response = await fetch(MEDICAL_HISTORY_API, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(medicalHistory)
        });
        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Could not save your medical history.');
        const updated = result.medical_history.updated_at;
        document.getElementById('medical-history-updated').textContent = updated
            ? `Medical History Updated ${new Date(updated).toLocaleString()}`
            : 'Medical history saved.';
        showMedicalHistoryMessage('Your medical history has been saved.', 'success');
    } catch (error) {
        showMedicalHistoryMessage(error.message, 'error');
    } finally {
        saveButton.disabled = false;
        saveButton.innerHTML = originalLabel;
    }
}

function showMedicalHistoryMessage(message, type) {
    const element = document.getElementById('medical-history-message');
    element.textContent = message;
    element.className = `message ${type}`;
    element.style.display = 'block';
}
