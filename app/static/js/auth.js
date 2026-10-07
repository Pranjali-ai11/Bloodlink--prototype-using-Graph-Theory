const API_BASE = '';
let capturedDonorLocation = null;
document.addEventListener('DOMContentLoaded', function() {
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        markRequiredFields('register-form', ['name', 'email', 'phone', 'age', 'blood_group', 'gender', 'password', 'confirm_password', 'role']);
        attachFieldValidation('phone', validatePhone);
        attachFieldValidation('age', validateAge);
        attachFieldValidation('password', validatePassword);
        attachFieldValidation('email', validateEmail);
    }
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        markRequiredFields('login-form', ['email', 'password']);
        attachFieldValidation('email', validateEmail);
    }
});
const registerForm = document.getElementById('register-form');
if (registerForm) {
    registerForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const role = document.getElementById('role').value;
        const requiredFields = [
            { id: 'name', validate: null },
            { id: 'email', validate: validateEmail },
            { id: 'phone', validate: validatePhone },
            { id: 'age', validate: validateAge },
            { id: 'blood_group', validate: null },
            { id: 'gender', validate: null },
            { id: 'password', validate: validatePassword },
            { id: 'confirm_password', validate: null },
            { id: 'role', validate: null }
        ].filter(field => field.id !== 'blood_group' || role === 'donor');
        const isFormValid = validateFormBeforeSubmit('register-form', requiredFields);
        
        if (!isFormValid) {
            showMessage(document.getElementById('message'), 'Please fix the errors above', 'error');
            return;
        }
        
        const name = document.getElementById('name').value;
        const email = document.getElementById('email').value;
        const phone = document.getElementById('phone').value;
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirm_password').value;
        const gender = document.getElementById('gender').value;
        const age = Number(document.getElementById('age').value);
        
        if (password !== confirmPassword) {
            showMessage(document.getElementById('message'), 'Passwords do not match', 'error');
            return;
        }
        
        const data = {
            name,
            email,
            phone,
            password,
            role,
            gender,
            age,
            blood_group: document.getElementById('blood_group').value
        };
        if (role === 'donor') {
            data.city = document.getElementById('city').value;
            data.address = document.getElementById('address').value;
            if (capturedDonorLocation) {
                data.latitude = capturedDonorLocation.latitude;
                data.longitude = capturedDonorLocation.longitude;
                submitRegister(data);
            } else if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(function(position) {
                    data.latitude = position.coords.latitude;
                    data.longitude = position.coords.longitude;
                    submitRegister(data);
                }, function() {

                    submitRegister(data);
                });
            } else {
                submitRegister(data);
            }
        } else {
            submitRegister(data);
        }
    });
    const getLocBtn = document.getElementById('get-location-btn');
    if (getLocBtn) {
        getLocBtn.addEventListener('click', function() {
            const locationStatus = document.getElementById('register-location-status');
            const setLocationStatus = (message, isError = false) => {
                if (!locationStatus) return;
                locationStatus.textContent = message;
                locationStatus.hidden = false;
                locationStatus.classList.toggle('is-error', isError);
            };

            if (navigator.geolocation) {
                this.textContent = 'Getting location...';
                this.disabled = true;
                setLocationStatus('Requesting your current location…');
                navigator.geolocation.getCurrentPosition(
                    async function(position) {
                        const lat = position.coords.latitude;
                        const lng = position.coords.longitude;
                        capturedDonorLocation = { latitude: lat, longitude: lng };
                        const coordsText = `Coordinates: ${lat.toFixed(5)}, ${lng.toFixed(5)}`;
                        let placeText = '';
                        try {
                            const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}`);
                            if (!response.ok) throw new Error('Address lookup unavailable');
                            const data = await response.json();
                            const address = data.address || {};
                            const city = address.city || address.town || address.village || address.municipality || address.county || address.state_district || '';
                            const street = [address.house_number, address.road || address.pedestrian || address.neighbourhood || address.suburb].filter(Boolean).join(' ');
                            if (city) document.getElementById('city').value = city;
                            if (street || data.display_name) document.getElementById('address').value = street || data.display_name;
                            placeText = [street, city].filter(Boolean).join(', ');
                        } catch (error) {
                            console.warn('Reverse geocoding unavailable:', error);
                        }
                        setLocationStatus(placeText ? `Current location: ${placeText} · ${coordsText}` : `Current location captured · ${coordsText}`);
                        getLocBtn.textContent = 'Location obtained ✓';
                        getLocBtn.disabled = false;
                    },
                    function(error) {
                        capturedDonorLocation = null;
                        getLocBtn.textContent = 'Get My Location';
                        getLocBtn.disabled = false;
                        setLocationStatus('Could not get location: ' + error.message, true);
                        showMessage(document.getElementById('message'), 
                            'Could not get location: ' + error.message, 'error');
                    },
                    { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 }
                );
            } else {
                setLocationStatus('Current location is not supported by this browser.', true);
                showMessage(document.getElementById('message'), 
                    'Geolocation is not supported', 'error');
            }
        });
    }
    const roleSelect = document.getElementById('role');
    const donorSection = document.getElementById('donor-section');
    
    if (roleSelect) {
        roleSelect.addEventListener('change', function() {
            if (this.value === 'donor') {
                donorSection.style.display = 'block';
                document.getElementById('blood_group').required = true;
            } else {
                donorSection.style.display = 'none';
                document.getElementById('blood_group').required = false;
            }
        });
        if (roleSelect.value === 'donor') {
            donorSection.style.display = 'block';
            document.getElementById('blood_group').required = true;
        } else {
            donorSection.style.display = 'none';
            document.getElementById('blood_group').required = false;
        }
    }
}

async function submitRegister(data) {
    try {
        const response = await fetch(`${API_BASE}/api/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage(document.getElementById('message'), 
                'Registration successful! Redirecting...', 'success');
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 2000);
        } else {
            showMessage(document.getElementById('message'), 
                result.error || 'Registration failed', 'error');
        }
    } catch (error) {
        showMessage(document.getElementById('message'), 
            'Error: ' + error.message, 'error');
    }
}
const loginForm = document.getElementById('login-form');
if (loginForm) {
    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        
        try {
            const response = await fetch(`${API_BASE}/api/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });
            
            const result = await response.json();
            if (response.ok) {
    showMessage(document.getElementById('message'), 
        'Login successful! Redirecting...', 'success');

    setTimeout(() => {
        if (result.user.role === 'admin') {
            window.location.href = '/admin/hospitals';
        } else {
            window.location.href = '/dashboard';
        }
    }, 1500);
}
             else {
                showMessage(document.getElementById('message'), 
                    result.error || 'Login failed', 'error');
            }
        } catch (error) {
            showMessage(document.getElementById('message'), 
                'Error: ' + error.message, 'error');
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
