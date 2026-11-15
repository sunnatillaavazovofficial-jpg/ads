(function () {
  'use strict';
  const form = document.getElementById('job-form');
  if (!form) return;
  const tbody = document.getElementById('items');
  const tpl = document.getElementById('row-tpl');
  const prices = {};
  (window.DN_PRICES || []).forEach(p => { prices[p.name.toLowerCase()] = p; });
  const W = document.getElementById('width');
  const H = document.getElementById('height');
  const U = document.getElementById('size_unit');
  const areaLabel = document.getElementById('area-label');

  function area() {
    const w = DN.parse(W.value), h = DN.parse(H.value);
    if (!w || !h) return 0;
    return Math.round(w * h / (U.value === 'sm' ? 10000 : 1) * 1000) / 1000;
  }

  function recalc() {
    const a = area();
    areaLabel.textContent = a ? 'Maydon: ' + DN.num(a) + ' m²' : '';
    let sub = 0;
    tbody.querySelectorAll('tr').forEach(tr => {
      const q = DN.parse(tr.querySelector('[name=item_qty]').value);
      const p = DN.parse(tr.querySelector('[name=item_price]').value);
      const s = q * p;
      sub += s;
      tr.querySelector('.sum').textContent = DN.num(s);
    });
    const disc = DN.parse(document.getElementById('discount').value);
    const paid = DN.parse(document.getElementById('paid').value);
    const total = Math.max(sub - disc, 0);
    document.getElementById('t-sub').textContent = DN.num(sub) + ' ' + DN_CURRENCY;
    document.getElementById('t-total').textContent = DN.num(total) + ' ' + DN_CURRENCY;
    document.getElementById('t-debt').textContent = DN.num(total - paid) + ' ' + DN_CURRENCY;
  }

  function addRow(focus) {
    const tr = tpl.content.firstElementChild.cloneNode(true);
    tbody.appendChild(tr);
    if (focus) tr.querySelector('input').focus();
    recalc();
    return tr;
  }

  function setUnit(sel, unit) {
    if (![...sel.options].some(o => o.value === unit)) {
      const o = document.createElement('option');
      o.value = o.textContent = unit;
      sel.appendChild(o);
    }
    sel.value = unit;
  }

  tbody.addEventListener('input', e => {
    const tr = e.target.closest('tr');
    if (e.target.name === 'item_name') {
      const p = prices[e.target.value.trim().toLowerCase()];
      if (p) {
        setUnit(tr.querySelector('[name=item_unit]'), p.unit);
        tr.querySelector('[name=item_price]').value = p.price;
        if (p.unit === 'm²' && area()) tr.querySelector('[name=item_qty]').value = area();
      }
    }
    if (e.target.name === 'item_unit' && e.target.value === 'm²' && area()) {
      tr.querySelector('[name=item_qty]').value = area();
    }
    recalc();
  });
  tbody.addEventListener('change', e => {
    if (e.target.name === 'item_unit') {
      const tr = e.target.closest('tr');
      if (e.target.value === 'm²' && area()) tr.querySelector('[name=item_qty]').value = area();
      recalc();
    }
  });
  tbody.addEventListener('click', e => {
    const b = e.target.closest('[data-del]');
    if (b) { b.closest('tr').remove(); recalc(); }
  });
  document.getElementById('add-row').addEventListener('click', () => addRow(true));

  // o'lcham o'zgarsa m² qatorlarini yangilash
  [W, H, U].forEach(el => el.addEventListener('input', () => {
    const a = area();
    if (a) tbody.querySelectorAll('tr').forEach(tr => {
      if (tr.querySelector('[name=item_unit]').value === 'm²') tr.querySelector('[name=item_qty]').value = a;
    });
    recalc();
  }));
  ['discount', 'paid'].forEach(id => document.getElementById(id).addEventListener('input', recalc));

  if (!tbody.children.length) addRow(false);
  recalc();
  if (location.hash === '#items') {
    tbody.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  // yuborishda tugmani bloklash (katta fayllar yuklanayotganda ikki marta bosilmasin)
  form.addEventListener('submit', () => {
    const b = document.getElementById('save-btn');
    b.disabled = true;
    b.textContent = 'Saqlanmoqda...';
  });
})();
