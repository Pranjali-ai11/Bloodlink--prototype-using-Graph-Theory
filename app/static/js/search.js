const API_BASE = "";

let map = null;
let markers = [];
function applyQuickAccessBloodGroup() {
    const params = new URLSearchParams(window.location.search);
    const bg = params.get("blood_group")?.replace(" ", "+");

    if (bg) {
        const select = document.getElementById("blood-group");
        if (select) select.value = bg;
    }
}

document.addEventListener('DOMContentLoaded', function () {
    initializeMap();
    attachSearchHandlers();
    applyQuickAccessBloodGroup();  
});

function initializeMap() {
    const mapElement = document.getElementById('map');

    if (mapElement && map === null) {
        map = L.map('map').setView([18.5204, 73.8567], 12); 

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);
        setTimeout(() => {
            map.invalidateSize();
        }, 200);
    }
}
window.addEventListener("load", function () {
    if (map) {
        map.invalidateSize();
    }
});

function attachSearchHandlers() {
    const searchBtn = document.getElementById('search-btn');
    const currentLocBtn = document.getElementById('current-location-btn');

    if (searchBtn) {
        searchBtn.addEventListener('click', performSearch);
    }

    if (currentLocBtn) {
        currentLocBtn.addEventListener('click', getCurrentLocation);
    }
}

function getCurrentLocation() {
    if (navigator.geolocation) {
        document.getElementById('current-location-btn').textContent = 'Getting location...';

        navigator.geolocation.getCurrentPosition(function (position) {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            map.setView([lat, lng], 13);
            L.circleMarker([lat, lng], {
                radius: 10,
                color: '#3498db',
                fillColor: '#3498db',
                fillOpacity: 0.8
            }).addTo(map).bindPopup('Your Location');
            window.currentLocation = { lat, lng };

            document.getElementById('current-location-btn').textContent = 'Location obtained ✓';
            performSearch();
        }, function (error) {
            alert('Could not get your location: ' + error.message);
        });
    } else {
        alert('Geolocation is not supported by your browser');
    }
}

