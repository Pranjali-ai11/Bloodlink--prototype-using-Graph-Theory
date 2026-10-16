(() => {
    const kind = window.BLOODLINK_FACILITY_TYPE;
    const label = kind === 'hospitals' ? 'hospital' : 'blood bank';
    const collectionKey = kind === 'blood-banks' ? 'blood_banks' : kind;
    const endpoint = `/api/admin/${kind}`;
    const rows = document.getElementById('facility-rows');
    const modal = document.getElementById('facility-modal');
    const detailModal = document.getElementById('facility-detail-modal');
    const deleteModal = document.getElementById('facility-delete-modal');
    const form = document.getElementById('facility-form');
    let facilities = [];
    let editingId = null;
    let deletingId = null;

    const message = (text, error = false) => {
        const node = document.getElementById('facility-message');
        node.textContent = text;
        node.classList.toggle('message-error', error);
        node.classList.toggle('message-success', !error);
    };
    const showModal = node => { node.style.display = 'flex'; };
    const hideModal = node => { node.style.display = 'none'; };
    const cell = value => { const td = document.createElement('td'); td.textContent = value || '—'; return td; };

    async function api(url, options = {}) {
        const response = await fetch(url, { ...options, headers: { ...(options.body ? {'Content-Type': 'application/json'} : {}), ...(options.headers || {}) }});
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
        return data;
    }

    async function load() {
        rows.innerHTML = '<tr><td colspan="7" class="table-empty">Loading facilities…</td></tr>';
        try {
            const data = await api(endpoint);
            if (!Array.isArray(data[collectionKey])) {
                throw new Error(`Invalid response from ${endpoint}: expected a ${collectionKey} list.`);
            }
            facilities = data[collectionKey];
            render();
            document.getElementById('facility-count').textContent = facilities.length;
        } catch (error) {
            document.getElementById('facility-count').textContent = '—';
            rows.innerHTML = '';
            const tr = document.createElement('tr'); const td = cell(error.message); td.colSpan = 7; td.className = 'table-empty'; tr.append(td); rows.append(tr);
            message(error.message, true);
        }
    }

    function render() {
        const query = document.getElementById('facility-search').value.trim().toLocaleLowerCase();
        const filtered = facilities.filter(item => [item.name, item.city, item.address, item.phone].some(value => (value || '').toLocaleLowerCase().includes(query)));
        if (!filtered.length) { rows.innerHTML = `<tr><td colspan="7" class="table-empty">${query ? 'No facilities match this search.' : `No ${label}s have been added yet.`}</td></tr>`; return; }
        rows.replaceChildren(...filtered.map(item => {
            const tr = document.createElement('tr');
            tr.append(cell(item.name), cell(item.city), cell(item.address), cell(item.phone), cell(item.latitude == null ? '' : `${item.latitude}, ${item.longitude}`));
            const type = cell(''); const badge = document.createElement('span'); badge.className = `status-pill ${item.is_demo ? 'status-pending' : 'status-available'}`; badge.textContent = item.is_demo ? 'Demo' : 'Managed'; type.append(badge); tr.append(type);
            const actions = cell(''); actions.className = 'facility-actions';
            [['View', () => view(item.id)], ['Edit', () => edit(item)], ['Delete', () => confirmDelete(item)]].forEach(([text, callback]) => { const button = document.createElement('button'); button.type = 'button'; button.className = `btn ${text === 'Delete' ? 'btn-danger' : 'btn-secondary'}`; button.textContent = text; button.addEventListener('click', callback); actions.append(button); });
            tr.append(actions); return tr;
        }));
    }

    function edit(item = null) {
        editingId = item?.id ?? null;
        document.getElementById('facility-modal-title').textContent = `${item ? 'Edit' : 'Add'} ${label}`;
        form.reset();
        if (item) for (const key of ['name', 'address', 'city', 'phone', 'latitude', 'longitude', 'is_demo']) form.elements[key].type === 'checkbox' ? form.elements[key].checked = item[key] : form.elements[key].value = item[key] ?? '';
        document.getElementById('facility-form-error').textContent = '';
        showModal(modal);
    }

    async function view(id) {
        try {
            const data = await api(`${endpoint}/${id}`); const item = data[kind === 'hospitals' ? 'hospital' : 'blood_bank'];
            document.getElementById('facility-detail-title').textContent = item.name;
            const target = document.getElementById('facility-detail-content'); target.replaceChildren();
            [['Address', item.address], ['City', item.city], ['Phone', item.phone], ['Latitude', item.latitude], ['Longitude', item.longitude], ['Record', item.is_demo ? 'Demo/seed' : 'Managed']].forEach(([key, value]) => { const p = document.createElement('p'); const strong = document.createElement('strong'); strong.textContent = `${key}: `; p.append(strong, document.createTextNode(value ?? 'Not provided')); target.append(p); });
            showModal(detailModal);
        } catch (error) { message(error.message, true); }
    }

    function confirmDelete(item) { deletingId = item.id; document.getElementById('facility-delete-copy').textContent = `Delete ${item.name}? This cannot be undone.`; showModal(deleteModal); }

    document.getElementById('add-facility').addEventListener('click', () => edit());
    document.getElementById('facility-refresh').addEventListener('click', load);
    document.getElementById('facility-search').addEventListener('input', render);
    document.querySelectorAll('[data-modal-close]').forEach(button => button.addEventListener('click', () => hideModal(modal)));
    document.querySelector('[data-detail-close]').addEventListener('click', () => hideModal(detailModal));
    document.querySelector('[data-delete-cancel]').addEventListener('click', () => hideModal(deleteModal));
    [modal, detailModal, deleteModal].forEach(node => node.addEventListener('click', event => { if (event.target === node) hideModal(node); }));
    form.addEventListener('submit', async event => {
        event.preventDefault();
        const fields = new FormData(form); const payload = Object.fromEntries(fields.entries());
        payload.is_demo = form.elements.is_demo.checked;
        for (const key of ['latitude', 'longitude']) payload[key] = payload[key] === '' ? null : Number(payload[key]);
        try {
            await api(editingId ? `${endpoint}/${editingId}` : endpoint, { method: editingId ? 'PUT' : 'POST', body: JSON.stringify(payload) });
            hideModal(modal); message(`${label[0].toUpperCase()}${label.slice(1)} saved.`); await load();
        } catch (error) { document.getElementById('facility-form-error').textContent = error.message; }
    });
    document.getElementById('facility-delete-confirm').addEventListener('click', async () => {
        try { await api(`${endpoint}/${deletingId}`, { method: 'DELETE' }); hideModal(deleteModal); message(`${label[0].toUpperCase()}${label.slice(1)} deleted.`); await load(); }
        catch (error) { message(error.message, true); }
    });
    load();
})();
