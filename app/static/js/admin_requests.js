document.querySelectorAll('.request-save').forEach(button => button.addEventListener('click', async () => {
    const id = button.dataset.requestId;
    const status = document.querySelector(`.request-status[data-request-id="${id}"]`).value;
    const urgency_level = document.querySelector(`.request-urgency[data-request-id="${id}"]`).value;
    const message = document.getElementById('request-message'); button.disabled = true;
    try { const response = await fetch(`/api/requests/${id}`, { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify({status, urgency_level}) }); const data = await response.json(); if (!response.ok) throw new Error(data.error || 'Unable to update request.'); message.textContent = `Request #${id} updated.`; message.className = 'message message-success'; window.location.reload(); }
    catch (error) { message.textContent = error.message; message.className = 'message message-error'; button.disabled = false; }
}));
