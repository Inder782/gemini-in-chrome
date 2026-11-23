(max) => {
  // Lists the clickable / typeable elements that are really visible on screen, including inside shadow DOM.
  const SEL = 'a[href],button,input,textarea,select,summary,[role=button],[role=radio],[role=checkbox],[role=tab],' +
    '[role=menuitem],[role=option],[role=switch],[role=link],[role=textbox],[role=combobox],[contenteditable=""],' +
    '[contenteditable=true],[tabindex]:not([tabindex="-1"]),tp-yt-paper-radio-button,tp-yt-paper-checkbox,' +
    'ytcp-button,tp-yt-paper-item';
  const found = [];
  const walk = (root) => {
    for (const el of root.children || []) {
      if (el.id === '__gic_overlay') continue;
      if (el.matches && el.matches(SEL)) found.push(el);
      if (el.shadowRoot) walk(el.shadowRoot);
      walk(el);
    }
  };
  walk(document.documentElement);
  const deepAt = (x, y) => {
    let el = document.elementFromPoint(x, y);
    while (el && el.shadowRoot) {
      const inner = el.shadowRoot.elementFromPoint(x, y);
      if (!inner || inner === el) break;
      el = inner;
    }
    return el;
  };
  const related = (a, b) => {
    for (let n = b; n; n = n.parentNode || n.host) if (n === a) return true;
    for (let n = a; n; n = n.parentNode || n.host) if (n === b) return true;
    return false;
  };
  const out = [], seen = [];
  for (const el of found) {
    const r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) continue;
    if (r.bottom < 0 || r.right < 0 || r.top > innerHeight || r.left > innerWidth) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity === 0) continue;
    const x = Math.round(Math.min(Math.max(r.left + r.width / 2, 1), innerWidth - 1));
    const y = Math.round(Math.min(Math.max(r.top + r.height / 2, 1), innerHeight - 1));
    const hit = deepAt(x, y);
    if (!hit || !related(el, hit)) continue;              // covered by a dialog or overlay
    const lab = el.labels && el.labels[0] ? el.labels[0].innerText : '';
    const label = (el.getAttribute('aria-label') || el.innerText || lab || el.placeholder || el.value ||
                   el.title || el.getAttribute('name') || el.id || '').replace(/\s+/g, ' ').trim().slice(0, 70);
    if (seen.some(s => Math.abs(s.x - x) < 4 && Math.abs(s.y - y) < 4 && s.label === label)) continue;
    seen.push({x, y, label});
    const flags = [];
    if (el.disabled || el.getAttribute('aria-disabled') === 'true') flags.push('disabled');
    if (el.checked || el.getAttribute('aria-checked') === 'true' || el.hasAttribute('checked')) flags.push('checked');
    const val = ('value' in el && el.type !== 'file' && el.tagName !== 'BUTTON') ? String(el.value || '').slice(0, 80)
              : (el.isContentEditable ? (el.innerText || '').trim().slice(0, 80) : '');
    out.push({i: out.length + 1, tag: el.tagName.toLowerCase(), type: el.type || '', role: el.getAttribute('role') || '',
              label, value: val, flags, x, y, l: Math.round(r.left), t: Math.round(r.top),
              w: Math.round(r.width), h: Math.round(r.height)});
    if (out.length >= max) break;
  }
  const doc = document.documentElement;
  return {url: location.href, title: document.title, scrollY: Math.round(scrollY), scrollH: doc.scrollHeight,
          viewH: innerHeight, elements: out};
}
