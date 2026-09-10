/* Original examples only. All diffs come from the Python comparison engine. */
"use strict";
const app = document.getElementById("app");
const repo = "https://github.com/ppplkmvvb/skillvariants";
const esc = (value) => String(value ?? "").replace(/[&<>"']/g,
  (char) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[char]));
let dataPromise;
let routeVersion = 0;
let activeExample = null;
let view = "paired";

function sourceUrl(path) {
  const url = new URL(`${repo}/blob/main/${path.split("/").map(encodeURIComponent).join("/")}`);
  if (url.protocol !== "https:") throw new Error("Unsupported source URL");
  return url.href;
}

function validateData(data) {
  if (data?.schema_version !== "2" || data.provenance?.kind !== "original_illustrative_examples"
      || !Array.isArray(data.examples) || data.examples.length === 0) {
    throw new Error("The example export has an unsupported format.");
  }
  const ids = new Set();
  for (const example of data.examples) {
    if (!/^[a-z-]+$/.test(example.id) || ids.has(example.id)
        || !["ADDED", "PRESERVED", "REVERSED"].includes(example.direction)
        || ![example.title, example.short_title, example.observation, example.interpretation,
          example.maintainer_question].every((s) => typeof s === "string" && s.length > 0)
        || !Array.isArray(example.citations) || !Array.isArray(example.comparison?.hunks)
        || typeof example.comparison.unified_diff !== "string"
        || example.comparison.truncation?.truncated !== false) {
      throw new Error("The example export is incomplete. Regenerate it from the original sources.");
    }
    ids.add(example.id);
    for (const side of ["a", "b"]) {
      const source = example.sources?.[side];
      if (typeof source?.content !== "string" || !/^[a-f0-9]{64}$/.test(source.raw_sha256)
          || typeof source.path !== "string" || !source.path.startsWith("examples/approval-gate/")) {
        throw new Error("Source identity is missing from an example.");
      }
    }
    for (const hunk of example.comparison.hunks) {
      if (!/^hunk-\d+$/.test(hunk.hunk_id) || !Array.isArray(hunk.changes)) throw new Error("Invalid evidence hunk.");
      for (const side of ["a", "b"]) {
        if (!Array.isArray(hunk[side]?.lines) || !hunk[side].lines.every((line) =>
          Number.isInteger(line.line_number) && line.line_number > 0 && typeof line.text === "string")) {
          throw new Error("Invalid source line in paired evidence.");
        }
      }
    }
    if (example.citations.length === 0) throw new Error("An example has no source citation.");
    for (const citation of example.citations) {
      const hunk = example.comparison.hunks.find((entry) => entry.hunk_id === citation?.hunk_id);
      if (!hunk) throw new Error("A citation points to missing evidence.");
      for (const side of ["a", "b"]) {
        const numbers = citation[`${side}_lines`];
        const available = new Set(hunk[side].lines.map((line) => line.line_number));
        if (!Array.isArray(numbers) || numbers.length === 0 || !numbers.every((n) =>
          Number.isInteger(n) && available.has(n))) {
          throw new Error("A source citation has missing or invalid line numbers.");
        }
      }
    }
  }
  return data;
}

function loadData() {
  if (!dataPromise) dataPromise = fetch("data/examples.json", {cache: "no-cache"}).then((response) => {
    if (!response.ok) throw new Error(`Example data could not be loaded (HTTP ${response.status}).`);
    return response.json();
  }).then(validateData);
  return dataPromise;
}

function badge(example) {
  return `<span class="badge ${example.id === "reversed" ? "reversed" : ""}">${esc(example.direction)}</span>`;
}

