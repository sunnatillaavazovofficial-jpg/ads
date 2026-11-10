(function () {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));

  // ---------- mobil menyu
  const navBtn = $("#nav-toggle");
  if (navBtn) {
    navBtn.addEventListener("click", () => document.body.classList.toggle("nav-open"));
    document.addEventListener("click", (e) => {
      if (document.body.classList.contains("nav-open") && !e.target.closest(".sidebar") && e.target !== navBtn) {
        document.body.classList.remove("nav-open");
      }
    });
  }

  // ---------- tasdiqlash
  document.addEventListener("submit", (e) => {
    const msg = e.target.getAttribute("data-confirm");
    if (msg && !window.confirm(msg)) e.preventDefault();
  });

  // ---------- "Yo'q" belgisi (ish formasi)
  function syncStep(step) {
    const cb = $(".none-cb", step);
    if (!cb) return;
    const none = cb.checked;
    step.classList.toggle("is-none", none);
    $$(".wf-body input, .wf-body textarea, .wf-body select", step).forEach((el) => {
      if (el.classList.contains("keep")) return;
      el.disabled = none;
    });
  }
  $$(".wf-step").forEach((step) => {
    const cb = $(".none-cb", step);
    if (!cb) return;
    cb.addEventListener("change", () => syncStep(step));
    $$(".wf-body input[type=file]", step).forEach((inp) =>
      inp.addEventListener("change", () => {
        if (inp.files.length) { cb.checked = false; syncStep(step); }
        const list = inp.parentElement.querySelector(".picked");
        if (list) list.textContent = Array.from(inp.files).map((f) => f.name).join(", ");
      })
    );
    syncStep(step);
  });
  const workForm = $("#work-form");
  if (workForm) {
    workForm.addEventListener("submit", (e) => {
      const missing = [];
      $$(".wf-step[data-required]", workForm).forEach((step) => {
        const cb = $(".none-cb", step);
        if (cb && cb.checked) return;
        const kind = step.getAttribute("data-required");
        let ok = true;
        if (kind === "file") {
          const inp = $("input[type=file]", step);
          const kept = $$(".existing-files input[type=checkbox]", step).filter((c) => !c.checked).length;
          ok = (inp && inp.files.length > 0) || kept > 0;
        } else if (kind === "size") {
          ok = $$("input[name=width], input[name=height]", step).every((i) => parseFloat((i.value || "").replace(",", ".")) > 0);
        } else {
          const el = $("input[type=text], textarea, select", step);
          ok = el && el.value.trim() !== "";
        }
        step.classList.toggle("has-err", !ok);
        if (!ok) missing.push(step.getAttribute("data-label"));
      });
      if (missing.length) {
        e.preventDefault();
        alert("Quyidagilarni to'ldiring yoki «Yo'q» deb belgilang:\n\n• " + missing.join("\n• "));
        const first = $(".wf-step.has-err", workForm);
        if (first) first.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
      }
      const btn = $("button[type=submit]", workForm);
      if (btn) { btn.disabled = true; btn.textContent = "Yuklanmoqda..."; }
    });
  }

  // ---------- hisob: material tanlanganda narxlarni to'ldirish
  const expForm = $("#expense-form");
  if (expForm) {
    const sel = $("select[name=material_id]", expForm);
    const area = parseFloat(expForm.getAttribute("data-area") || "0");
    sel.addEventListener("change", () => {
      const opt = sel.selectedOptions[0];
      const custom = !opt.value;
      $("input[name=name]", expForm).value = custom ? "" : opt.dataset.name;
      $("input[name=unit]", expForm).value = custom ? "" : opt.dataset.unit;
      $("input[name=cost_price]", expForm).value = custom ? "" : opt.dataset.cost;
      $("input[name=sell_price]", expForm).value = custom ? "" : opt.dataset.sell;
      const qty = $("input[name=qty]", expForm);
      if (!custom && opt.dataset.unit === "m²" && area > 0) qty.value = area;
      else if (!custom && !qty.value) qty.value = 1;
      $(".custom-name", expForm).style.display = custom ? "" : "none";
    });
  }

  // ---------- rasmni katta ko'rish
  const lb = document.createElement("div");
  lb.className = "lightbox";
  lb.innerHTML = "<img alt=''>";
  document.body.appendChild(lb);
  lb.addEventListener("click", () => lb.classList.remove("open"));
  document.addEventListener("click", (e) => {
    const a = e.target.closest("[data-lightbox]");
    if (!a) return;
    e.preventDefault();
    $("img", lb).src = a.getAttribute("data-lightbox");
    lb.classList.add("open");
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") lb.classList.remove("open"); });

  // ---------- Telegram: chatlar ro'yxatini yangilab turish
  const chatList = $("#tg-chat-list");
  if (chatList) {
    const filter = $("#chat-filter");
    const applyFilter = () => {
      const q = (filter && filter.value || "").toLowerCase();
      $$(".list-item", chatList).forEach((it) => {
        it.style.display = !q || it.textContent.toLowerCase().includes(q) ? "" : "none";
      });
    };
    if (filter) filter.addEventListener("input", applyFilter);
    setInterval(async () => {
      if (document.hidden) return;
      try {
        const r = await fetch("/telegram?partial=1", { headers: { "X-Requested-With": "fetch" } });
        if (r.ok) { chatList.innerHTML = await r.text(); applyFilter(); }
      } catch (_) { /* tarmoq xatosi */ }
    }, 15000);
  }

  // ---------- Telegram: chat tanlash sahifasida qidirish
  const dlgFilter = $("#dialog-filter");
  if (dlgFilter) {
    const items = $$(".dialogs .list-item");
    const kindSel = $("#dialog-kind");
    const apply = () => {
      const q = dlgFilter.value.toLowerCase();
      const k = kindSel ? kindSel.value : "";
      items.forEach((it) => {
        const okText = !q || it.textContent.toLowerCase().includes(q);
        const okKind = !k || it.dataset.kind === k || (k === "selected" && $("input", it).checked);
        it.style.display = okText && okKind ? "" : "none";
      });
    };
    dlgFilter.addEventListener("input", apply);
    if (kindSel) kindSel.addEventListener("change", apply);
    const counter = $("#selected-count");
    const recount = () => { if (counter) counter.textContent = $$(".dialogs input[name=peer]:checked").length; };
    $$(".dialogs input[name=peer]").forEach((c) => c.addEventListener("change", recount));
    recount();
  }

  // ---------- Telegram: chat oynasi
  const box = $("#messages");
  if (box) {
    const chatId = box.dataset.chat;
    let lastId = parseInt(box.dataset.last || "0", 10);
    let firstId = parseInt(box.dataset.first || "0", 10);
    const scrollDown = () => { box.scrollTop = box.scrollHeight; };
    scrollDown();
    $$("img", box).forEach((img) => img.addEventListener("load", () => { if (box.dataset.stick !== "0") scrollDown(); }, { once: true }));
    box.addEventListener("scroll", () => {
      box.dataset.stick = box.scrollHeight - box.scrollTop - box.clientHeight < 80 ? "1" : "0";
    });

    async function poll() {
      if (document.hidden) return;
      try {
        const r = await fetch(`/telegram/chat/${chatId}/messages?after=${lastId}`, { headers: { "X-Requested-With": "fetch" } });
        if (!r.ok) return;
        const data = await r.json();
        if (data.count) {
          const atBottom = box.dataset.stick !== "0";
          box.insertAdjacentHTML("beforeend", data.html);
          lastId = data.last_id;
          if (atBottom) scrollDown();
        }
      } catch (_) { /* tarmoq xatosi */ }
    }
    setInterval(poll, 5000);

    const older = $("#load-older");
    if (older) {
      older.addEventListener("click", async () => {
        older.disabled = true;
        const r = await fetch(`/telegram/chat/${chatId}/messages?before=${firstId}`, { headers: { "X-Requested-With": "fetch" } });
        older.disabled = false;
        if (!r.ok) return;
        const data = await r.json();
        if (!data.count) { older.textContent = "Boshqa xabar yo'q"; older.disabled = true; return; }
        const prevH = box.scrollHeight;
        older.insertAdjacentHTML("afterend", data.html);
        firstId = data.first_id;
        box.scrollTop = box.scrollHeight - prevH;
      });
    }

    const sendForm = $("#send-form");
    if (sendForm) {
      const ta = $("textarea", sendForm);
      ta.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendForm.requestSubmit(); }
      });
      sendForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!ta.value.trim()) return;
        const fd = new FormData(sendForm);
        ta.disabled = true;
        try {
          const r = await fetch(sendForm.action, { method: "POST", body: fd, headers: { "X-Requested-With": "fetch" } });
          const data = await r.json();
          if (!r.ok) alert(data.error || "Yuborilmadi");
          else { ta.value = ""; box.dataset.stick = "1"; await poll(); }
        } catch (_) { alert("Tarmoq xatosi"); }
        ta.disabled = false;
        ta.focus();
      });
    }
  }
})();
