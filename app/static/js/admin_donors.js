document.addEventListener('DOMContentLoaded', function () {
    const message = document.getElementById('donation-message');
    document.querySelectorAll('.record-donation-btn').forEach(button => {
        button.addEventListener('click', async function () {
            const donorId = this.dataset.donorId;
            const originalText = this.textContent;
            this.disabled = true;
            this.textContent = 'Saving…';
            message.style.display = 'none';

            try {
                const response = await fetch(`/api/admin/donors/${donorId}/complete-donation`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });
                const result = await response.json();
                if (!response.ok) {
                    throw new Error(result.error || 'Could not record the donation.');
                }

                message.textContent = result.message;
                message.className = 'message success';
                message.style.display = 'block';
                window.setTimeout(() => window.location.reload(), 700);
            } catch (error) {
                message.textContent = error.message;
                message.className = 'message error';
                message.style.display = 'block';
                this.disabled = false;
                this.textContent = originalText;
            }
        });
    });
});