function home(data) {
  const reversed = data.examples.find((example) => example.id === "reversed") || data.examples[0];
  const citation = reversed.citations[0];
  const proofLine = (side) => reversed.sources[side].content.split(/\r?\n/)[citation[`${side}_lines`][0] - 1];
  return `<section class="hero">
    <div><p class="eyebrow">A reading tool for Skill maintainers</p>
      <h1>See the rule.<br><em>Read the difference.</em></h1>
      <p class="hero-copy">Compare Agent Skills before adapting them. Find what changed, check both sources, and decide which instructions belong in your workflow.</p>
      <div class="actions"><a class="button primary" href="#/example/reversed">Inspect an example <span aria-hidden="true">→</span></a>
        <a class="button" href="${repo}#quickstart">Compare your Skills</a></div>
    </div>
    <div class="hero-proof"><div class="proof-heading"><span>SKILL.md <span aria-hidden="true">↔</span> SKILL.md</span><span>ILLUSTRATIVE EXAMPLE</span></div>
      <div class="proof-body"><h2>One short edit.<br>A different approval order.</h2>
        <div class="proof-line before"><small>A / Target · line ${citation.a_lines[0]}</small><code>${esc(proofLine("a"))}</code></div>
        <div class="proof-line after"><small>B / Variant · line ${citation.b_lines[0]}</small><code>${esc(proofLine("b"))}</code></div>
        <p class="proof-note">Similar wording can hide a consequential change. Read the pair.</p></div>
    </div>
  </section>
  <section aria-labelledby="examples-title"><div class="section-heading"><h2 id="examples-title">Three changes. Three different readings.</h2><p>Original examples · complete source evidence</p></div>
    <div class="example-list">${data.examples.map((example, index) => `<a class="example-card" href="#/example/${example.id}">
      <div class="case-top"><span class="case-number">CASE 0${index + 1}</span>${badge(example)}</div>
      <h3>${esc(example.short_title)}</h3><p>${esc(example.observation)}</p>
      <span class="card-cta">Read the comparison <span aria-hidden="true">↗</span></span></a>`).join("")}</div>
  </section>
  <section class="method" aria-labelledby="method-title"><div><p class="eyebrow">How to read a comparison</p><h2 id="method-title">Evidence first.<br>Interpretation second.</h2>
    <p>These small Skills were authored for this project. They demonstrate a method; they are not sampled GitHub adaptations or adoption statistics.</p></div>
    <ol><li><strong>Start with the actual change.</strong><br>Paired lines show the target and variant together. Complete sources and the full diff are one click away.</li>
    <li><strong>Keep claims separate from observations.</strong><br>Our editorial interpretation explains a possible meaning. It is not a measurement of agent behavior.</li>
    <li><strong>Reproduce it on your files.</strong><br>The CLI computes differences and source hashes. You decide whether the adaptation is useful.</li></ol></section>`;
}

function lineRange(numbers) {
  return numbers.length === 1 ? `L${numbers[0]}` : `L${numbers[0]}–${numbers[numbers.length - 1]}`;
}

function changedLine(hunk, side, lineNumber) {
  return hunk.changes.some((change) => change.tag !== "equal"
    && lineNumber >= change[`${side}_start_line`]
    && lineNumber < change[`${side}_start_line`] + change[`${side}_line_count`]);
}

function sourcePane(example, side, lines, hunk = null) {
  return `<section class="source-pane" aria-label="${side === "a" ? "Target" : "Variant"} source">
    <div class="source-title"><strong>${side === "a" ? "A / Target" : "B / Variant"}</strong><span>SKILL.md</span></div>
    <div class="source-lines">${lines.map((line) => `<div class="source-line ${hunk && changedLine(hunk, side, line.line_number) ? `changed-${side}` : ""}">
      <span class="line-number" aria-label="line ${line.line_number}">${line.line_number}</span><span class="line-content">${esc(line.text) || " "}</span></div>`).join("")}</div></section>`;
}

function evidence(example) {
  if (view === "diff") return `<pre class="unified" aria-label="Complete unified diff">${esc(example.comparison.unified_diff) || "No textual differences."}</pre>`;
  if (view === "sources") {
    return `<div class="source-pair">${["a", "b"].map((side) => {
      const lines = example.sources[side].content.split(/\r?\n/);
      if (lines[lines.length - 1] === "") lines.pop();
      return sourcePane(example, side, lines.map((text, index) => ({text, line_number: index + 1})));
    }).join("")}</div>`;
  }
  return example.comparison.hunks.map((hunk) => `<div class="hunk"><div class="hunk-caption">${esc(hunk.hunk_id)} · paired context from both sources</div>
    <div class="source-pair">${["a", "b"].map((side) => sourcePane(example, side, hunk[side].lines, hunk)).join("")}</div></div>`).join("") || "<p>No textual differences.</p>";
}

