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
    dictate: 'Diktieren', close: 'Schließen', stale: 'Die Seite ist veraltet — bitte neu laden.',
    help: 'Hilfe zu dieser Seite', tour: 'Tour starten', next: 'Weiter', prev: 'Zurück', done: 'Fertig', isNew: 'neu',
    askHelp: 'Frag nach — z. B. „Wie lege ich einen neuen Fall an?“', askWho: 'Wen fragen?', noTopics: 'Zu dieser Seite gibt es noch keine Hilfe.',
    ref: 'Bezug', refOff: 'Ohne Bezug — allgemeine Frage', refOn: 'Bezug einschalten', refNone: 'Kein Fall geöffnet — allgemeine Frage'
  } : {
    team: 'My team', start: 'Start session', topic: 'Topic — one line', send: 'Send', end: 'End session',
    endNote: 'Closing note (optional)', thinking: 'thinking …', writing: 'writing the session log …', full: 'Full view',
    back: '← Team', place: 'Place', none: 'Nobody on your team yet. Hire an agent on the “My team” page.',
    manage: 'Manage team', running: 'running', closed: 'Session ended.', log: 'Log', keys: 'Return sends · Shift+Return new line',
    dictate: 'Dictate', close: 'Close', stale: 'The page is stale — please reload.',
    help: 'Help for this page', tour: 'Start the tour', next: 'Next', prev: 'Back', done: 'Done', isNew: 'new',
    askHelp: 'Ask — e.g. “How do I start a new case?”', askWho: 'Ask whom?', noTopics: 'There is no help for this page yet.',
    ref: 'About', refOff: 'No reference — a general question', refOn: 'Switch the reference on', refNone: 'No case open — a general question'
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
  // what the application reports as open (casefile: 'casefile:focus'); the workspace comes from the address
  var appFocus = window.casefileFocus || null;
  window.addEventListener('casefile:focus', function (e) { appFocus = e.detail || null; drawChip(); });
  function focus() {
    var p = place();
    if (!appFocus || !appFocus.case) return null;
    var f = {}; for (var k in appFocus) if (appFocus[k] != null) f[k] = appFocus[k];
    if (p.workspace) f.workspace = p.workspace;
    return f;
  }
  function focusOn() { return read('ap-ref-off') !== '1'; }
  var chipHost = null;
  function drawChip() {
    if (!chipHost) return;
    chipHost.innerHTML = '';
    var f = focus(), on = focusOn();
    var chip = el('div', 'ap-chip' + (f && on ? '' : ' off'));
    if (f && on) {
      chip.appendChild(el('span', 'ap-chip-k', T.ref));
      chip.appendChild(el('span', 'ap-chip-v', [f.label, f.case].filter(Boolean).join(' ') + (f.title ? ' · ' + f.title : '') + (f.document ? ' · ' + f.document : '')));
      var x = el('button', 'ap-chip-x', '×'); x.type = 'button'; x.title = T.refOff;
      x.onclick = function () { store('ap-ref-off', '1'); drawChip(); };
      chip.appendChild(x);
    } else if (f) {
      var b = el('button', 'ap-chip-on', T.refOn + ': ' + [f.label, f.case].filter(Boolean).join(' ')); b.type = 'button';
      b.onclick = function () { store('ap-ref-off', null); drawChip(); };
      chip.appendChild(b);
    } else {
      chip.appendChild(el('span', 'ap-chip-v', T.refNone));
    }
    chipHost.appendChild(chip);
  }
  if (/\/w\/[a-z0-9]/.test(location.pathname.slice(BASE.length))) document.documentElement.classList.add('ap-in-app');

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
  launcher.setAttribute('data-help', 'panel.launcher');
  var panel = el('aside', 'ap-panel'); panel.setAttribute('aria-label', T.team); panel.hidden = true;
  var head = el('div', 'ap-head'); var title = el('b', null, T.team); var closeBtn = el('button', 'ap-x', '×');
  closeBtn.type = 'button'; closeBtn.setAttribute('aria-label', T.close);
  var helpBtn = el('button', 'ap-x ap-help', '?'); helpBtn.type = 'button'; helpBtn.title = T.help;
  helpBtn.setAttribute('aria-label', T.help); helpBtn.setAttribute('data-help', 'panel.help');
  head.appendChild(title); head.appendChild(helpBtn); head.appendChild(closeBtn);
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
      var pl = place(), f = focus();
      if (f) { for (var k in f) pl[k] = f[k]; }
      api('POST', '/api/sessions', { agent: a.id, topic: input.value, place: pl })
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
      chipHost = el('div', 'ap-chips'); body.appendChild(chipHost); drawChip();
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
        api('POST', '/api/sessions/' + v.id + '/say', { text: text.value, focus: focusOn() ? focus() : null }).then(function () { text.value = ''; return showSession(v.id); })
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

  // ---------------------------------------------------------------- help for this page
  var helpData = null;
  function loadHelp() { return helpData ? Promise.resolve(helpData) : api('GET', '/api/help').then(function (j) { helpData = j; return j; }); }
  function newer(a, b) {                                  // semver-ish: is a newer than b?
    var x = String(a || '0').split('.').map(Number), y = String(b || '0').split('.').map(Number);
    for (var i = 0; i < 3; i++) { if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) > (y[i] || 0); }
    return false;
  }
  function onPage() {                                    // the topics whose anchors are visible right now, in page order
    var seen = {}, list = [];
    document.querySelectorAll('[data-help]').forEach(function (n) {
      var k = n.getAttribute('data-help'); if (seen[k]) return;
      var r = n.getBoundingClientRect(); if (!r.width && !r.height) return;
      seen[k] = 1; list.push(k);
    });
    return list;
  }
  function showHelp() {
    stopPoll(); title.textContent = T.help; body.innerHTML = '';
    loadHelp().then(function (h) {
      var keys = onPage(), byKey = {}; h.topics.forEach(function (t) { byKey[t.key] = t; });
      var topics = keys.map(function (k) { return byKey[k]; }).filter(Boolean);
      var lastSeen = read('ap-help-seen');
      var back = el('button', 'ap-back', T.back); back.type = 'button'; back.onclick = function () { showTeam(); };
      body.appendChild(back);
      var surfaces = {}; topics.forEach(function (t) { surfaces[t.surface] = 1; });
      Object.keys(surfaces).forEach(function (s) { if (h.surfaces[s]) body.appendChild(el('p', 'ap-hint', h.surfaces[s])); });
      if (!topics.length) { body.appendChild(el('p', 'ap-hint', T.noTopics)); return; }
      var go = el('button', 'ap-primary', T.tour); go.type = 'button'; go.onclick = function () { tour(topics, 0); };
      body.appendChild(go);
      topics.forEach(function (t, i) {
        var row = el('button', 'ap-topic'); row.type = 'button';
        var head2 = el('b', null, t.title);
        if (lastSeen && newer(t.since, lastSeen)) head2.appendChild(el('span', 'ap-new', T.isNew));
        row.appendChild(head2); row.appendChild(el('span', null, t.text));
        row.onclick = function () { tour(topics, i); };
        body.appendChild(row);
      });
      // ask: the question goes to the team with this page's help as its reference
      var ask = el('textarea', 'ap-text'); ask.rows = 2; ask.placeholder = T.askHelp;
      body.appendChild(ask);
      var who = el('div', 'ap-row');
      state.agents.forEach(function (a) {
        var b = el('button', 'ap-quiet'); b.type = 'button'; b.appendChild(avatar(a, 'sm')); b.appendChild(el('span', null, ' ' + a.label));
        b.onclick = function () { askAbout(a, ask.value, keys); };
        who.appendChild(b);
      });
      if (state.agents.length) { body.appendChild(el('p', 'ap-hint', T.askWho)); body.appendChild(who); }
      var top = topics.reduce(function (m, t) { return newer(t.since, m) ? t.since : m; }, lastSeen || '0');
      store('ap-help-seen', top);
    }).catch(function (e) { body.appendChild(el('p', 'ap-err', e.message)); });
  }
  function askAbout(a, question, keys) {
    if (!question.trim()) return;
    var f = focus() || {}, p = place(); for (var k in p) if (f[k] == null) f[k] = p[k];
    f.help = keys.join(',');
    var run = state.sessions.filter(function (s) { return s.agent_id === a.id; })[0];
    var start = run ? Promise.resolve({ id: run.session })
      : api('POST', '/api/sessions', { agent: a.id, topic: T.help + ': ' + (document.title || ''), place: f });
    start.then(function (j) { return api('POST', '/api/sessions/' + j.id + '/say', { text: question, focus: f }).then(function () { return refresh().then(function () { showSession(j.id); }); }); })
      .catch(function (e) { body.insertBefore(el('p', 'ap-err', e.message), body.firstChild); });
  }
  var spot = null, tip = null;
  function endTour() { if (spot) spot.remove(); if (tip) tip.remove(); spot = tip = null; document.removeEventListener('keydown', tourKeys); }
  function tourKeys(e) { if (e.key === 'Escape') endTour(); }
  function tour(topics, i) {
    endTour();
    var t = topics[i], n = document.querySelector('[data-help="' + t.key + '"]');
    if (!n) return;
    n.scrollIntoView({ block: 'center', behavior: 'smooth' });
    var r = n.getBoundingClientRect();
    spot = el('div', 'ap-spot');
    spot.style.top = (r.top - 6) + 'px'; spot.style.left = (r.left - 6) + 'px'; spot.style.width = (r.width + 12) + 'px'; spot.style.height = (r.height + 12) + 'px';
    tip = el('div', 'ap-tip');
    tip.appendChild(el('small', null, (i + 1) + ' / ' + topics.length));
    tip.appendChild(el('b', null, t.title)); tip.appendChild(el('p', null, t.text));
    var row = el('div', 'ap-row');
    if (i > 0) { var p = el('button', 'ap-quiet', T.prev); p.type = 'button'; p.onclick = function () { tour(topics, i - 1); }; row.appendChild(p); }
    var nx = el('button', 'ap-primary', i < topics.length - 1 ? T.next : T.done); nx.type = 'button';
    nx.onclick = function () { if (i < topics.length - 1) tour(topics, i + 1); else endTour(); };
    row.appendChild(nx); tip.appendChild(row);
    document.body.appendChild(spot); document.body.appendChild(tip);
    var below = r.bottom + 14, w = Math.min(340, window.innerWidth - 24);
    tip.style.width = w + 'px';
    tip.style.left = Math.max(12, Math.min(r.left, window.innerWidth - w - 12)) + 'px';
    tip.style.top = (below + 180 < window.innerHeight ? below : Math.max(12, r.top - 200)) + 'px';
    document.addEventListener('keydown', tourKeys);
    nx.focus();
  }
  helpBtn.addEventListener('click', function () { if (panel.hidden) open(true); showHelp(); });

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
