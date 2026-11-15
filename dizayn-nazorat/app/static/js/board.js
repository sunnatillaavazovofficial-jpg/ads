(function () {
  'use strict';
  const board = document.getElementById('board');
  if (!board) return;
  let dragged = null;
  let fromCol = null;

  board.addEventListener('dragstart', e => {
    const card = e.target.closest('.kcard');
    if (!card) return;
    dragged = card;
    fromCol = card.closest('.col');
    card.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', card.dataset.id);
  });
  board.addEventListener('dragend', () => {
    if (dragged) dragged.classList.remove('dragging');
    board.querySelectorAll('.col').forEach(c => c.classList.remove('drag-over'));
  });
  board.querySelectorAll('.col').forEach(col => {
    col.addEventListener('dragover', e => { e.preventDefault(); col.classList.add('drag-over'); });
    col.addEventListener('dragleave', e => { if (!col.contains(e.relatedTarget)) col.classList.remove('drag-over'); });
    col.addEventListener('drop', async e => {
      e.preventDefault();
      col.classList.remove('drag-over');
      if (!dragged || col === fromCol) return;
      const card = dragged;
      const prevCol = fromCol;
      col.querySelector('.col-b').prepend(card);
      updateCounts();
      try {
        const r = await fetch('/jobs/' + card.dataset.id + '/status', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
          body: JSON.stringify({ status: col.dataset.status }),
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.error || 'Xato');
        DN.toast('#' + card.dataset.id + ' → ' + d.label);
      } catch (err) {
        prevCol.querySelector('.col-b').prepend(card);
        updateCounts();
        DN.toast('Holat o\'zgarmadi: ' + err.message, 'error');
      }
    });
  });
  function updateCounts() {
    board.querySelectorAll('.col').forEach(c => { c.querySelector('.n').textContent = c.querySelectorAll('.kcard').length; });
  }
})();
