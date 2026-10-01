const API_BASE = '';
let currentDonorId = null;

document.addEventListener('DOMContentLoaded', function() {
    loadDashboard();
    const editAgeButton = document.getElementById('edit-age-btn');
    const ageUpdateForm = document.getElementById('age-update-form');
    if (editAgeButton && ageUpdateForm) {
        editAgeButton.addEventListener('click', function() {
            ageUpdateForm.hidden = !ageUpdateForm.hidden;
            if (!ageUpdateForm.hidden) document.getElementById('profile-age').focus();
        });
        ageUpdateForm.addEventListener('submit', saveDonorAge);
    }
});

async function loadDashboard() {
    try {
        const response = await fetch(`${API_BASE}/api/current-user`);
        
        if (!response.ok) {
            window.location.href = '/login';
            return;
        }
        
        const user = await response.json();
        document.getElementById('user-name').textContent = user.name;
        document.getElementById('user-email').textContent = user.email;
        if (user.donor) {
            const donorSection = document.getElementById('donor-section');
            donorSection.style.display = 'block';
            currentDonorId = user.donor.donor_id;
            
            document.getElementById('donor-blood-group').textContent = user.donor.blood_group;
            document.getElementById('donor-location').textContent = user.donor.city || user.donor.address || 'N/A';
            document.getElementById('donor-age').textContent = user.age ?? 'Not provided';
            const availability = document.getElementById('donor-availability');
            const canDonate = Boolean(user.donor.is_eligible);
            const isDiscoverable = Boolean(user.donor.is_available && canDonate);
            availability.textContent = isDiscoverable ? 'Available' : 'Unavailable';
            availability.className = `status-pill ${isDiscoverable ? 'status-available' : 'status-pending'}`;
            document.getElementById('donor-count').textContent = user.donor.donation_count;
            document.getElementById('last-donation').textContent = user.donor.last_donation_date || 'Never';
            const eligibility = user.donor;
            const eligibilityStatus = document.getElementById('eligibility-status');
            if (eligibility.is_eligible) {
                eligibilityStatus.textContent = 'Eligible to Donate';
                eligibilityStatus.className = 'status-pill status-available';
            } else if (eligibility.eligibility_status === 'waiting_period') {
                eligibilityStatus.textContent = `Eligible after ${eligibility.eligible_after}`;
                eligibilityStatus.className = 'status-pill status-pending';
            } else if (eligibility.eligibility_status === 'age_required') {
                eligibilityStatus.textContent = 'Age Needed';
                eligibilityStatus.className = 'status-pill status-pending';
            } else {
                eligibilityStatus.textContent = 'Not Eligible';
                eligibilityStatus.className = 'status-pill status-critical';
            }
            document.getElementById('eligibility-reason').textContent = eligibility.is_eligible
                ? ''
                : (eligibility.eligibility_status === 'age_required'
                    ? 'Add your age to confirm eligibility and appear in donor search.'
                    : eligibility.eligibility_reason);
            const ageForm = document.getElementById('age-update-form');
            const editAgeButton = document.getElementById('edit-age-btn');
            document.getElementById('profile-age').value = user.age ?? '';
            ageForm.hidden = user.age !== null && user.age !== undefined;
            editAgeButton.hidden = user.age === null || user.age === undefined;
            const availabilityButton = document.getElementById('toggle-availability-btn');
            availabilityButton.innerHTML = `<i class="fas fa-arrows-rotate"></i> ${user.donor.is_available ? 'Mark unavailable' : 'Set as available'}`;
            availabilityButton.onclick = toggleAvailability;
        }
        await Promise.all([loadDonorStats(), loadRequests(), loadMedicalHistorySummary()]);
        
    } catch (error) {
        console.error('Error loading dashboard:', error);
        window.location.href = '/login';
    }
}

async function loadMedicalHistorySummary() {
    const indicator = document.getElementById('medical-history-updated-indicator');
    if (!indicator) return;
    try {
        const response = await fetch(`${API_BASE}/api/medical-history`);
        if (!response.ok) throw new Error('Unable to load status');
        const { medical_history: history } = await response.json();
        if (history && history.updated_at) {
            indicator.textContent = `Medical History Updated · ${new Date(history.updated_at).toLocaleDateString()}`;
            indicator.className = 'status-pill status-available';
        } else {
            indicator.textContent = 'Not added yet';
            indicator.className = 'status-pill status-pending';
        }
    } catch (error) {
        indicator.textContent = 'View medical history';
        indicator.className = 'status-pill status-normal';
    }
}