function detail(data, example) {
  const command = `skillvariants compare ${example.sources.a.path} ${example.sources.b.path} --json`;
  return `<div class="workspace"><aside class="sidebar"><a class="back" href="#/">← All examples</a><p class="eyebrow">The approval checkpoint</p>
    <nav class="case-nav" aria-label="Comparison examples">${data.examples.map((entry, i) => `<a href="#/example/${entry.id}" ${entry.id === example.id ? 'aria-current="page"' : ""}><span class="case-number">0${i + 1}</span><span>${esc(entry.short_title)}</span></a>`).join("")}</nav>
    <p class="sidebar-note">Original illustrative examples.<br><br>Both full sources are included. The explanation is an editorial reading, not an automated semantic score.</p></aside>
    <article class="detail"><p class="eyebrow">Original illustrative example / ${esc(example.direction.toLowerCase())}</p><h1>${esc(example.title)}</h1>
      <p class="observation">${esc(example.observation)}</p>
      <div class="citation-row"><span>Evidence:</span>${example.citations.map((c) => `<button type="button" class="citation" data-citation="${esc(c.hunk_id)}">Target ${lineRange(c.a_lines)} ↔ Variant ${lineRange(c.b_lines)}</button>`).join("")}</div>
      <div class="annotation"><span>INTERPRETATION</span><p>${esc(example.interpretation)}</p></div>
      <div class="annotation question"><span>YOUR DECISION</span><p>${esc(example.maintainer_question)}</p></div>
      <section aria-labelledby="evidence-title"><div class="evidence-heading"><h2 id="evidence-title">Inspect the source</h2><span>All hunks included · no truncation</span></div>
        <div class="view-switch" role="group" aria-label="Evidence view">${[["paired", "Paired evidence"], ["sources", "Complete sources"], ["diff", "Unified diff"]].map(([key, title]) => `<button type="button" data-view="${key}" aria-pressed="${view === key}">${title}</button>`).join("")}</div>
        <div id="evidence-panel">${evidence(example)}</div>
        <p class="legend"><span class="swatch red" aria-hidden="true"></span>Target text removed or replaced <span class="swatch green" aria-hidden="true"></span>Variant text inserted or replaced</p>
      </section>
      <details class="hashes"><summary>Source identity &amp; reproducibility</summary><p>SHA-256 identifies the exact UTF-8 source contents. These examples are generated offline using the same comparison engine as the CLI.</p>
        <dl>${["a", "b"].map((side) => `<dt>${side === "a" ? "A / Target" : "B / Variant"}</dt><dd><a href="${esc(sourceUrl(example.sources[side].path))}">${esc(example.sources[side].path)}</a><code>SHA-256 ${example.sources[side].raw_sha256}</code></dd>`).join("")}</dl>
        <p><a href="data/examples.json" download>Download the complete example evidence (JSON)</a></p></details>
      <section class="reproduce" aria-labelledby="reproduce-title"><h2 id="reproduce-title">Try this comparison yourself</h2>
        <p>From a checkout of the repository with SkillVariants installed. No GitHub token needed for these local files.</p>
        <div class="command"><code id="compare-command">${esc(command)}</code><button type="button" class="copy" data-copy>Copy</button></div><div class="copy-status" role="status"></div>
        <p><a href="${repo}#quickstart">Install the CLI and compare your own Skills ↗</a></p></section>
    </article></div>`;
}

function errorPage(title, message, retry = false) {
  return `<section class="error-page"><p class="eyebrow">Comparison explorer</p><h1>${esc(title)}</h1><p>${esc(message)}</p>
    <div class="actions"><a class="button" href="#/">Back to examples</a>${retry ? '<button type="button" class="button primary" data-retry>Retry loading</button>' : ""}</div></section>`;
}

async function route() {
  const version = ++routeVersion;
  const hash = window.location.hash;
  if (hash === "#main-content") { document.getElementById("main-content").focus(); return; }
  activeExample = null;
  const path = hash.replace(/^#\/?/, "");
  const match = /^example\/([a-z-]+)$/.exec(path);
  if (path && !match) {
    app.innerHTML = errorPage("This page is not available", "Choose one of the current illustrative examples. Historical study and motif links are no longer presented as validated evidence.");
    document.title = "Page not found — SkillVariants";
    return;
  }
  app.innerHTML = '<p class="loading">Loading comparison evidence…</p>';
  try {
    const data = await loadData();
    if (version !== routeVersion) return;
    if (!match) {
      app.innerHTML = home(data);
      document.title = "SkillVariants — inspect the difference";
    } else {
      const example = data.examples.find((entry) => entry.id === match[1]);
      if (!example) {
        app.innerHTML = errorPage("Example not found", "This example does not exist in the current export. Choose an example from the index.");
        document.title = "Example not found — SkillVariants";
        return;
      }
      activeExample = example;
      view = "paired";
      app.innerHTML = detail(data, example);
      document.title = `${example.short_title} — SkillVariants`;
    }
  } catch (error) {
    if (version !== routeVersion) return;
    app.innerHTML = errorPage("We couldn't load the examples", error instanceof Error ? error.message : "The example data is unavailable.", true);
    document.title = "Examples unavailable — SkillVariants";
  }
}

app.addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  if (button.hasAttribute("data-retry")) { dataPromise = null; await route(); return; }
  if (button.dataset.view && activeExample) {
    view = button.dataset.view;
    app.querySelectorAll("[data-view]").forEach((control) => control.setAttribute("aria-pressed", String(control.dataset.view === view)));
    document.getElementById("evidence-panel").innerHTML = evidence(activeExample);
  }
  if (button.dataset.citation && activeExample) {
    view = "paired";
    app.querySelectorAll("[data-view]").forEach((control) => control.setAttribute("aria-pressed", String(control.dataset.view === view)));
    document.getElementById("evidence-panel").innerHTML = evidence(activeExample);
    document.getElementById("evidence-title").scrollIntoView({block: "start"});
  }
  if (button.hasAttribute("data-copy")) {
    const status = app.querySelector(".copy-status");
    try {
      await navigator.clipboard.writeText(document.getElementById("compare-command").textContent);
      status.textContent = "Command copied.";
    } catch (error) {
      status.textContent = "Clipboard is unavailable. Select and copy the command above.";
    }
  }
});

window.addEventListener("hashchange", () => { window.scrollTo(0, 0); route(); });
route();
