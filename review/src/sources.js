// Sources section: the key sources (hand-picked, with why each matters) and the full register of every URL the
// repository cites (analysis/sources.py -> analysis/sources.json, embedded as #sourcesData). Search filters both;
// the register is grouped by topic in disclosures so the page stays short until a group is opened.
const Sources = (() => {
  let D = null, built = false;
  const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const label = e => e.title || e.context || e.domain;
  const files = e => e.files.slice(0, 3).map(f => `<code>${esc(f)}</code>`).join(', ') + (e.files.length > 3 ? ` +${e.files.length - 3} more` : '');
  const date = e => e.checked ? `${esc(e.checked)}${e.checkedFrom === 'file' ? '<span class="srcf" title="Date stated once for all links in the citing file">*</span>' : ''}` : '—';
  // link health from the last automated check: dead links offer the archived copy when one exists
  function health(e) {
    const l = e.link; if (!l) return '';
    if (l.status === 'dead') return ` <span class="chip fail">dead link${l.code ? ' ' + l.code : ''}</span>${l.archive ? ` <a class="srcarch" href="${esc(l.archive)}" rel="noopener" target="_blank">archived copy</a>` : ''}`;
    if (l.status === 'unverified') return ` <span class="chip open" title="The site refused an automated check${l.code ? ' (HTTP ' + l.code + ')' : ''}; it may work in a browser">not verified</span>`;
    return '';
  }
  function row(e) {
    return `<tr data-q="${esc((label(e) + ' ' + e.url + ' ' + e.files.join(' ')).toLowerCase())}" data-link="${e.link ? e.link.status : ''}"><td><a href="${esc(e.url)}" rel="noopener" target="_blank">${esc(label(e))}</a>${health(e)}<div class="srcu">${esc(e.domain)}</div></td><td class="n">${date(e)}</td><td>${files(e)}</td></tr>`;
  }
  function build() {
    const el = document.getElementById('sourcesData'); if (!el) return;
    try { D = JSON.parse(el.textContent); } catch (err) { return; }
    const key = document.getElementById('srcKey'), reg = document.getElementById('srcReg'), q = document.getElementById('srcQ'), n = document.getElementById('srcCount');
    if (key) key.querySelector('tbody').innerHTML = D.key.map(k => {
      const e = D.sources.find(s => s.url === k.url) || { url: k.url, files: [], domain: '' };
      return `<tr data-q="${esc((k.name + ' ' + k.why + ' ' + k.url).toLowerCase())}" data-link="${e.link ? e.link.status : ''}"><td><a href="${esc(k.url)}" rel="noopener" target="_blank">${esc(k.name)}</a>${health(e)}<div class="srcu">${esc(k.topic)}</div></td><td>${esc(k.why)}</td><td class="n">${date(e)}</td></tr>`;
    }).join('');
    if (reg) reg.innerHTML = D.categories.map(c => {
      const rows = D.sources.filter(e => e.category === c);
      return `<details class="srcgrp"><summary><span>${esc(c)}</span> <span class="srcn">${rows.length}</span></summary><div class="tbl"><table><thead><tr><th>Source</th><th class="n">Checked</th><th>Cited in</th></tr></thead><tbody>${rows.map(row).join('')}</tbody></table></div></details>`;
    }).join('');
    if (n) n.textContent = D.count;
    const lc = D.linkCheck, ls = document.getElementById('srcLinks');
    if (ls && lc && lc.date) ls.innerHTML = `Every link was checked automatically on ${esc(lc.date)}: ${lc.counts.ok} open, <b>${lc.counts.dead} dead</b> (marked, with an archived copy where one exists), ${lc.counts.unverified} could not be verified because the site blocks automated checks (they usually open in a browser).`;
    const dd = document.getElementById('srcDead');
    const apply = () => {
      const t = q ? q.value.trim().toLowerCase() : '', only = dd && dd.checked; let shown = 0;
      document.querySelectorAll('#srcKey tbody tr, #srcReg tbody tr').forEach(tr => { const on = (!t || tr.dataset.q.includes(t)) && (!only || tr.dataset.link === 'dead'); tr.hidden = !on; if (on && tr.closest('#srcReg')) shown++; });
      document.querySelectorAll('#srcReg details').forEach(d => { const any = d.querySelector('tbody tr:not([hidden])'); d.hidden = !any; if (t || only) d.open = !!any; });
      const st = document.getElementById('srcStatus'); if (st) st.textContent = (t || only) ? `${shown} of ${D.count} sources match` : '';
    };
    if (q) q.addEventListener('input', apply); if (dd) dd.addEventListener('change', apply);
    built = true;
  }
  return { redraw() { if (!built) build(); } };
})();