async function loadRequests() {
    const list = document.getElementById('requests-list');
    const activeCount = document.getElementById('stat-requests');
    if (!list) return;

    try {
        const response = await fetch(`${API_BASE}/api/requests`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Could not load your requests.');

        const requests = data.requests || [];
        if (activeCount) activeCount.textContent = requests.filter(item => item.status === 'active').length;
        if (requests.length === 0) {
            list.innerHTML = '<div class="requests-empty"><i class="fas fa-heart-pulse"></i><p>No blood requests yet.</p><span>Your requests will appear here after you submit one.</span></div>';
            return;
        }

        list.innerHTML = requests.map(item => {
            const status = String(item.status || 'active').toLowerCase();
            const urgency = String(item.urgency_level || 'normal').toLowerCase();
            const safeUrgency = ['normal', 'urgent', 'critical'].includes(urgency) ? urgency : 'normal';
            const createdDate = item.created_at ? new Date(item.created_at).toLocaleDateString() : '';
            return `<article class="request-item">
                <div class="request-item-heading"><h3>${escapeRequestText(item.blood_group)} blood needed</h3><span class="status-pill ${status === 'fulfilled' ? 'status-available' : status === 'active' ? 'status-pending' : 'status-normal'}">${escapeRequestText(status.charAt(0).toUpperCase() + status.slice(1))}</span></div>
                <p><i class="fas fa-location-dot"></i> ${escapeRequestText(item.location || 'Location not provided')}</p>
                <div class="request-item-meta"><span class="request-urgency urgency-${safeUrgency}">${escapeRequestText(safeUrgency)} priority</span><span>${escapeRequestText(createdDate)}</span></div>
            </article>`;
        }).join('');
    } catch (error) {
        list.innerHTML = `<div class="requests-empty request-error"><p>${escapeRequestText(error.message)}</p></div>`;
    }
}

function escapeRequestText(value) {
    return String(value ?? '').replace(/[&<>"']/g, character => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[character]);
}

async function saveDonorAge(event) {
    event.preventDefault();
    const ageField = document.getElementById('profile-age');
    const age = Number(ageField.value);
    const feedback = document.getElementById('age-update-message');
    if (!Number.isInteger(age) || age < 0) {
        feedback.textContent = 'Please enter a valid age as a whole number.';
        feedback.className = 'message error';
        feedback.style.display = 'block';
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/donors/${currentDonorId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ age })
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Unable to update your age.');
        feedback.textContent = 'Age saved. Your eligibility has been updated.';
        feedback.className = 'message success';
        feedback.style.display = 'block';
        await loadDashboard();
    } catch (error) {
        feedback.textContent = error.message;
        feedback.className = 'message error';
        feedback.style.display = 'block';
    }
}

async function toggleAvailability() {
    try {
        const user = await fetch(`${API_BASE}/api/current-user`).then(r => r.json());
        const donorId = user.donor.donor_id;
        const newStatus = !user.donor.is_available;
        
        const response = await fetch(`${API_BASE}/api/donors/${donorId}/availability`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ is_available: newStatus })
        });
        
        if (response.ok) {
            const feedback = document.getElementById('availability-message');
            feedback.style.display = 'none';
            loadDashboard();
        } else {
            const result = await response.json();
            const feedback = document.getElementById('availability-message');
            feedback.textContent = result.error || 'Failed to update availability.';
            feedback.className = 'message error';
            feedback.style.display = 'block';
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

async function loadDonorStats() {
    try {
        const donorsResponse = await fetch(`${API_BASE}/api/donors?page=1`);
        const donorsData = await donorsResponse.json();
        
        document.getElementById('stat-donors').textContent = donorsData.total;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}
const logoutBtn = document.getElementById('logout-btn');
if (logoutBtn) {
    logoutBtn.addEventListener('click', async function() {
        try {
            await fetch(`${API_BASE}/api/logout`, { method: 'POST' });
            window.location.href = '/';
        } catch (error) {
            console.error('Logout error:', error);
        }
    });
}
const createRequestBtn = document.getElementById('create-request-btn');
const requestModal = document.getElementById('request-modal');
const closeBtn = document.querySelector('.close');

if (createRequestBtn) {
    createRequestBtn.addEventListener('click', function() {
        requestModal.style.display = 'block';
    });
}

if (closeBtn) {
    closeBtn.addEventListener('click', function() {
        requestModal.style.display = 'none';
    });
}

window.addEventListener('click', function(event) {
    if (event.target === requestModal) {
        requestModal.style.display = 'none';
    }
});
const getCurrentLocationBtn = document.getElementById('get-current-location-btn');
if (getCurrentLocationBtn) {
    getCurrentLocationBtn.addEventListener('click', function(e) {
        e.preventDefault();
        
        if (!navigator.geolocation) {
            alert('Geolocation is not supported by your browser');
            return;
        }
        
        this.textContent = '⏳ Getting location...';
        this.disabled = true;
        
        navigator.geolocation.getCurrentPosition(
            function(position) {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                
                // Store coordinates
                document.getElementById('request-coords').value = `${lat}, ${lng}`;
                document.getElementById('coordinates-group').style.display = 'block';
                fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`)
                    .then(r => r.json())
                    .then(data => {
                        if (data.address) {
                            const address = `${data.address.road || ''} ${data.address.neighbourhood || ''}, ${data.address.city || data.address.town || ''}`.trim();
                            document.getElementById('request-location').value = address;
                        }
                        
                        const locationStatus = document.getElementById('location-status');
                        locationStatus.textContent = '✓ Location captured (Lat: ' + lat.toFixed(4) + ', Lng: ' + lng.toFixed(4) + ')';
                        locationStatus.style.color = '#90ee90';
                        locationStatus.style.display = 'block';
                        
                        getCurrentLocationBtn.textContent = '📍 Location obtained ✓';
                        getCurrentLocationBtn.disabled = false;
                    })
                    .catch(e => {
                        console.error('Geolocation error:', e);
                        const locationStatus = document.getElementById('location-status');
                        locationStatus.textContent = '✓ Coordinates captured (address lookup failed)';
                        locationStatus.style.display = 'block';
                        getCurrentLocationBtn.textContent = '📍 Location obtained ✓';
                        getCurrentLocationBtn.disabled = false;
                    });
            },
            function(error) {
                let errorMsg = '';
                switch(error.code) {
                    case error.PERMISSION_DENIED:
                        errorMsg = 'Permission to access location denied';
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errorMsg = 'Location information unavailable';
                        break;
                    case error.TIMEOUT:
                        errorMsg = 'Location request timed out';
                        break;
                    default:
                        errorMsg = 'Error getting location: ' + error.message;
                }
                
                const locationStatus = document.getElementById('location-status');
                locationStatus.textContent = '✗ ' + errorMsg;
                locationStatus.style.color = '#ffb6c1';
                locationStatus.style.display = 'block';
                
                getCurrentLocationBtn.textContent = '📍 Use Live Location';
                getCurrentLocationBtn.disabled = false;
            }
        );
    });
}
const createRequestForm = document.getElementById('create-request-form');
if (createRequestForm) {
    createRequestForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const bloodGroup = document.getElementById('request-blood-group').value;
        const location = document.getElementById('request-location').value;
        const urgencyLevel = document.getElementById('request-urgency').value;
        const coords = document.getElementById('request-coords').value;
        
        if (!bloodGroup || !location) {
            alert('Please select blood group and enter location');
            return;
        }
        
        let lat, lng;
        
        try {
            if (coords) {
                const [latStr, lngStr] = coords.split(',').map(v => v.trim());
                lat = parseFloat(latStr);
                lng = parseFloat(lngStr);
            } else if (navigator.geolocation) {
                const position = await new Promise((resolve, reject) => {
                    navigator.geolocation.getCurrentPosition(resolve, reject);
                });
                lat = position.coords.latitude;
                lng = position.coords.longitude;
            }
            
            const response = await fetch(`${API_BASE}/api/requests`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    blood_group: bloodGroup,
                    location: location,
                    urgency_level: urgencyLevel,
                    latitude: lat,
                    longitude: lng
                })
            });
            
            if (response.ok) {
                alert('Blood request created successfully!');
                requestModal.style.display = 'none';
                createRequestForm.reset();
                document.getElementById('coordinates-group').style.display = 'none';
                document.getElementById('location-status').style.display = 'none';
                document.getElementById('get-current-location-btn').textContent = '📍 Use Live Location';
                await loadDashboard();
            } else {
                const error = await response.json();
                alert('Error: ' + (error.error || 'Failed to create request'));
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error: ' + error.message);
        }
    });
}
function showMessage(element, message, type = 'success') {
    if (!element) return;
    
    element.textContent = message;
    element.className = `message ${type}`;
    element.style.display = 'block';
    
    if (type === 'success') {
        setTimeout(() => {
            element.style.display = 'none';
        }, 3000);
    }
}
