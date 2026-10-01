const API_BASE = '';
async function checkLoginStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/current-user`);
        
        if (response.ok) {
            const user = await response.json();
            updateNavForLoggedIn(user);
            return user;
        } else {
            updateNavForLoggedOut();
            return null;
        }
    } catch (error) {
        console.error('Error checking login status:', error);
        updateNavForLoggedOut();
        return null;
    }
}

function updateNavForLoggedIn(user) {
    const authNav = document.getElementById('auth-nav');
    const userNav = document.getElementById('user-nav');
    
    if (authNav) authNav.style.display = 'none';
    if (userNav) {
        userNav.style.display = 'block';
        userNav.innerHTML = `
            <a href="/dashboard" class="btn btn-primary">Dashboard</a>
            <button id="logout-btn" class="btn btn-primary">Logout</button>
        `;
        document.getElementById('logout-btn').addEventListener('click', logout);
    }
}

function updateNavForLoggedOut() {
    const authNav = document.getElementById('auth-nav');
    const userNav = document.getElementById('user-nav');
    
    if (authNav) authNav.style.display = 'block';
    if (userNav) userNav.style.display = 'none';
}

async function logout() {
    try {
        await fetch(`${API_BASE}/api/logout`, { method: 'POST' });
        window.location.href = '/';
    } catch (error) {
        console.error('Logout error:', error);
    }
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
document.addEventListener('DOMContentLoaded', function() {
    checkLoginStatus();
    loadHomeDonorCount();
    const bloodBtns = document.querySelectorAll('.blood-btn');
    bloodBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const bloodGroup = this.getAttribute('data-group');
            window.location.href = `/search?blood_group=${bloodGroup}`;
        });
    });
});

async function loadHomeDonorCount() {
    const countElement = document.getElementById('home-donor-count');
    if (!countElement) return;
    try {
        const response = await fetch(`${API_BASE}/api/donors?page=1`);
        if (!response.ok) return;
        const data = await response.json();
        countElement.textContent = new Intl.NumberFormat().format(data.total || 0);
    } catch (error) {
        console.error('Error loading donor count:', error);
    }
}
