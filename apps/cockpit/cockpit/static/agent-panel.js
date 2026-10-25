/* The side panel: the person's team, on every page of the cockpit and inside the applications it mounts (ADR-020).
 * Self-contained: the shell includes it, and the cockpit injects it into /w/<id>/ pages. It talks only to the
 * cockpit's own API, with the cookie and the CSRF header, and reports where the person is as the session's place.
 */
(function () {
  if (window.__agentPanel) return;
  window.__agentPanel = true;
  var script = document.currentScript;
  var BASE = script ? new URL(script.src, location.href).pathname.replace(/\/static\/agent-panel\.js$/, '') : '';
  var DE = (document.documentElement.lang || 'de').slice(0, 2) !== 'en';
  var T = DE ? {
    team: 'Mein Team', start: 'Session starten', topic: 'Thema — eine Zeile', send: 'Senden', end: 'Session beenden',
    endNote: 'Notiz zum Abschluss (optional)', thinking: 'denkt nach …', writing: 'schreibt das Session-Log …', full: 'Vollansicht',
    back: '← Team', place: 'Ort', none: 'Noch niemand im Team. Stell auf der Seite „Mein Team“ einen Agenten ein.',
    manage: 'Team verwalten', running: 'läuft', closed: 'Session beendet.', log: 'Log', keys: 'Return sendet · Shift+Return neue Zeile',
    dictate: 'Diktieren', close: 'Schließen', stale: 'Die Seite ist veraltet — bitte neu laden.'
  } : {
    team: 'My team', start: 'Start session', topic: 'Topic — one line', send: 'Send', end: 'End session',
    endNote: 'Closing note (optional)', thinking: 'thinking …', writing: 'writing the session log …', full: 'Full view',
    back: '← Team', place: 'Place', none: 'Nobody on your team yet. Hire an agent on the “My team” page.',
    manage: 'Manage team', running: 'running', closed: 'Session ended.', log: 'Log', keys: 'Return sends · Shift+Return new line',
    dictate: 'Dictate', close: 'Close', stale: 'The page is stale — please reload.'
  };
  function store(k, v) { try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, v); } catch (e) {} }
  function read(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  var csrf = (document.cookie.match(/(?:^|; )csrf=([^;]+)/) || [])[1] || '';

  function place() {
    var m = location.pathname.slice(BASE.length).match(/^\/w\/([a-z0-9][a-z0-9_-]*)\/?(.*)$/);
    var p = { url: location.pathname + location.hash, title: document.title };
    if (m) { p.workspace = m[1]; p.item = (m[2] + location.hash).replace(/^\/+/, '') || undefined; }
    var app = document.querySelector('meta[name="cf-app"]');
    if (app) p.application = app.content;
    return p;
  }
  function api(method, path, body) {
    var opt = { method: method, credentials: 'same-origin', headers: { 'X-CSRF': csrf } };
    if (body) { opt.headers['Content-Type'] = 'application/json'; opt.body = JSON.stringify(body); }
    return fetch(BASE + path, opt).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) { if (!r.ok) throw new Error(j.reason || (r.status === 403 ? T.stale : r.status)); return j; });
    });
  }
  function avatar(a, size) {
    var s = el('span', 'ap-av' + (size ? ' ' + size : ''));
    if (a.img) { var i = el('img'); i.src = BASE + '/api/agents/' + a.id + '/avatar'; i.alt = ''; s.appendChild(i); }
    else s.textContent = a.initials || '?';
    return s;
  }

  // ---------------------------------------------------------------- the frame
  var launcher = el('button', 'ap-launch'); launcher.type = 'button'; launcher.setAttribute('aria-label', T.team);
  var panel = el('aside', 'ap-panel'); panel.setAttribute('aria-label', T.team); panel.hidden = true;
  var head = el('div', 'ap-head'); var title = el('b', null, T.team); var closeBtn = el('button', 'ap-x', '×');
  closeBtn.type = 'button'; closeBtn.setAttribute('aria-label', T.close);
  head.appendChild(title); head.appendChild(closeBtn);
  var body = el('div', 'ap-body');
  panel.appendChild(head); panel.appendChild(body);
  document.body.appendChild(launcher); document.body.appendChild(panel);
  document.body.classList.add('has-agent-panel');

  var state = { agents: [], sessions: [], current: read('ap-session'), timer: null };
  function open(on) { panel.hidden = !on; launcher.classList.toggle('on', on); store('ap-open', on ? '1' : null); if (on) refresh(); }
  launcher.addEventListener('click', function () { open(panel.hidden); });
  closeBtn.addEventListener('click', function () { open(false); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !panel.hidden) open(false); });

  function drawLauncher() {
    launcher.innerHTML = '';
    var stack = el('span', 'ap-stack');
    state.agents.slice(0, 3).forEach(function (a) { stack.appendChild(avatar(a, 'sm')); });
    if (!state.agents.length) stack.appendChild(el('span', 'ap-av sm', '+'));
    launcher.appendChild(stack);
    var answered = state.sessions.filter(function (s) { return s.kind === 'answered'; }).length;
    if (answered) launcher.appendChild(el('span', 'ap-badge', String(answered)));
  }

  function refresh() {
    return api('GET', '/api/team').then(function (j) {
      state.agents = j.agents || []; state.sessions = j.sessions || []; if (j.csrf) csrf = j.csrf;
      drawLauncher();
      if (panel.hidden) return;
      if (state.current) return showSession(state.current);
      showTeam();
    }).catch(function () { launcher.hidden = true; });
  }

  // ---------------------------------------------------------------- the team
  function showTeam(err) {
    stopPoll(); state.current = null; store('ap-session', null);
    title.textContent = T.team; body.innerHTML = '';
    if (err) body.appendChild(el('p', 'ap-err', err));
    if (!state.agents.length) body.appendChild(el('p', 'ap-hint', T.none));
    state.agents.forEach(function (a) {
      var row = el('button', 'ap-agent'); row.type = 'button';
      row.appendChild(avatar(a));
      var txt = el('span', 'ap-agent-tx'); txt.appendChild(el('b', null, a.label));
      var mine = state.sessions.filter(function (s) { return s.agent_id === a.id; });
      if (mine.length) txt.appendChild(el('small', null, T.running + ': ' + mine[0].topic));
      row.appendChild(txt);
      row.addEventListener('click', function () {
        var run = state.sessions.filter(function (s) { return s.agent_id === a.id; })[0];
        if (run) showSession(run.session); else showStart(a);
      });
      body.appendChild(row);
    });
    var manage = el('a', 'ap-link', T.manage); manage.href = BASE + '/team'; body.appendChild(manage);
  }

  function showStart(a) {
    body.innerHTML = '';
    var back = el('button', 'ap-back', T.back); back.type = 'button'; back.onclick = function () { showTeam(); };
    body.appendChild(back);
    var who = el('div', 'ap-who'); who.appendChild(avatar(a, 'lg')); who.appendChild(el('b', null, a.label)); body.appendChild(who);
    var p = place();
    body.appendChild(el('p', 'ap-hint', T.place + ': ' + (p.workspace ? p.workspace + (p.item ? ' · ' + p.item : '') : (p.title || p.url))));
    var input = el('input', 'ap-input'); input.placeholder = T.topic; input.maxLength = 120;
    var go = el('button', 'ap-primary', T.start); go.type = 'button';
    function start() {
      if (!input.value.trim()) { input.focus(); return; }
      go.disabled = true;
      api('POST', '/api/sessions', { agent: a.id, topic: input.value, place: place() })
        .then(function (j) { return refresh().then(function () { showSession(j.id); }); })
        .catch(function (e) { go.disabled = false; showTeam(e.message); });
    }
    go.onclick = start;
    input.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.isComposing) { e.preventDefault(); start(); } });
    body.appendChild(input); body.appendChild(go);
    input.focus();
  }

  // ---------------------------------------------------------------- one session
  function showSession(sid) {
    state.current = sid; store('ap-session', sid);
    return api('GET', '/api/sessions/' + sid).then(drawSession).catch(function (e) { showTeam(e.message); });
  }

  function drawSession(v) {
    var keepDraft = body.querySelector('.ap-text');
    var draft = keepDraft ? keepDraft.value : '';
    title.textContent = v.label + ' · ' + v.topic;
    body.innerHTML = '';
    var bar = el('div', 'ap-bar');
    var back = el('button', 'ap-back', T.back); back.type = 'button'; back.onclick = function () { refresh().then(function () { showTeam(); }); };
    var full = el('a', 'ap-link', T.full); full.href = BASE + '/sessions/' + v.id;
    bar.appendChild(back); bar.appendChild(full); body.appendChild(bar);
    if (v.place && (v.place.workspace || v.place.item)) body.appendChild(el('p', 'ap-hint', T.place + ': ' + [v.place.workspace, v.place.item].filter(Boolean).join(' · ')));
    var log = el('div', 'ap-log');
    v.turns.forEach(function (t) {
      var m = el('div', 'ap-msg ' + t.role);
      if (t.role === 'assistant' && t.html != null) { var b = el('div', 'ap-md'); b.innerHTML = t.html; m.appendChild(b); }
      else m.appendChild(el('div', 'ap-plain', t.text));
      log.appendChild(m);
    });
    if (v.pending) log.appendChild(el('div', 'ap-msg assistant wait', v.pending === 'end' ? T.writing : T.thinking));
    if (v.status === 'closed') log.appendChild(el('p', 'ap-hint', T.closed + (v.log ? ' ' + T.log + ': ' + v.log : '')));
    body.appendChild(log);
    if (v.status === 'active') {
      var text = el('textarea', 'ap-text'); text.rows = 3; text.placeholder = T.keys; text.value = draft; text.disabled = !!v.pending;
      var row = el('div', 'ap-row');
      var send = el('button', 'ap-primary', T.send); send.type = 'button'; send.disabled = !!v.pending;
      var Rec = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (Rec) {
        var mic = el('button', 'ap-mic'); mic.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" d="M12 15a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3Zm5-3a1 1 0 1 1 2 0 7 7 0 0 1-6 6.93V21h3a1 1 0 1 1 0 2H8a1 1 0 1 1 0-2h3v-2.07A7 7 0 0 1 5 12a1 1 0 1 1 2 0 5 5 0 0 0 10 0Z"/></svg>'; mic.type = 'button'; mic.title = T.dictate; mic.disabled = !!v.pending;
        var rec = null, baseText = '';
        mic.onclick = function () {
          if (rec) { rec.stop(); return; }
          rec = new Rec(); rec.lang = DE ? 'de-DE' : 'en-US'; rec.interimResults = true; rec.continuous = true;
          baseText = text.value ? text.value.replace(/\s*$/, ' ') : '';
          rec.onresult = function (ev) { var s = ''; for (var i = 0; i < ev.results.length; i++) s += ev.results[i][0].transcript; text.value = baseText + s; };
          rec.onend = function () { rec = null; mic.classList.remove('on'); text.focus(); };
          rec.start(); mic.classList.add('on');
        };
        row.appendChild(mic);
      }
      function say() {
        if (!text.value.trim()) return;
        send.disabled = true;
        api('POST', '/api/sessions/' + v.id + '/say', { text: text.value }).then(function () { text.value = ''; return showSession(v.id); })
          .catch(function (e) { send.disabled = false; body.insertBefore(el('p', 'ap-err', e.message), log); });
      }
      send.onclick = say;
      text.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing && e.keyCode !== 229) { e.preventDefault(); say(); } });
      row.appendChild(send);
      body.appendChild(text); body.appendChild(row);
      var endRow = el('div', 'ap-row');
      var note = el('input', 'ap-input'); note.placeholder = T.endNote;
      var end = el('button', 'ap-quiet', T.end); end.type = 'button'; end.disabled = !!v.pending;
      end.onclick = function () {
        end.disabled = true;
        api('POST', '/api/sessions/' + v.id + '/end', { note: note.value }).then(function () { return showSession(v.id); })
          .catch(function (e) { end.disabled = false; body.insertBefore(el('p', 'ap-err', e.message), log); });
      };
      endRow.appendChild(note); endRow.appendChild(end); body.appendChild(endRow);
      if (!v.pending) text.focus();
    }
    log.scrollTop = log.scrollHeight;
    stopPoll();
    if (v.pending) state.timer = setTimeout(function () { showSession(v.id); }, 3000);
    else if (v.status !== 'active') refresh().then(drawLauncher);
  }
  function stopPoll() { if (state.timer) { clearTimeout(state.timer); state.timer = null; } }

  // the person menu and other pages can open the panel on an agent: <a data-agent-panel="atlas">
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('[data-agent-panel]');
    if (!t) return;
    e.preventDefault();
    open(true);
    var aid = t.getAttribute('data-agent-panel');
    refresh().then(function () {
      var a = state.agents.filter(function (x) { return x.id === aid; })[0];
      if (!a) return;
      var run = state.sessions.filter(function (s) { return s.agent_id === a.id; })[0];
      if (run) showSession(run.session); else showStart(a);
    });
  });

  refresh().then(function () { if (read('ap-open') === '1') open(true); });
  setInterval(function () { if (panel.hidden) refresh(); }, 30000);    // the badge stays current while the panel is closed
})();
