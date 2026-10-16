(() => {
    const bankSelect = document.getElementById('inventory-bank');
    const rows = document.getElementById('inventory-rows');
    const modal = document.getElementById('inventory-modal');
    const form = document.getElementById('inventory-form');
    let current = [];
    let editing = null;
    const msg = (text, error = false) => { const node = document.getElementById('inventory-message'); node.textContent = text; node.classList.toggle('message-error', error); node.classList.toggle('message-success', !error); };
    async function api(url, options = {}) { const response = await fetch(url, { ...options, headers: { ...(options.body ? {'Content-Type': 'application/json'} : {}), ...(options.headers || {}) }}); const data = await response.json().catch(() => ({})); if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`); return data; }
    function draw() {
        rows.replaceChildren(); document.getElementById('inventory-total').textContent = `${current.length} records`;
        if (!current.length) { const tr = document.createElement('tr'), td = document.createElement('td'); td.colSpan = 4; td.className = 'table-empty'; td.textContent = 'No stock records for this bank. Add records for the blood groups it tracks.'; tr.append(td); rows.append(tr); }
        current.forEach(item => { const tr = document.createElement('tr'); [item.blood_group, item.units, item.is_demo ? 'Demo/seed' : 'Managed'].forEach(value => { const td = document.createElement('td'); td.textContent = value; tr.append(td); }); const td = document.createElement('td'); [['Edit', () => open(item)], ['Delete', () => remove(item)]].forEach(([name, action]) => { const button = document.createElement('button'); button.className = `btn ${name === 'Delete' ? 'btn-danger' : 'btn-secondary'}`; button.textContent = name; button.addEventListener('click', action); td.append(button); }); tr.append(td); rows.append(tr); });
        const stock = document.getElementById('inventory-stock'); stock.replaceChildren(...['A+','A-','B+','B-','AB+','AB-','O+','O-'].map(group => { const item = current.find(record => record.blood_group === group); const chip = document.createElement('div'); chip.className = 'inventory-stock-item'; const name = document.createElement('strong'); name.textContent = group; const value = document.createElement('span'); value.textContent = item ? `${item.units} units` : 'Not recorded'; chip.append(name, value); return chip; }));
    }
    async function load() { if (!bankSelect.value) { current = []; draw(); return; } rows.innerHTML = '<tr><td colspan="4" class="table-empty">Loading stock…</td></tr>'; try { const result = await api(`/api/admin/blood-banks/${bankSelect.value}/inventory`); current = result.inventory || []; draw(); } catch (error) { msg(error.message, true); } }
    function open(item = null) { editing = item?.id ?? null; form.reset(); document.getElementById('inventory-modal-title').textContent = item ? 'Edit inventory record' : 'Add inventory record'; if (item) { form.elements.blood_group.value = item.blood_group; form.elements.blood_group.disabled = true; form.elements.units.value = item.units; form.elements.is_demo.checked = item.is_demo; } else { form.elements.blood_group.disabled = false; form.elements.is_demo.checked = bankSelect.selectedOptions[0]?.dataset.demo === 'true'; } document.getElementById('inventory-form-error').textContent = ''; modal.style.display = 'flex'; }
    async function remove(item) { if (!window.confirm(`Delete ${item.blood_group} inventory record?`)) return; try { await api(`/api/admin/inventory/${item.id}`, { method: 'DELETE' }); msg('Inventory record deleted.'); await load(); } catch (error) { msg(error.message, true); } }
    bankSelect.addEventListener('change', load); document.getElementById('inventory-add').addEventListener('click', () => open());
    document.querySelectorAll('[data-inventory-close]').forEach(button => button.addEventListener('click', () => { modal.style.display = 'none'; }));
    modal.addEventListener('click', event => { if (event.target === modal) modal.style.display = 'none'; });
    form.addEventListener('submit', async event => { event.preventDefault(); const payload = { blood_group: form.elements.blood_group.value, units: Number(form.elements.units.value), is_demo: form.elements.is_demo.checked }; try { const url = editing ? `/api/admin/inventory/${editing}` : `/api/admin/blood-banks/${bankSelect.value}/inventory`; await api(url, { method: editing ? 'PUT' : 'POST', body: JSON.stringify(payload) }); modal.style.display = 'none'; msg('Inventory saved.'); await load(); } catch (error) { document.getElementById('inventory-form-error').textContent = error.message; } });
    if (bankSelect.value) load();
})();
