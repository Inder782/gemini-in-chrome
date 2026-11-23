(opts) => {
  // The "agent is here" layer: animated gradient ring, status badge, labelled cursor, click ripples, target highlight,
  // and a marked tab title + icon. Built with DOM/CSSOM calls only (no innerHTML) so strict Trusted Types sites allow it.
  if (window.top !== window) return;
  const o = Object.assign({name: 'Gemini', colors: ['#4285f4', '#9b72f2', '#f06292', '#ffb74d', '#34a853'],
                           chrome: true, active: true}, opts || {});
  if (window.__gic && document.getElementById('__gic_overlay')) {
    window.__gic.configure(o);
    return;
  }
  const px = (n) => n + 'px';
  const NS = 'http://www.w3.org/2000/svg';
  const root = document.createElement('div');
  root.id = '__gic_overlay';
  Object.assign(root.style, {position: 'fixed', left: 0, top: 0, width: '100vw', height: '100vh', pointerEvents: 'none',
                             zIndex: '2147483647'});

  // ---- gradient ring (crisp line + soft halo)
  const GRAD = 'linear-gradient(90deg,' + o.colors.concat(o.colors[0]).join(',') + ')';
  const ring = (blur, width, op) => {
    const d = document.createElement('div');
    Object.assign(d.style, {position: 'fixed', left: 0, top: 0, width: '100vw', height: '100vh', boxSizing: 'border-box',
                            padding: px(width), background: GRAD, backgroundSize: '300% 100%', opacity: String(op),
                            filter: blur ? 'blur(' + blur + 'px)' : 'none'});
    d.style.setProperty('-webkit-mask', 'linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)');
    d.style.setProperty('-webkit-mask-composite', 'xor');
    d.style.setProperty('mask-composite', 'exclude');
    d.animate([{backgroundPosition: '0% 0'}, {backgroundPosition: '300% 0'}], {duration: 5000, iterations: Infinity});
    return d;
  };
  const glow = document.createElement('div');
  glow.append(ring(16, 14, 0.4), ring(0, 4, 1));
  glow.animate([{transform: 'scale(1)'}, {transform: 'scale(1.004)'}, {transform: 'scale(1)'}],
               {duration: 2400, iterations: Infinity, easing: 'ease-in-out'});

  // ---- status badge: pulsing dot + text
  const badge = document.createElement('div');
  Object.assign(badge.style, {position: 'fixed', top: '12px', left: '50%', transform: 'translateX(-50%)',
    display: 'flex', alignItems: 'center', gap: '10px', background: 'rgba(24,24,27,.92)', color: '#fff',
    font: '600 14px/1.3 system-ui,-apple-system,Segoe UI,sans-serif', padding: '9px 18px 9px 14px', borderRadius: '999px',
    maxWidth: '72vw', boxShadow: '0 4px 18px rgba(0,0,0,.35), 0 0 0 1px rgba(255,255,255,.12)'});
  const dot = document.createElement('span');
  Object.assign(dot.style, {width: '9px', height: '9px', borderRadius: '50%', background: o.colors[0], flex: 'none',
                            boxShadow: '0 0 0 0 ' + o.colors[0]});
  dot.animate([{boxShadow: '0 0 0 0 rgba(66,133,244,.7)'}, {boxShadow: '0 0 0 9px rgba(66,133,244,0)'}],
              {duration: 1300, iterations: Infinity});
  const btext = document.createElement('span');
  Object.assign(btext.style, {whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'});
  btext.textContent = o.name + ' is working';
  badge.append(dot, btext);

  // ---- cursor + label
  const cur = document.createElementNS(NS, 'svg');
  cur.setAttribute('width', '34'); cur.setAttribute('height', '34'); cur.setAttribute('viewBox', '0 0 24 24');
  const path = document.createElementNS(NS, 'path');
  path.setAttribute('d', 'M3 2 L3 20 L8 15.5 L11.5 22 L14.5 20.7 L11 14.2 L17.5 14 Z');
  path.setAttribute('fill', o.colors[0]); path.setAttribute('stroke', '#fff'); path.setAttribute('stroke-width', '1.6');
  path.setAttribute('stroke-linejoin', 'round');
  cur.appendChild(path);
  Object.assign(cur.style, {position: 'fixed', left: 0, top: 0, transform: 'translate(-60px,-60px)',
                            transition: 'transform .08s linear', filter: 'drop-shadow(0 2px 4px rgba(0,0,0,.45))'});
  const tag = document.createElement('div');
  Object.assign(tag.style, {position: 'fixed', left: 0, top: 0, transform: 'translate(-90px,-90px)', color: '#fff',
    background: 'linear-gradient(90deg,' + o.colors[0] + ',' + o.colors[1] + ')', font: '700 12px/1 system-ui,sans-serif',
    padding: '5px 9px', borderRadius: '10px', transition: 'transform .08s linear',
    boxShadow: '0 2px 8px rgba(0,0,0,.3)'});
  tag.textContent = o.name;

  const marks = document.createElement('div');
  const decor = [glow, badge];
  root.append(glow, marks, badge, cur, tag);
  (document.body || document.documentElement).appendChild(root);

  // ---- tab title + icon so the agent's tab is easy to find
  let awake = false, observer = null, idleTimer = null, savedIcons = [], ourIcon = null;
  const prefix = () => '✨ ' + o.name + ' working · ';
  const markTitle = () => { if (awake && !document.title.startsWith(prefix())) document.title = prefix() + document.title; };
  const ICON = 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">' +
    '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="' + o.colors[0] + '"/>' +
    '<stop offset="1" stop-color="' + o.colors[2] + '"/></linearGradient></defs><circle cx="16" cy="16" r="15" fill="url(#g)"/>' +
    '<path d="M16 5l2.6 8.4L27 16l-8.4 2.6L16 27l-2.6-8.4L5 16l8.4-2.6z" fill="#fff"/></svg>');
  function wake() {
    if (!o.chrome) return;
    root.style.display = '';
    if (!awake) {
      awake = true;
      markTitle();
      try {
        observer = new MutationObserver(markTitle);
        observer.observe(document.querySelector('title') || document.head, {subtree: true, childList: true, characterData: true});
        savedIcons = Array.from(document.querySelectorAll('link[rel~="icon"]'));
        savedIcons.forEach((l) => l.remove());
        ourIcon = document.createElement('link'); ourIcon.rel = 'icon'; ourIcon.href = ICON;
        document.head.appendChild(ourIcon);
      } catch (e) { /* the title marker is a nicety */ }
    }
    clearTimeout(idleTimer);
    idleTimer = setTimeout(sleep, 90000);   // no calls for 90 s: stop looking busy
  }
  function sleep() {
    awake = false;
    root.style.display = 'none';
    if (observer) observer.disconnect();
    if (document.title.startsWith(prefix())) document.title = document.title.slice(prefix().length);
    try {
      if (ourIcon) ourIcon.remove();
      savedIcons.forEach((l) => document.head.appendChild(l));
    } catch (e) { /* ignore */ }
  }
  if (!o.chrome) { glow.style.display = 'none'; badge.style.display = 'none'; cur.style.display = 'none'; tag.style.display = 'none'; }

  document.addEventListener('mousemove', (e) => {
    cur.style.transform = 'translate(' + px(e.clientX) + ',' + px(e.clientY) + ')';
    tag.style.transform = 'translate(' + px(e.clientX + 28) + ',' + px(e.clientY + 26) + ')';
  }, true);
  document.addEventListener('mousedown', (e) => {
    if (!o.chrome) return;
    const rip = document.createElement('div');
    Object.assign(rip.style, {position: 'fixed', left: px(e.clientX - 20), top: px(e.clientY - 20), width: '40px', height: '40px',
      borderRadius: '50%', border: '3px solid ' + o.colors[0], background: 'rgba(66,133,244,.22)'});
    root.appendChild(rip);
    rip.animate([{transform: 'scale(.3)', opacity: 1}, {transform: 'scale(1.7)', opacity: 0}], {duration: 600})
       .onfinish = () => rip.remove();
  }, true);

  window.__gic = {
    configure(n) { o.name = n.name || o.name; },
    say(t) { btext.textContent = t; wake(); },
    mark(list) {
      marks.replaceChildren();
      for (const m of list) {
        const box = document.createElement('div');
        Object.assign(box.style, {position: 'fixed', left: px(m.l), top: px(m.t), width: px(m.w), height: px(m.h),
                                  boxSizing: 'border-box', border: '1.5px solid #e91e63'});
        const n = document.createElement('div');
        n.textContent = String(m.i);
        Object.assign(n.style, {position: 'absolute', left: '-1px', top: '-1px', background: '#e91e63', color: '#fff',
                                font: 'bold 11px/1 system-ui,sans-serif', padding: '2px 4px'});
        box.appendChild(n);
        marks.appendChild(box);
      }
    },
    clearMarks() { marks.replaceChildren(); },
    capture(on) { decor.forEach((d) => { d.style.visibility = on ? 'hidden' : 'visible'; }); },
    highlight(r) {
      if (!o.chrome) return;
      const h = document.createElement('div');
      Object.assign(h.style, {position: 'fixed', left: px(r.l - 4), top: px(r.t - 4), width: px(r.w + 8), height: px(r.h + 8),
        boxSizing: 'border-box', border: '2.5px solid ' + o.colors[1], borderRadius: '8px',
        boxShadow: '0 0 0 4px rgba(155,114,242,.25), 0 0 22px rgba(155,114,242,.6)'});
      root.appendChild(h);
      h.animate([{opacity: 0, transform: 'scale(1.12)'}, {opacity: 1, transform: 'scale(1)'}, {opacity: 1}, {opacity: 0}],
                {duration: 900, easing: 'ease-out'}).onfinish = () => h.remove();
    },
  };
  if (o.active) wake(); else root.style.display = 'none';
}
