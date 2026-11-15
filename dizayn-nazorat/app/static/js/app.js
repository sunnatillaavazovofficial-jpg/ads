(function () {
  'use strict';

  // ---------- mobil menyu ----------
  const sb = document.getElementById('sidebar');
  const bd = document.getElementById('backdrop');
  const mb = document.getElementById('menu-btn');
  function toggle(open) { sb && sb.classList.toggle('open', open); bd && bd.classList.toggle('open', open); }
  mb && mb.addEventListener('click', () => toggle(!sb.classList.contains('open')));
  bd && bd.addEventListener('click', () => toggle(false));

  // ---------- yordamchilar ----------
  window.DN = window.DN || {};
  DN.toast = function (msg, type) {
    const t = document.createElement('div');
    t.className = 'toast' + (type === 'error' ? ' error' : '');
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3500);
  };
  DN.esc = function (s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  };
  DN.num = function (v) {
    v = Math.round((Number(v) || 0) * 100) / 100;
    const [i, d] = String(Math.abs(v)).split('.');
    return (v < 0 ? '-' : '') + i.replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + (d ? ',' + d : '');
  };
  DN.parse = function (v) {
    const n = parseFloat(String(v || '').replace(/\s/g, '').replace(',', '.'));
    return isNaN(n) ? 0 : n;
  };
  DN.lightbox = function (src) {
    const lb = document.createElement('div');
    lb.className = 'lightbox';
    lb.innerHTML = '<img src="' + DN.esc(src) + '">';
    lb.addEventListener('click', () => lb.remove());
    document.addEventListener('keydown', function h(e) { if (e.key === 'Escape') { lb.remove(); document.removeEventListener('keydown', h); } });
    document.body.appendChild(lb);
  };

  document.addEventListener('click', e => {
    const a = e.target.closest('[data-lightbox]');
    if (a) { e.preventDefault(); DN.lightbox(a.getAttribute('href')); }
  });

  // ---------- fayl tashlash (dropzone) ----------
  function fileChip(f) {
    const chip = document.createElement('span');
    chip.className = 'chip';
    if (/^image\/(png|jpe?g|gif|webp|bmp|svg\+xml|avif)$/.test(f.type) && f.size < 15 * 1024 * 1024) {
      const img = document.createElement('img');
      img.src = URL.createObjectURL(f);
      chip.appendChild(img);
    } else {
      const ext = document.createElement('span');
      ext.className = 'ext';
      ext.textContent = (f.name.split('.').pop() || 'FAYL').slice(0, 4).toUpperCase();
      chip.appendChild(ext);
    }
    const nm = document.createElement('span');
    nm.textContent = f.name;
    chip.appendChild(nm);
    return chip;
  }
  document.querySelectorAll('[data-drop]').forEach(zone => {
    const input = zone.querySelector('input[type=file]');
    const list = zone.querySelector('.drop-list');
    let files = new DataTransfer();
    function render() {
      list.innerHTML = '';
      [...input.files].forEach(f => list.appendChild(fileChip(f)));
    }
    input.addEventListener('change', () => {
      // tanlangan fayllarni oldingilariga qo'shib boramiz
      [...input.files].forEach(f => files.items.add(f));
      input.files = files.files;
      render();
    });
    ['dragenter', 'dragover'].forEach(ev => zone.addEventListener(ev, e => { e.preventDefault(); zone.classList.add('over'); }));
    ['dragleave', 'drop'].forEach(ev => zone.addEventListener(ev, e => { e.preventDefault(); zone.classList.remove('over'); }));
    zone.addEventListener('drop', e => {
      [...e.dataTransfer.files].forEach(f => files.items.add(f));
      input.files = files.files;
      render();
    });
  });

  // ---------- o'qilmagan Telegram xabarlar soni (menyuda) ----------
  const navBadge = document.getElementById('nav-unread');
  async function pollUnread() {
    if (!navBadge || document.hidden) return;
    try {
      const r = await fetch('/api/inbox/chats', { headers: { Accept: 'application/json' } });
      if (!r.ok) return;
      const d = await r.json();
      const n = d.chats.reduce((s, c) => s + (c.unread || 0), 0);
      navBadge.textContent = n > 99 ? '99+' : n;
      navBadge.classList.toggle('hidden', !n);
    } catch (e) { /* tarmoq xatosi */ }
  }
  if (window.DN_POLL_UNREAD && navBadge && !document.getElementById('inbox')) {
    pollUnread();
    setInterval(pollUnread, 20000);
  }
})();