async function performSearch() {
    let bloodGroup = document.getElementById('blood-group')?.value;
    if (!bloodGroup) {
        const params = new URLSearchParams(window.location.search);
        bloodGroup = params.get("blood_group")?.replace(" ", "+");
    }

    const radius = parseInt(document.getElementById('radius')?.value || 10);
    const urgency = document.getElementById('urgency')?.value || 2;

    if (!bloodGroup) {
        alert('Please select a blood group');
        return;
    }

    if (!window.currentLocation) {
        alert('Please select your location first');
        return;
    }

    const userLat = window.currentLocation.lat;
    const userLng = window.currentLocation.lng;

    try {
        const response = await fetch(`${API_BASE}/api/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                blood_group: bloodGroup,
                latitude: userLat,
                longitude: userLng,
                radius_km: radius,
                urgency: urgency
            })
        });

        const data = await response.json();

        if (response.ok) {
            displayDonors(data.donors || []);
            const [banksResult, hospitalsResult] = await Promise.allSettled([
                fetch(`${API_BASE}/api/blood-banks`).then(async result => {
                    if (!result.ok) throw new Error('Blood-bank directory request failed');
                    return result.json();
                }),
                fetch(`${API_BASE}/api/hospitals`).then(async result => {
                    if (!result.ok) throw new Error('Hospital directory request failed');
                    return result.json();
                })
            ]);
            const banks = banksResult.status === 'fulfilled'
                ? banksResult.value.blood_banks || [] : null;
            const hospitals = hospitalsResult.status === 'fulfilled'
                ? hospitalsResult.value.hospitals || [] : null;
            displayFacilityResults(banks, hospitals, bloodGroup, userLat, userLng, radius);
        } else {
            alert('Search failed: ' + (data.error || 'Unknown error'));
        }

    } catch (error) {
        alert('Error: ' + error.message);
    }
}

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, character => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    })[character]);
}

function formatRankValue(value, decimals = 0) {
    if (value === null || value === undefined || value === '') return 'N/A';
    const number = Number(value);
    return Number.isFinite(number) ? number.toFixed(decimals) : 'N/A';
}

function coordinatesFor(location) {
    if (location.latitude === null || location.latitude === undefined ||
        location.longitude === null || location.longitude === undefined) return null;
    const latitude = Number(location.latitude);
    const longitude = Number(location.longitude);
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude) ||
        latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) return null;
    return { latitude, longitude };
}

function distanceBetween(lat1, lon1, lat2, lon2) {
    const radians = degrees => degrees * Math.PI / 180;
    const latitudeDelta = radians(lat2 - lat1);
    const longitudeDelta = radians(lon2 - lon1);
    const arc = Math.sin(latitudeDelta / 2) ** 2 +
        Math.cos(radians(lat1)) * Math.cos(radians(lat2)) *
        Math.sin(longitudeDelta / 2) ** 2;
    return 6371 * 2 * Math.atan2(Math.sqrt(arc), Math.sqrt(1 - arc));
}

function createSearchMarkerIcon(type) {
    const icons = { donor: 'fa-user', bloodBank: 'fa-droplet', hospital: 'fa-hospital' };
    return L.divIcon({
        className: 'search-marker-wrapper',
        html: `<span class="search-marker search-marker-${type}"><i class="fas ${icons[type]}"></i></span>`,
        iconSize: [36, 36],
        iconAnchor: [18, 18],
        popupAnchor: [0, -18]
    });
}

function addSearchMarker(location, type, popup) {
    const coordinates = coordinatesFor(location);
    if (!coordinates || !map || !window.L) return;
    const marker = L.marker([coordinates.latitude, coordinates.longitude], {
        icon: createSearchMarkerIcon(type)
    }).bindPopup(popup).addTo(map);
    markers.push(marker);
}

function renderEmptyResult(element, message) {
    if (!element) return;
    const empty = document.createElement('div');
    empty.className = 'no-results';
    empty.textContent = message;
    element.replaceChildren(empty);
}

function renderFacilityCard(element, facility, type, bloodGroup, distance) {
    if (!element) return;
    const card = document.createElement('article');
    card.className = 'facility-card';
    const typeLabel = type === 'bloodBank' ? 'Blood Bank' : 'Hospital';
    const heading = document.createElement('h3');
    heading.textContent = facility.name || typeLabel;
    const badge = document.createElement('span');
    badge.className = `facility-type facility-type-${type}`;
    badge.textContent = typeLabel;
    const group = document.createElement('p');
    group.innerHTML = `<strong>Blood group:</strong> <span class="donor-badge badge-blood">${escapeHtml(bloodGroup)}</span>`;
    const units = document.createElement('p');
    units.innerHTML = `<strong>Available units:</strong> ${escapeHtml(facility.units)}`;
    const address = document.createElement('p');
    address.innerHTML = `<strong>Address:</strong> ${escapeHtml([facility.address, facility.city].filter(Boolean).join(', ') || 'Not provided')}`;
    const distanceRow = document.createElement('p');
    distanceRow.innerHTML = `<strong>Distance:</strong> ${distance === null ? 'Unavailable' : `${distance.toFixed(2)} km`}`;
    card.append(heading, badge, group, units, address, distanceRow);
    if (facility.is_demo) {
        const demo = document.createElement('p');
        demo.className = 'facility-demo-note';
        demo.textContent = 'Demo inventory; not live availability.';
        card.appendChild(demo);
    }
    element.appendChild(card);

    const popup = `<b>${escapeHtml(facility.name || typeLabel)}</b><br>` +
        `Type: ${typeLabel}<br>Blood group: ${escapeHtml(bloodGroup)}<br>` +
        `Available units: ${escapeHtml(facility.units)}<br>` +
        `Address: ${escapeHtml([facility.address, facility.city].filter(Boolean).join(', ') || 'Not provided')}<br>` +
        `Distance: ${distance === null ? 'Unavailable' : `${distance.toFixed(2)} km`}`;
    addSearchMarker(facility, type, popup);
}

function displayFacilityResults(banks, hospitals, bloodGroup, userLat, userLng, radius) {
    const banksList = document.getElementById('blood-banks-list');
    const hospitalsList = document.getElementById('hospitals-list');
    if (banksList) banksList.replaceChildren();
    if (hospitalsList) hospitalsList.replaceChildren();

    if (banks === null) {
        renderEmptyResult(banksList, 'Blood-bank results could not be loaded.');
    } else {
        const matches = banks.flatMap(bank => {
            const inventory = (bank.inventory || []).find(item =>
                item.blood_group === bloodGroup && Number(item.units) > 0
            );
            if (!inventory) return [];
            const coordinates = coordinatesFor(bank);
            const distance = coordinates
                ? distanceBetween(userLat, userLng, coordinates.latitude, coordinates.longitude)
                : null;
            if (distance !== null && distance > radius) return [];
            return [{
                ...bank,
                units: Number(inventory.units),
                is_demo: Boolean(bank.is_demo || inventory.is_demo),
                distance
            }];
        });
        if (matches.length === 0) {
            renderEmptyResult(banksList, 'No matching blood available at nearby blood banks.');
        } else {
            matches.forEach(bank => renderFacilityCard(
                banksList, bank, 'bloodBank', bloodGroup, bank.distance
            ));
        }
    }

    if (hospitals === null) {
        renderEmptyResult(hospitalsList, 'Hospital results could not be loaded.');
    } else {
        renderEmptyResult(hospitalsList, 'No matching blood available at nearby hospitals.');
    }

    const locatedMarkers = markers.filter(marker => map?.hasLayer(marker));
    if (locatedMarkers.length && map) {
        const bounds = L.featureGroup(locatedMarkers).getBounds();
        if (bounds.isValid()) map.fitBounds(bounds, { padding: [28, 28], maxZoom: 13 });
    }
}

function displayDonors(donors) {
    const donorsList = document.getElementById('donors-list');
    if (!donorsList) return;

    markers.forEach(marker => map?.removeLayer(marker));
    markers = [];
    donorsList.replaceChildren();

    if (!Array.isArray(donors) || donors.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'no-results';
        const heading = document.createElement('p');
        heading.textContent = 'No matching blood available at nearby donors.';
        const explanation = document.createElement('small');
        explanation.textContent = 'Donors appear after confirming they meet the age and donation waiting-period requirements.';
        empty.append(heading, explanation);
        donorsList.appendChild(empty);
        return;
    }

    donors.forEach((donor, index) => {
        const backendRank = Number(donor.rank);
        const rank = Number.isInteger(backendRank) && backendRank > 0 ? backendRank : index + 1;
        const score = formatRankValue(donor.ai_score, 2);
        const reliability = formatRankValue(donor.reliability_score);
        const distance = formatRankValue(donor.distance_km, 2);
        const rankClass = rank === 1 ? ' ranking-first' : '';
        const urgencyClass = rank === 1 ? 'high' : rank <= 3 ? 'medium' : 'low';

        const card = document.createElement('article');
        card.className = 'donor-card ' + urgencyClass + rankClass;

        const ranking = document.createElement('div');
        ranking.className = 'donor-ranking';
        const rankLabel = document.createElement('span');
        rankLabel.className = 'donor-rank-label';
        rankLabel.textContent = 'Rank #' + rank;
        ranking.appendChild(rankLabel);
        if (rank === 1) {
            const topMatch = document.createElement('span');
            topMatch.className = 'donor-top-match';
            topMatch.textContent = 'Top ranked match';
            ranking.appendChild(topMatch);
        }

        const heading = document.createElement('h3');
        heading.textContent = donor.name || 'Donor';

        const scoreGrid = document.createElement('div');
        scoreGrid.className = 'donor-score-grid';
        [
            ['Match Score', score],
            ['Reliability', reliability === 'N/A' ? 'N/A' : reliability + '/100'],
            ['Distance', distance === 'N/A' ? 'N/A' : distance + ' km']
        ].forEach(([label, value]) => {
            const metric = document.createElement('div');
            metric.className = 'donor-score-metric';
            const metricLabel = document.createElement('span');
            metricLabel.textContent = label;
            const metricValue = document.createElement('strong');
            metricValue.textContent = value;
            metric.append(metricLabel, metricValue);
            scoreGrid.appendChild(metric);
        });

        const info = document.createElement('div');
        info.className = 'donor-info';
        const addInfo = (label, value) => {
            const row = document.createElement('p');
            const title = document.createElement('strong');
            title.textContent = label + ': ';
            row.append(title, document.createTextNode(value));
            info.appendChild(row);
        };
        const blood = document.createElement('p');
        const bloodBadge = document.createElement('span');
        bloodBadge.className = 'donor-badge badge-blood';
        bloodBadge.textContent = donor.blood_group || 'N/A';
        blood.append(bloodBadge);
        info.appendChild(blood);
        addInfo('City', donor.city || 'N/A');
        addInfo('Age', formatRankValue(donor.age));
        const status = document.createElement('p');
        const statusLabel = document.createElement('strong');
        statusLabel.textContent = 'Status: ';
        const availability = document.createElement('span');
        availability.className = 'donor-badge badge-available';
        availability.textContent = 'Available';
        const eligibility = document.createElement('span');
        eligibility.className = 'donor-badge badge-available';
        eligibility.textContent = 'Eligible to Donate';
        status.append(statusLabel, availability, document.createTextNode(' '), eligibility);
        info.appendChild(status);
        addInfo('Donations', formatRankValue(donor.donation_count));
        const verified = document.createElement('p');
        verified.textContent = donor.is_verified ? '✓ Verified Donor' : 'Not verified';
        info.appendChild(verified);

        const buttons = document.createElement('div');
        buttons.className = 'donor-buttons';
        const email = document.createElement('a');
        email.className = 'btn btn-secondary';
        email.href = 'mailto:' + (donor.email || '');
        email.textContent = 'Email';
        buttons.appendChild(email);

        card.append(ranking, heading, scoreGrid, info, buttons);
        donorsList.appendChild(card);

        const latitude = Number(donor.latitude);
        const longitude = Number(donor.longitude);
        if (donor.latitude !== null && donor.latitude !== undefined &&
            donor.longitude !== null && donor.longitude !== undefined &&
            Number.isFinite(latitude) && Number.isFinite(longitude) && map && window.L) {
            const popup = '<b>' + escapeHtml(donor.name || 'Donor') + '</b><br>' +
                'Type: Donor<br>' +
                'Rank: #' + rank + '<br>' +
                'Blood group: ' + escapeHtml(donor.blood_group || 'N/A') + '<br>' +
                'Address: ' + escapeHtml([donor.address, donor.city].filter(Boolean).join(', ') || 'Not provided') + '<br>' +
                'Distance: ' + (distance === 'N/A' ? 'N/A' : distance + ' km');
            addSearchMarker(donor, 'donor', popup);
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
