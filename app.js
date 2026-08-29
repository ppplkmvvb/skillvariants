/* SkillVariants explorer — static, precomputed data only. */
const FAMILIES = ["systematic-debugging", "frontend-design", "brainstorming"];
const FAMILY_TITLES = {
  "systematic-debugging": "systematic-debugging",
  "frontend-design": "frontend-design",
  "brainstorming": "brainstorming",
};
const $app = document.getElementById("app");
const esc = (s) => String(s ?? "").replace(/[&<>"']/g,
  (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

async function loadFamily(family) {
  const res = await fetch(`data/${family}.json`);
  if (!res.ok) throw new Error(`data load failed: ${family}`);
  return res.json();
}

function home() {
  $app.innerHTML = `
    <div class="hero">
      <h1>SkillVariants</h1>
      <p class="sub">See recurring ways developers adapt Agent Skills —
      backed by real GitHub implementations.</p>
      <div class="ctas">
        <a class="btn primary" href="#studies">Explore real Skill studies</a>
        <a class="btn" href="https://github.com/ppplkmvvb/skillvariants/blob/main/skills/skillvariants/SKILL.md">Use from your Agent</a>
        <a class="btn" href="https://github.com/ppplkmvvb/skillvariants#try-the-cli">Use the CLI</a>
      </div>
      <p class="muted">Deterministic GitHub evidence · agent-powered analysis ·
      no LLM in the engine.</p>
    </div>
    <h2 class="sec" id="studies">Real Skill studies</h2>
    <div class="cards" id="cards"><p class="muted">Loading studies…</p></div>`;
  const cards = document.getElementById("cards");
  Promise.all(FAMILIES.map(loadFamily)).then((studies) => {
    cards.innerHTML = studies.map((s) => `
      <div class="card">
        <h3><a href="#study/${s.family}">${esc(FAMILY_TITLES[s.family])}</a></h3>
        <p class="stats">
          ${s.summary.related_variant_count} related variants ·
          ${s.summary.mutation_group_count} mutation groups ·
          ${s.summary.accepted_motif_count} recurring adaptations
        </p>
        <p class="muted" style="font-size:13.5px">Target:
          <a href="${esc(s.target.direct_skill_url)}">${esc(s.target.repository)}/${esc(s.target.path)}</a></p>
        <a class="btn" href="#study/${s.family}">Open study</a>
      </div>`).join("");
  }).catch(() => { cards.innerHTML = "<p>Failed to load study data.</p>"; });
}

function study(family) {
  $app.innerHTML = "<p class='muted'>Loading…</p>";
  loadFamily(family).then((s) => {
    const t = s.target;
    $app.innerHTML = `
      <a class="back" href="#/">← All studies</a>
      <div class="hero"><h1>${esc(t.name)}</h1>
        <p class="sub">Source:
          <a href="${esc(t.direct_skill_url)}">${esc(t.repository)}/${esc(t.path)}</a>
          (ref <code>${esc(t.ref)}</code>)</p></div>
      <div class="card"><p class="stats">
        ${s.summary.related_variant_count} related variants ·
        ${s.summary.mutation_group_count} mutation groups ·
        ${s.summary.exact_copy_count} exact copies collapsed ·
        ${s.summary.accepted_motif_count} recurring adaptations</p>
        <p class="muted" style="font-size:13px">${esc(s.capture_note)}</p></div>
      <h2 class="sec">Recurring adaptations</h2>
      ${s.accepted_motifs.map((m, i) => `
        <div class="motif-card">
          <h3><a href="#motif/${family}/${i}">${esc(m.display_name)}</a></h3>
          <p class="counts">Observed across ${m.group_count} mutation groups
            in ${m.repository_count} repositories ·
            ${m.representatives.length} representative implementations shown</p>
          <p>${esc(m.what_changed)}</p>
          <p class="muted">(interpretation) ${esc(m.interpretation)}</p>
          <span class="label">${esc(m.label)}</span>
          <a class="btn" href="#motif/${family}/${i}">Explore</a>
        </div>`).join("")}`;
  }).catch(() => { $app.innerHTML = "<p>Failed to load study.</p>"; });
}

function motifDetail(family, index) {
  $app.innerHTML = "<p class='muted'>Loading…</p>";
  loadFamily(family).then((s) => {
    const m = s.accepted_motifs[index];
    if (!m) { $app.innerHTML = "<p>Motif not found.</p>"; return; }
    const sig = m.behavior_signature || {};
    $app.innerHTML = `
      <a class="back" href="#study/${family}">← ${esc(FAMILY_TITLES[family])}</a>
      <div class="hero"><h1>${esc(m.display_name)}</h1>
        <p class="sub">Observed across ${m.group_count} mutation groups in
        ${m.repository_count} repositories.</p></div>
      <h2 class="sec">Strict invariant</h2>
      <div class="invariant">${esc(m.invariant)}</div>
      <h2 class="sec">Behavior signature</h2>
      <p>
        <span class="label">trigger: ${esc(sig.trigger ?? "—")}</span>
        <span class="label">action: ${esc(sig.action ?? "—")}</span>
        <span class="label">object: ${esc(sig.object ?? "—")}</span>
        <span class="label">outcome: ${esc(sig.outcome ?? "—")}</span>
      </p>
      <h2 class="sec">What changed</h2><p>${esc(m.what_changed)}</p>
      <h2 class="sec">Why it may matter</h2>
      <div class="note">(interpretation) ${esc(m.interpretation)}</div>
      <h2 class="sec">Tradeoff</h2>
      <div class="note">(interpretation) ${esc(m.tradeoff)}</div>
      <h2 class="sec">Representative implementations</h2>
      <ol class="reps">
        ${m.representatives.map((r, ri) => `
          <li>
            <a href="${esc(r.direct_skill_url)}">${esc(r.repository)}/${esc(r.path)}</a>
            ${r.source_available === false
              ? `<span class="label">source changed since capture</span>`
              : `<a class="btn" href="#compare/${family}/${index}/${ri}">Compare with target</a>`}
            ${r.compare ? compareSummary(r.compare) : ""}
          </li>`).join("")}
      </ol>`;
  });
}

function compareSummary(compare) {
  const sim = compare?.similarity;
  if (!sim) return "";
  return `<p class="counts">similarity ${Math.round((sim.score ?? 0) * 100)}% ·
    length ${esc(compare.length_change ?? "")} ·
    mutation: ${esc(compare.detected_mutation ?? "n/a")}</p>`;
}

function compareView(family, motifIndex, repIndex) {
  $app.innerHTML = "<p class='muted'>Loading…</p>";
  loadFamily(family).then((s) => {
    const m = s.accepted_motifs[motifIndex];
    const rep = m?.representatives?.[repIndex];
    const cmp = rep?.compare;
    if (!m || !rep || !cmp) { $app.innerHTML = "<p>Compare data not found.</p>"; return; }
    const targetUrl = s.target.direct_skill_url;
    const lines = (cmp.text_diff_brief || []);
    $app.innerHTML = `
      <a class="back" href="#motif/${family}/${motifIndex}">← ${esc(m.display_name)}</a>
      <div class="hero"><h1>Compare with target</h1>
        <p class="sub">
          Target: <a href="${esc(targetUrl)}">${esc(s.target.repository)}/${esc(s.target.path)}</a><br>
          Variant: <a href="${esc(rep.direct_skill_url)}">${esc(rep.repository)}/${esc(rep.path)}</a></p></div>
      <div class="card"><p class="stats">
        similarity ${Math.round((cmp.similarity?.score ?? 0) * 100)}% ·
        length ${esc(cmp.length_change ?? "")} ·
        headings ${esc(cmp.workflow_headings ?? "")} ·
        mutation: ${esc(cmp.detected_mutation ?? cmp.primary ?? "n/a")}</p></div>
      <h2 class="sec">Text diff (brief)</h2>
      <div class="diff">${lines.map((l) => {
        const cls = l.startsWith("+") ? "add" : l.startsWith("-") ? "del" : "";
        return `<div class="line ${cls}">${esc(l)}</div>`;
      }).join("")}</div>
      <h2 class="sec">Sources</h2>
      <ul class="reps">
        <li>Target: <a href="${esc(targetUrl)}">${esc(targetUrl)}</a></li>
        <li>Variant: <a href="${esc(rep.direct_skill_url)}">${esc(rep.direct_skill_url)}</a></li>
      </ul>`;
  });
}

function route() {
  const hash = location.hash.replace(/^#/, "") || "/";
  const parts = hash.split("/").filter(Boolean);
  if (parts.length === 0 || parts[0] === "studies") return home();
  if (parts[0] === "study" && parts[1]) return study(parts[1]);
  if (parts[0] === "motif" && parts[2] !== undefined)
    return motifDetail(parts[1], Number(parts[2]));
  if (parts[0] === "compare" && parts[3] !== undefined)
    return compareView(parts[1], Number(parts[2]), Number(parts[3]));
  return home();
}
window.addEventListener("hashchange", route);
route();
