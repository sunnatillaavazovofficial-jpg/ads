(function () {
  'use strict';
  const root = document.getElementById('inbox');
  if (!root) return;
  const $ = id => document.getElementById(id);
  const listEl = $('chat-list');
  const msgsEl = $('msgs');
  const textEl = $('msg-text');
  const fileEl = $('file-input');
  const attEl = $('att');
  const COLORS = ['#6366f1', '#ec4899', '#14b8a6', '#f59e0b', '#3b82f6', '#8b5cf6', '#ef4444', '#22c55e', '#0ea5e9', '#f97316'];

  let chats = [];
  let active = null;      // ochiq chat obyekti
  let lastId = 0;         // ochiq chatdagi oxirgi xabar (baza id)
  let lastDate = 0;       // ko'rsatilgan eng yangi xabar vaqti (ms)
  let firstId = 0;        // eng eski yuklangan xabar
  let accFilter = '';
  let search = '';
  let loadingOlder = false;
  let noMoreOlder = false;
  let attachMsgId = null;

  const fmtTime = iso => new Date(iso).toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit' });
  function fmtShort(iso) {
    if (!iso) return '';
    const d = new Date(iso), now = new Date();
    if (d.toDateString() === now.toDateString()) return fmtTime(iso);
    const diff = (now - d) / 86400000;
    if (diff < 6) return d.toLocaleDateString('uz-UZ', { weekday: 'short' });
    return d.toLocaleDateString('uz-UZ', { day: '2-digit', month: '2-digit', year: '2-digit' });
  }
  const dayKey = iso => new Date(iso).toDateString();
  const dayLabel = iso => {
    const d = new Date(iso), now = new Date();
    if (d.toDateString() === now.toDateString()) return 'Bugun';
    const y = new Date(now); y.setDate(now.getDate() - 1);
    if (d.toDateString() === y.toDateString()) return 'Kecha';
    return d.toLocaleDateString('uz-UZ', { day: 'numeric', month: 'long', year: 'numeric' });
  };
  const initials = t => (t || '?').split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0]).join('').toUpperCase() || '?';
  const sizeFmt = n => !n ? '' : n < 1048576 ? (n / 1024).toFixed(0) + ' KB' : (n / 1048576).toFixed(1) + ' MB';

  async function api(url, opts) {
    const r = await fetch(url, Object.assign({ headers: { Accept: 'application/json' } }, opts || {}));
    let d = {};
    try { d = await r.json(); } catch (e) { /* bo'sh javob */ }
    if (!r.ok) throw new Error(d.error || ('Xato ' + r.status));
    return d;
  }

  // ---------------- chatlar ro'yxati ----------------
  async function loadChats() {
    try {
      const d = await api('/api/inbox/chats');
      chats = d.chats;
      renderChats();
      const nb = document.getElementById('nav-unread');
      if (nb) {
        const n = chats.reduce((s, c) => s + (c.unread || 0), 0);
        nb.textContent = n > 99 ? '99+' : n; nb.classList.toggle('hidden', !n);
      }
    } catch (e) {
      listEl.innerHTML = '<div class="empty small">Chatlarni yuklab bo\'lmadi: ' + DN.esc(e.message) + '</div>';
    }
  }

  function renderChats() {
    const term = search.toLowerCase();
    const items = chats.filter(c => {
      if (accFilter === 'unread' && !c.unread) return false;
      if (accFilter && accFilter !== 'unread' && String(c.account && c.account.id) !== accFilter) return false;
      if (term && !((c.title || '') + ' ' + (c.username || '') + ' ' + (c.phone || '') + ' ' + (c.last_text || '')).toLowerCase().includes(term)) return false;
      return true;
    });
    if (!items.length) {
      listEl.innerHTML = '<div class="empty small">' + (chats.length ? 'Hech narsa topilmadi' : 'Saralangan chatlar yo\'q. Akkaunt sahifasidan chatlarni tanlang.') + '</div>';
      return;
    }
    listEl.innerHTML = items.map(c => {
      const acc = c.account || {};
      return '<div class="chat-item' + (active && active.id === c.id ? ' active' : '') + '" data-id="' + c.id + '">' +
        '<div class="av" style="background:' + COLORS[c.id % 10] + '">' + DN.esc(initials(c.title)) +
        '<span class="acc-dot" style="background:' + DN.esc(acc.color || '#999') + '" title="' + DN.esc(acc.name || '') + '"></span></div>' +
        '<div class="mid"><div class="top"><b>' + DN.esc(c.title) + '</b><time>' + fmtShort(c.last_at) + '</time></div>' +
        '<div class="bot"><span class="acc-name" style="background:' + DN.esc(acc.color || '#999') + '">' + DN.esc(acc.name || '') + '</span>' +
        '<span class="prev">' + DN.esc(c.last_text || '') + '</span>' +
        (c.unread ? '<span class="unread">' + c.unread + '</span>' : '') + '</div></div></div>';
    }).join('');
  }

  listEl.addEventListener('click', e => {
    const it = e.target.closest('.chat-item');
    if (it) openChat(Number(it.dataset.id));
  });
  $('chat-search').addEventListener('input', e => { search = e.target.value; renderChats(); });
  $('acc-filter').addEventListener('click', e => {
    const b = e.target.closest('button');
    if (!b) return;
    accFilter = b.dataset.acc;
    $('acc-filter').querySelectorAll('button').forEach(x => x.classList.toggle('active', x === b));
    renderChats();
  });

  // ---------------- suhbat ----------------
  async function openChat(id) {
    const c = chats.find(x => x.id === id) || { id: id, title: '...' };
    active = c;
    lastId = 0; firstId = 0; lastDate = 0; noMoreOlder = false;
    msgsEl.dataset.lastDay = ''; msgsEl.dataset.lastSender = '';
    root.classList.add('has-chat');
    $('conv-empty').classList.add('hidden');
    ['conv-h', 'msgs', 'composer'].forEach(x => $(x).classList.remove('hidden'));
    setHeader(c);
    msgsEl.innerHTML = '<div class="empty small">Yuklanmoqda...</div>';
    history.replaceState(null, '', '/inbox?chat=' + id);
    renderChats();
    try {
      const d = await api('/api/inbox/chats/' + id + '/messages');
      if (!active || active.id !== id) return;
      active = d.chat;
      setHeader(d.chat);
      msgsEl.innerHTML = '';
      appendMessages(d.messages, true);
      const local = chats.find(x => x.id === id);
      if (local) { local.unread = 0; renderChats(); }
      if (!d.messages.length) loadOlder();
    } catch (e) {
      msgsEl.innerHTML = '<div class="empty small">' + DN.esc(e.message) + '</div>';
    }
    textEl.focus();
  }

  function setHeader(c) {
    $('conv-title').textContent = c.title;
    const acc = c.account || {};
    const bits = [];
    if (c.username) bits.push('@' + c.username);
    if (c.phone) bits.push('+' + String(c.phone).replace(/^\+/, ''));
    bits.push({ user: 'Shaxsiy', group: 'Guruh', channel: 'Kanal', bot: 'Bot' }[c.kind] || '');
    if (acc.name) bits.push('akkaunt: ' + acc.name);
    $('conv-sub').textContent = bits.filter(Boolean).join(' · ');
    const contact = c.username ? '@' + c.username : (c.phone ? '+' + String(c.phone).replace(/^\+/, '') : '');
    $('new-job-btn').href = '/jobs/new?' + new URLSearchParams({ client_name: c.kind === 'user' ? c.title : '', client_contact: contact, tg_chat: c.id }).toString();
  }

  function mediaHtml(m) {
    const src = '/inbox/media/' + m.id;
    switch (m.media_type) {
      case 'photo':
        return '<img class="media" loading="lazy" src="' + src + '" data-full="' + src + '" alt="" onerror="this.outerHTML=\'<div class=&quot;small muted&quot;>🖼 Rasm (yuklab boʻlmadi)</div>\'">';
      case 'video':
        return '<video controls preload="none" src="' + src + '"></video>';
      case 'gif':
        return '<video autoplay muted loop playsinline src="' + src + '"></video>';
      case 'video_note':
        return '<video controls preload="none" src="' + src + '" style="max-width:240px;border-radius:50%"></video>';
      case 'voice':
      case 'audio':
        return '<audio controls preload="none" src="' + src + '"></audio>' + (m.media_name ? '<div class="small muted">' + DN.esc(m.media_name) + '</div>' : '');
      case 'document': {
        const name = m.media_name || 'fayl';
        const ext = (name.split('.').pop() || 'FAYL').slice(0, 4).toUpperCase();
        return '<a class="doc" href="' + src + '?download=1"><span class="ext">' + DN.esc(ext) + '</span><span><b>' + DN.esc(name) + '</b><br><span class="small muted">' + sizeFmt(m.media_size) + ' · yuklab olish</span></span></a>';
      }
      case 'sticker':
      case 'geo':
      case 'contact':
      case 'poll':
        return '';
      default:
        return m.media_label ? '<div class="small muted">' + DN.esc(m.media_label) + '</div>' : '';
    }
  }

  function linkify(s) {
    return DN.esc(s).replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
  }

  function msgHtml(m, showSender) {
    const canAttach = ['photo', 'document', 'video', 'audio', 'voice', 'gif'].includes(m.media_type);
    return '<div class="msg' + (m.out ? ' out' : '') + '" data-id="' + m.id + '">' +
      (showSender && m.sender ? '<div class="sn">' + DN.esc(m.sender) + '</div>' : '') +
      mediaHtml(m) +
      (m.text ? '<div class="tx">' + linkify(m.text) + '</div>' : '') +
      '<div class="tm">' + fmtTime(m.date) + '</div>' +
      (canAttach ? '<div class="m-acts"><button class="btn sm icon" data-attach="' + m.id + '" title="Ishga biriktirish">📎</button></div>' : '') +
      '</div>';
  }

  function appendMessages(list, scroll) {
    if (!list.length) return;
    const nearBottom = msgsEl.scrollHeight - msgsEl.scrollTop - msgsEl.clientHeight < 120;
    const lastEl = msgsEl.querySelector('.msg:last-of-type');
    let prevDay = msgsEl.dataset.lastDay || '';
    let prevSender = msgsEl.dataset.lastSender || '';
    const isGroup = active && active.kind !== 'user' && active.kind !== 'bot';
    let html = '';
    list.forEach(m => {
      if (msgsEl.querySelector('.msg[data-id="' + m.id + '"]')) return;
      const dk = dayKey(m.date);
      if (dk !== prevDay) { html += '<div class="day-sep">' + dayLabel(m.date) + '</div>'; prevDay = dk; prevSender = ''; }
      const sKey = (m.out ? 'out' : 'in') + ':' + m.sender;
      html += msgHtml(m, isGroup && !m.out && sKey !== prevSender);
      prevSender = sKey;
      lastId = Math.max(lastId, m.id);
      lastDate = Math.max(lastDate, new Date(m.date).getTime());
      if (!firstId || m.id < firstId) firstId = m.id;
    });
    msgsEl.dataset.lastDay = prevDay;
    msgsEl.dataset.lastSender = prevSender;
    msgsEl.insertAdjacentHTML('beforeend', html);
    if (scroll || nearBottom || !lastEl) msgsEl.scrollTop = msgsEl.scrollHeight;
  }

  function prependMessages(list) {
    if (!list.length) return;
    const oldH = msgsEl.scrollHeight;
    const isGroup = active && active.kind !== 'user' && active.kind !== 'bot';
    let prevDay = '', prevSender = '', html = '';
    list.forEach(m => {
      if (msgsEl.querySelector('.msg[data-id="' + m.id + '"]')) return;
      const dk = dayKey(m.date);
      if (dk !== prevDay) { html += '<div class="day-sep">' + dayLabel(m.date) + '</div>'; prevDay = dk; prevSender = ''; }
      const sKey = (m.out ? 'out' : 'in') + ':' + m.sender;
      html += msgHtml(m, isGroup && !m.out && sKey !== prevSender);
      prevSender = sKey;
      if (!firstId || m.id < firstId) firstId = m.id;
      lastId = Math.max(lastId, m.id);
    });
    // birinchi kun ajratgichi takrorlanmasin
    const firstSep = msgsEl.querySelector('.day-sep');
    msgsEl.insertAdjacentHTML('afterbegin', html);
    if (firstSep && list.length && firstSep.textContent === dayLabel(list[list.length - 1].date)) firstSep.remove();
    msgsEl.scrollTop = msgsEl.scrollHeight - oldH;
  }

  async function loadOlder() {
    if (!active || loadingOlder || noMoreOlder) return;
    loadingOlder = true;
    const id = active.id;
    try {
      // avval bazadagi eskiroq xabarlar
      let d = await api('/api/inbox/chats/' + id + '/messages?before=' + (firstId || 0));
      if (active.id !== id) return;
      if (!d.messages.length || !firstId) {
        // bazada yo'q — Telegramdan tortib olamiz
        const r = await api('/api/inbox/chats/' + id + '/older', { method: 'POST' });
        if (active.id !== id) return;
        if (!r.count) { noMoreOlder = true; if (!msgsEl.querySelector('.msg')) msgsEl.innerHTML = '<div class="empty small">Xabarlar yo\'q</div>'; return; }
        d = await api('/api/inbox/chats/' + id + '/messages' + (firstId ? '?before=' + firstId : ''));
        if (active.id !== id) return;
        if (!firstId) { msgsEl.innerHTML = ''; appendMessages(d.messages, true); return; }
      }
      prependMessages(d.messages);
    } catch (e) {
      DN.toast(e.message, 'error');
    } finally {
      loadingOlder = false;
    }
  }
  msgsEl.addEventListener('scroll', () => { if (msgsEl.scrollTop < 60) loadOlder(); });

  msgsEl.addEventListener('click', e => {
    const img = e.target.closest('img.media');
    if (img) { DN.lightbox(img.dataset.full); return; }
    const at = e.target.closest('[data-attach]');
    if (at) {
      attachMsgId = Number(at.dataset.attach);
      $('attach-job').value = '';
      $('attach-dlg').showModal();
    }
  });
  $('attach-dlg').addEventListener('close', async () => {
    if ($('attach-dlg').returnValue !== 'ok' || !attachMsgId) return;
    try {
      const d = await api('/api/inbox/messages/' + attachMsgId + '/attach', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ job_id: $('attach-job').value, kind: $('attach-kind').value }),
      });
      DN.toast('Fayl #' + d.job_id + ' «' + d.title + '» ishiga biriktirildi');
    } catch (err) { DN.toast(err.message, 'error'); }
  });

  async function pollMessages() {
    if (!active || document.hidden) return;
    const id = active.id;
    try {
      const d = await api('/api/inbox/chats/' + id + '/messages?after=' + lastId);
      if (!active || active.id !== id) return;
      // Telegramdan tortilgan eski xabarlar pastga qo'shilib ketmasin (ular tepaga yuklanadi)
      const fresh = d.messages.filter(m => !lastDate || new Date(m.date).getTime() >= lastDate - 1000);
      d.messages.forEach(m => { lastId = Math.max(lastId, m.id); });
      appendMessages(fresh, false);
    } catch (e) { /* jim */ }
  }

  // ---------------- yuborish ----------------
  fileEl.addEventListener('change', () => {
    const f = fileEl.files[0];
    if (!f) { attEl.classList.add('hidden'); return; }
    if (f.size > (window.DN_MAX_MB || 300) * 1048576) { DN.toast('Fayl juda katta', 'error'); fileEl.value = ''; return; }
    attEl.innerHTML = '📎 ' + DN.esc(f.name) + ' (' + sizeFmt(f.size) + ') <a href="#" id="att-x">✕</a>';
    attEl.classList.remove('hidden');
    $('att-x').onclick = ev => { ev.preventDefault(); fileEl.value = ''; attEl.classList.add('hidden'); };
  });
  textEl.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); $('composer').requestSubmit(); }
  });
  textEl.addEventListener('input', () => { textEl.style.height = 'auto'; textEl.style.height = Math.min(textEl.scrollHeight, 160) + 'px'; });
  $('composer').addEventListener('submit', async e => {
    e.preventDefault();
    if (!active) return;
    const text = textEl.value.trim();
    const file = fileEl.files[0];
    if (!text && !file) return;
    const fd = new FormData();
    fd.append('text', text);
    if (file) fd.append('file', file);
    const btn = $('send-btn');
    btn.disabled = true;
    try {
      const d = await api('/api/inbox/chats/' + active.id + '/send', { method: 'POST', body: fd });
      textEl.value = ''; textEl.style.height = '';
      fileEl.value = ''; attEl.classList.add('hidden');
      if (d.message) appendMessages([d.message], true); else pollMessages();
      loadChats();
    } catch (err) {
      DN.toast(err.message, 'error');
    } finally {
      btn.disabled = false;
      textEl.focus();
    }
  });

  $('back-btn').addEventListener('click', () => {
    active = null;
    root.classList.remove('has-chat');
    history.replaceState(null, '', '/inbox');
    renderChats();
  });
  $('hide-btn').addEventListener('click', async () => {
    if (!active || !confirm('«' + active.title + '» chatini ro\'yxatdan olib tashlaysizmi? (Telegramda o\'chmaydi)')) return;
    try {
      await api('/api/inbox/chats/' + active.id + '/hide', { method: 'POST' });
      active = null;
      root.classList.remove('has-chat');
      $('conv-empty').classList.remove('hidden');
      ['conv-h', 'msgs', 'composer'].forEach(x => $(x).classList.add('hidden'));
      loadChats();
    } catch (err) { DN.toast(err.message, 'error'); }
  });

  // inbox oynasi ekran balandligiga moslashsin
  function fitHeight() {
    const top = root.getBoundingClientRect().top + window.scrollY;
    root.style.height = Math.max(420, window.innerHeight - top - 20) + 'px';
  }
  fitHeight();
  window.addEventListener('resize', fitHeight);

  // ---------------- ishga tushirish ----------------
  loadChats().then(() => {
    const open = Number(root.dataset.open);
    if (open) openChat(open);
  });
  setInterval(() => { if (!document.hidden) loadChats(); }, 5000);
  setInterval(pollMessages, 3000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) { loadChats(); pollMessages(); } });
})();
