/*
 * Avisos en vivo del panel. Abre un WebSocket con el servidor y, por cada evento,
 * dispara `support:event` en document para que cada página actualice lo suyo.
 */
(function () {
  const script = document.currentScript;
  const listUrl = script.dataset.listUrl;
  const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + script.dataset.wsPath;
  const statusEl = document.getElementById('liveStatus');
  const labels = { connecting: 'Conectando…', online: 'En vivo', offline: 'Sin conexión' };
  const baseTitle = document.title;
  let unread = 0;
  let retryDelay = 1000;

  function setStatus(state) {
    if (!statusEl) return;
    statusEl.dataset.state = state;
    statusEl.querySelector('.live-label').textContent = labels[state];
  }

  // Resalta un elemento recién insertado o actualizado.
  window.LiveFlash = function (el) {
    if (!el) return;
    el.classList.remove('live-flash');
    void el.offsetWidth;
    el.classList.add('live-flash');
  };

  function showToast(ticket) {
    const toast = document.createElement('div');
    toast.className = 'toast live-toast';
    toast.setAttribute('role', 'status');
    const body = document.createElement('a');
    body.className = 'toast-body d-block text-decoration-none text-reset';
    body.href = listUrl + ticket.id + '/';
    const title = document.createElement('div');
    title.className = 'fw-semibold';
    title.textContent = 'Nuevo ticket ' + ticket.folio;
    const detail = document.createElement('div');
    detail.className = 'small text-muted';
    detail.textContent = ticket.application + ' · ' + ticket.issue_display + ' · ' + ticket.email;
    body.append(title, detail);
    toast.append(body);
    document.getElementById('liveToasts').append(toast);
    const instance = bootstrap.Toast.getOrCreateInstance(toast, { delay: 8000 });
    toast.addEventListener('hidden.bs.toast', () => toast.remove());
    instance.show();
  }

  function notifyTitle() {
    if (!document.hidden) return;
    unread += 1;
    document.title = '(' + unread + ') ' + baseTitle;
  }

  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) { unread = 0; document.title = baseTitle; }
  });

  function connect() {
    setStatus('connecting');
    const ws = new WebSocket(wsUrl);

    ws.onopen = function () {
      retryDelay = 1000;
      setStatus('online');
    };

    ws.onmessage = function (msg) {
      const data = JSON.parse(msg.data);
      document.dispatchEvent(new CustomEvent('support:event', { detail: data }));
      if (data.event === 'ticket.created') {
        showToast(data.ticket);
        notifyTitle();
      }
    };

    ws.onclose = function (e) {
      setStatus('offline');
      // 4401 = sesión vencida: reintenta despacio; navegar por el panel renueva la sesión.
      const delay = e.code === 4401 ? 30000 : retryDelay;
      retryDelay = Math.min(retryDelay * 2, 30000);
      setTimeout(connect, delay);
    };
  }

  connect();
})();
