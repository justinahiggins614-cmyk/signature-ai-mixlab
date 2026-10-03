#!/usr/bin/env node
/* Functional exercise harness for the Mix Lab shipped page code.
   Drives the REAL functions from index.html's inline engine block +
   js/jah-talk-fallback.js against the REAL shipped data (base-ais.json,
   wordai-idx.json, mixes.idx.json.gz, chunk files), with a stub DOM.
   Run: node code/qa/test_functional.js   (exit 0 = all pass)
*/
"use strict";
const fs = require("fs"), path = require("path"), vm = require("vm"),
      zlib = require("zlib"), crypto = require("crypto"),
      { execFileSync } = require("child_process");
const ROOT = path.resolve(__dirname, "..", "..");

let failures = 0, passes = 0;
function ok(name, cond, extra) {
  if (cond) { passes++; console.log("PASS:", name); }
  else { failures++; console.log("FAIL:", name, extra === undefined ? "" : String(extra).slice(0, 300)); }
}

/* ---------- stub DOM ---------- */
function mkEl() {
  return {
    children: [], style: {}, dataset: {},
    classList: { add() {}, remove() {}, contains() { return false; } },
    textContent: "", innerHTML: "", value: "", disabled: false, onclick: null,
    scrollTop: 0, scrollHeight: 0, tagName: "",
    scrollIntoView() {}, appendChild(c) { this.children.push(c); return c; },
    remove() {}, click() {}, select() {}, focus() {},
    setAttribute() {}, getAttribute() { return null; }, removeAttribute() {},
    querySelector() { return null; }, querySelectorAll() { return []; },
    addEventListener() {}, removeEventListener() {},
  };
}
const els = {};
const localStore = {};
const sandbox = {
  console, setTimeout, clearTimeout, setInterval, clearInterval, Promise,
  Math, JSON, Object, Array, String, Number, Boolean, RegExp, Date, Error,
  isNaN, parseInt, parseFloat, encodeURIComponent, decodeURIComponent,
  TextEncoder, AbortController, DecompressionStream,
  URLSearchParams, Blob, Response, Request, Headers,
  URL: { createObjectURL() { return "blob:stub"; }, revokeObjectURL() {} },
  crypto: crypto.webcrypto,
  document: {
    getElementById(id) { if (!els[id]) els[id] = mkEl(); return els[id]; },
    createElement(t) { const e = mkEl(); e.tagName = t; return e; },
    querySelector() { return null; }, querySelectorAll() { return []; },
    addEventListener() {}, removeEventListener() {},
    head: mkEl(), body: mkEl(), documentElement: mkEl(), title: "",
  },
  localStorage: {
    getItem(k) { return k in localStore ? localStore[k] : null; },
    setItem(k, v) { localStore[k] = String(v); },
    removeItem(k) { delete localStore[k]; },
  },
  navigator: { clipboard: { writeText(t) { sandbox.__clip = t; return Promise.resolve(t); } } },
  history: { replaceState() {} },
  location: { search: "", pathname: "/" },
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
/* fetch stub: serves repo files (incl. .gz chunks) as web Responses */
sandbox.fetch = async function (url) {
  const p = path.join(ROOT, String(url));
  if (!fs.existsSync(p)) return { ok: false, status: 404, body: null, text: async () => "" };
  const buf = fs.readFileSync(p);
  const r = new Response(new Blob([buf]), { status: 200 });
  return r;
};
vm.createContext(sandbox);

function runFile(p) {
  vm.runInContext(fs.readFileSync(p, "utf8"), sandbox, { filename: p });
}
function runSrc(src, name) {
  vm.runInContext(src, sandbox, { filename: name });
}

/* ---------- load shipped code ---------- */
runFile(path.join(ROOT, "js", "jah-talk-fallback.js"));
const html = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");
const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const engineSrc = blocks.find(b => b.includes("hybridSlots"));
if (!engineSrc) { console.log("FAIL: engine block not found in index.html"); process.exit(1); }
runSrc(engineSrc, "index.html#engine");
const tourSrc = blocks.find(b => b.includes("jah-tour-seen-mixlab"));
if (!tourSrc) { console.log("FAIL: tour block not found in index.html"); process.exit(1); }
runSrc(tourSrc, "index.html#tour");

/* ---------- load real data into the page's globals ---------- */
runSrc("BASE=" + fs.readFileSync(path.join(ROOT, "data", "base-ais.json"), "utf8") + ";", "base");
const wordaiArr = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "wordai-idx.json"), "utf8"));
const wmap = {}; wordaiArr.forEach(e => { wmap[e[1]] = e[0]; });
runSrc("WORDAIMAP=" + JSON.stringify(wmap) + ";WORDAI=true;", "wordaimap");
const idx = JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(ROOT, "data", "index", "mixes.idx.json.gz"))).toString());
runSrc("SEEDIDX=" + JSON.stringify(idx) + ";", "seedidx");
runSrc("APIINFO=" + JSON.stringify({ counts: { seeded_hybrids: idx.length }, _live: true }) + ";", "apiinfo");

const S = (src) => vm.runInContext(src, sandbox);

async function main() {
  /* ===== 1. forge input validation (items 6,7,8) ===== */
  const fw = (v) => { els["forgenum"] = mkEl(); els["forgenum"].value = v; return S("forgeWanted()"); };
  ok("forge: empty -> random", (() => { const r = fw(""); return r.ok && r.random; })());
  ok("forge: '1' accepted", (() => { const r = fw("1"); return r.ok && r.n === 1; })());
  ok("forge: '1000000' accepted", (() => { const r = fw("1000000"); return r.ok && r.n === 1000000; })());
  ok("forge: '0' rejected with message", (() => { const r = fw("0"); return !r.ok && /1 to 1,000,000/.test(r.err); })());
  ok("forge: '1000001' rejected with message", (() => { const r = fw("1000001"); return !r.ok && /1 to 1,000,000/.test(r.err); })());
  ok("forge: 'abc' rejected as non-numeric", (() => { const r = fw("abc"); return !r.ok && /not a hybrid number/.test(r.err); })());
  ok("forge: '1.5' rejected", (() => { const r = fw("1.5"); return !r.ok; })());
  ok("forge: '-5' rejected", (() => { const r = fw("-5"); return !r.ok; })());
  ok("forge: '  42  ' trimmed+accepted", (() => { const r = fw("  42  "); return r.ok && r.n === 42; })());
  ok("forge: '000042' canonicalized to 42", (() => { const r = fw("000042"); return r.ok && r.n === 42; })());

  /* ===== 2. compare input validation ===== */
  const cn = (a, b) => { els["cmpa"] = mkEl(); els["cmpb"] = mkEl(); els["cmpa"].value = a; els["cmpb"].value = b; return [S("cmpNum('cmpa')"), S("cmpNum('cmpb')")]; };
  ok("cmpNum: valid pair", (() => { const [a, b] = cn("12", "424242"); return a === 12 && b === 424242; })());
  ok("cmpNum: invalid rejected to 0", (() => { const [a, b] = cn("0", "abc"); return a === 0 && b === 0; })());
  ok("cmpNum: 1000001 rejected", (() => { const [a] = cn("1000001", "5"); return a === 0; })());

  /* ===== 3. shareable URL parsing (item 18) ===== */
  ok("parseMixParam: JAH-MIX-000042 -> 42", S("parseMixParam('JAH-MIX-000042')") === 42);
  ok("parseMixParam: bare number", S("parseMixParam('424242')") === 424242);
  ok("parseMixParam: lowercase prefix", S("parseMixParam('jah-mix-000001')") === 1);
  ok("parseMixParam: out-of-range rejected", S("parseMixParam('JAH-MIX-1000001')") === 0);
  ok("parseMixParam: garbage -> 0", S("parseMixParam('nope')") === 0);

  /* ===== 4. determinism: same number twice (item 14) ===== */
  for (const N of [1, 1000, 424242, 1000000, 16000, 16001]) {
    const a = JSON.stringify(S(`makeHybrid(${N})`));
    const b = JSON.stringify(S(`makeHybrid(${N})`));
    ok(`determinism: makeHybrid(${N}) byte-identical twice`, a === b);
  }

  /* ===== 5. JS mirror vs Python engine ===== */
  const pySrc = `
import json,sys
sys.path.insert(0, ${JSON.stringify(path.join(ROOT, "code"))})
from engine import make_hybrid, load_base, load_wordai, formal_seed
base=load_base(); wbyid={wid:w for w,wid in load_wordai()}
out={}
for N in [1,1000,424242,1000000,16000,16001,14000,999999]:
    r=make_hybrid(N,base,wbyid)
    out[N]={'name':r['name'],'variant':r['variant'],'stamp':r['stamp'],
            'pa':r['parentA']['id'],'pb':r['parentB']['id'],
            'seed':formal_seed(N,r['variant'])}
print(json.dumps(out))`;
  const py = JSON.parse(execFileSync("python3", ["-c", pySrc], { cwd: ROOT }).toString());
  for (const [ns, v] of Object.entries(py)) {
    const N = +ns, j = S(`makeHybrid(${N})`);
    ok(`JS==Python N=${N}: name/parents/variant`,
      j.name === v.name && j.parentA.id === v.pa && j.parentB.id === v.pb && j.variant === v.variant,
      JSON.stringify({ js: [j.name, j.parentA.id, j.parentB.id, j.variant], py: [v.name, v.pa, v.pb, v.variant] }));
    ok(`JS seedOf == Python formal_seed N=${N}`, S(`seedOf({n:${N},variant:${v.variant}})`) === v.seed);
  }

  /* ===== 6. hybrid numbers 1 and 1,000,000 (items 4,5) ===== */
  const h1 = S("makeHybrid(1)"), hM = S("makeHybrid(1000000)");
  ok("hybrid 1: stamp JAH-MIX-000001", h1.stamp === "JAH-MIX-000001");
  ok("hybrid 1000000: stamp JAH-MIX-1000000", hM.stamp === "JAH-MIX-1000000");
  ok("hybrid 1: parents differ", h1.parentA.id !== h1.parentB.id);
  ok("hybrid 1000000: parents differ", hM.parentA.id !== hM.parentB.id);

  /* ===== 7. archive resolution: stored vs on-demand (items 2,15,19) ===== */
  const g1 = await S("getHybrid(1)");
  ok("getHybrid(1): ARCHIVED status", String(g1._status).indexOf("ARCHIVED") === 0, g1._status);
  ok("getHybrid(1): archive hash stamped", typeof g1._hash === "string" && g1._hash.length === 64);
  const gMax = await S("getHybrid(16000)");
  ok("getHybrid(16000): ARCHIVED (last seeded)", String(gMax._status).indexOf("ARCHIVED") === 0);
  const gNext = await S("getHybrid(16001)");
  ok("getHybrid(16001): COMPUTED-ON-DEMAND", gNext._status === "COMPUTED-ON-DEMAND");
  const gM = await S("getHybrid(1000000)");
  ok("getHybrid(1000000): COMPUTED-ON-DEMAND", gM._status === "COMPUTED-ON-DEMAND");

  /* content-hash chain: JS recompute == archive-stamped hash == frozen vector */
  const vectors = JSON.parse(fs.readFileSync(path.join(ROOT, "code", "qa", "test_vectors.json"), "utf8"));
  for (const ns of Object.keys(vectors)) {
    const N = +ns, rec = await S(`getHybrid(${N})`);
    sandbox.CUR = rec;
    const hh = await S("recordHash(CUR)");
    ok(`content hash: N=${N} JS recompute == archive hash == vector`,
      hh === rec._hash && hh === vectors[ns].content_hash, hh + " vs " + rec._hash);
  }

  /* ===== 8. forge batch: Surprise-me range (item 9) ===== */
  for (let k = 0; k < 3; k++) {
    await S("forgeRandom()");
    await new Promise(r => setTimeout(r, 600)); /* forgeRandom fires forgeBatch un-awaited */
    const lf = S("LASTFORGE");
    ok(`forgeRandom #${k + 1}: start in seeded range 1..15988`, lf >= 1 && lf <= 15988, lf);
  }

  /* ===== 9. forgeBatch full path (item 10) ===== */
  await S("forgeBatch(424242,12,'harness run')");
  const boxHTML = els["forgecards"].innerHTML;
  ok("forgeBatch: 12 cards rendered", (boxHTML.match(/class="card"/g) || []).length === 12);
  ok("forgeBatch: forge meta shows range", /424,242/.test(els["forgemeta"].innerHTML));
  ok("forgeBatch: status badges present", /recbadge/.test(boxHTML));
  ok("forgeBatch: on-demand badge class", /recbadge mini ondemand/.test(boxHTML));
  ok("forgeBatch: archive note in meta", /COMPUTED ON DEMAND|ARCHIVED/.test(els["forgemeta"].innerHTML));
  ok("forgeBatch: device counter bumped", els["yourCount"] && els["yourCount"].textContent !== "");

  /* ===== 10. compare two hybrids (item 11) ===== */
  els["cmpa"] = mkEl(); els["cmpb"] = mkEl();
  els["cmpa"].value = "12"; els["cmpb"].value = "424242";
  await S("compareHybrids()");
  const cmpHTML = els["cmpcards"].innerHTML;
  ok("compare: two cards rendered", (cmpHTML.match(/class="card"/g) || []).length === 2);
  ok("compare: both stamps shown", /JAH-MIX-000012/.test(cmpHTML) && /JAH-MIX-424242/.test(cmpHTML));
  els["cmpa"].value = ""; els["cmpb"].value = "5";
  await S("compareHybrids()");
  ok("compare: invalid input shows message", els["cmperr"].style.display === "block" && /two whole/.test(els["cmperr"].textContent));

  /* ===== 11. archive search + filters (items 12,13) ===== */
  els["q"] = mkEl(); els["searchbtn"] = mkEl();
  els["q"].value = ""; S("PILLF='all'");
  await S("doSearch()");
  ok("search: empty query returns browse cards", /class="card"/.test(els["browsecards"].innerHTML));
  els["q"].value = "zzzznomatch123"; await S("doSearch()");
  ok("search: no-match message", /No matching archived hybrid/.test(els["browsecards"].innerHTML));
  els["q"].value = "JAH-MIX-000042"; await S("doSearch()");
  ok("search: exact ID match path", /Exact ID match/.test(els["browsecards"].innerHTML) && /JAH-MIX-000042/.test(els["browsecards"].innerHTML));
  /* filter pills over the real index */
  const pillCounts = {};
  for (const f of ["all", "v0", "v1", "v2", "word", "sysper"]) {
    S(`PILLF='${f}'`); els["q"].value = ""; await S("doSearch()");
    pillCounts[f] = (els["browsecards"].innerHTML.match(/class="card"/g) || []).length;
  }
  ok("filters: all pills render without error", Object.values(pillCounts).every(c => c > 0), JSON.stringify(pillCounts));
  S("PILLF='all'");
  /* pillOK unit checks on synthetic rows */
  ok("pillOK: v0 row", S("PILLF='v0',pillOK([4,'x','JAH-AI-SIG-001','JAH-AI-DOM-002',1])") === true);
  ok("pillOK: v0 rejects v1 row", S("PILLF='v0',pillOK([5,'x','a','b',1])") === false);
  ok("pillOK: word filter", S("PILLF='word',pillOK([14000,'x','JAH-AI-WORD-013740','JAH-AI-SIG-001',94])") === true);
  ok("pillOK: sysper filter", S("PILLF='sysper',pillOK([9,'x','JAH-AI-SIG-003','JAH-AI-PER-002',1])") === true);

  /* ===== 12. file view, badges, talk, dial, downloads (items 15,16,17) ===== */
  await S("openHybrid(424242,true)");
  ok("openHybrid: CUR set + stamp", S("CUR").stamp === "JAH-MIX-424242");
  ok("openHybrid: file view rendered", /RECORD STATUS/.test(els["fileview"].innerHTML));
  ok("statusBadge: computed shows COMPUTED ON DEMAND badge", /recbadge ondemand">COMPUTED ON DEMAND/.test(S("statusBadge()")), S("statusBadge()"));
  await S("openHybrid(42,true)");
  ok("statusBadge: archived shows ARCHIVED badge", /recbadge archived">ARCHIVED/.test(S("statusBadge()")), S("statusBadge()"));
  await S("verifyRecord()");
  ok("verifyRecord: archived hash verifies", /Verified/.test(els["fvverify"].textContent), els["fvverify"].textContent);
  sandbox.CUR = S("makeHybrid(424242)");
  /* Q&A */
  els["qain"] = mkEl(); els["qalog"] = mkEl();
  const qaPairs = [["who are you", "I am"], ["parents", "Parent A"], ["abilities", "fused abilities"],
                   ["variant", "fusion"], ["download", "Copy"], ["xyzzyunknown", "can only answer"]];
  for (const [q, frag] of qaPairs) {
    const ans = S(`qaAnswer(${JSON.stringify(q)})`);
    ok(`qaAnswer: '${q}'`, typeof ans === "string" && ans.toLowerCase().includes(frag.toLowerCase()), ans);
  }
  ok("JAHtalk module loaded", !!S("window.JAHtalk"));
  const ti1 = S("talkIntent('hello',CUR)");
  ok("talkIntent: greeting -> human reply", typeof ti1 === "string" && ti1.length > 10, ti1);
  const ti2 = S("talkIntent('what are your duties',CUR)");
  ok("talkIntent: duties question answered", typeof ti2 === "string" && ti2.length > 10, ti2);
  ok("talkIntent: off-file question -> null (falls to grounded answer)", S("talkIntent('tell me about quantum tunneling',CUR)") === null);
  sandbox.DIAL = { hist: [] };
  const dr = S("dialReply('hello')");
  ok("dialReply: live-session reply non-empty", typeof dr === "string" && dr.length > 10);
  /* downloads */
  const ft = S("fileText(CUR)");
  ok("fileText: valid download text", ft.includes("JAH-MIX-424242") && ft.includes("Mentality") && ft.length > 200);
  ok("download JSON: parses", (() => { try { const o = JSON.parse(JSON.stringify(S("CUR"))); return o.stamp === "JAH-MIX-424242"; } catch (e) { return false; } })());
  await S("dlHybrid(\"txt\")"); await S("dlHybrid(\"json\")");
  ok("dlHybrid: txt+json run without throwing", true);
  /* share */
  const btn = mkEl(); sandbox.__clip = null;
  S("shareHybrid")(btn, 42);
  ok("shareHybrid: copies ?mix= deep link", sandbox.__clip === "https://justinahiggins614-cmyk.github.io/signature-ai-mixlab/?mix=JAH-MIX-000042", sandbox.__clip);

  /* ===== 13. parent resolution vs phone-book canon (item 15) ===== */
  const catalog = JSON.parse(fs.readFileSync("/home/hatch/workspace/jah-ai-models/ai-catalog.json", "utf8"));
  const canonIds = new Set((catalog.records || []).map(r => r.id));
  const base = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "base-ais.json"), "utf8"));
  const missing = base.filter(b => !canonIds.has(b.id));
  ok("parent pool: all 260 base AIs resolve in phone-book canon", missing.length === 0, missing.map(m => m.id).slice(0, 5).join(","));
  const wParent = S("makeHybrid(14000)");
  ok("word-AI parent: hybrid 14000 parentA is a real word AI", wParent.parentA.id === "JAH-AI-WORD-013740" && wParent.parentA.type === "word", wParent.parentA.id);
  ok("word-AI parent: word resolved", (wParent.wordA || wParent.wordB || "").length > 0);
  const unseeded = S("parentOf(100259)");
  ok("word-AI parent: unpopulated slot flagged honestly", unseeded.unseeded === true && /^JAH-AI-WORD-/.test(unseeded.id));

  /* ===== 14. counts surface (item 2) ===== */
  await S("refreshCounts()");
  ok("refreshCounts: seeded count reads 16,000", els["seededCount"].textContent === "16,000", els["seededCount"].textContent);
  ok("refreshCounts: live label", /live from the manifest/.test(els["statverified"].textContent));
  runSrc("APIINFO={counts:{seeded_hybrids:0},_live:false,_unavailable:true};", "apifail");
  await S("refreshCounts()");
  ok("refreshCounts: failure shows retry, never a bare 0", /retry/.test(els["seededCount"].innerHTML) && !/^0$/.test(els["seededCount"].textContent));
  runSrc("APIINFO={counts:{seeded_hybrids:16000},_live:true};", "apiok");

  /* ===== 16. first-time user guide: spotlight tour ===== */
  S("startTour(true)");
  ok("tour: card opens on step 1", els["tourcard"].style.display === "block" && /Step 1 of 7/.test(els["tourtitle"].textContent), els["tourtitle"].textContent);
  ok("tour: step 1 covers WHAT/DOES/HOW", /WHAT/.test(els["tourbody"].innerHTML) && /WHAT IT DOES/.test(els["tourbody"].innerHTML) && /HOW/.test(els["tourbody"].innerHTML));
  S("tourNext()");
  ok("tour: Next -> step 2", /Step 2 of 7/.test(els["tourtitle"].textContent));
  S("tourBack()");
  ok("tour: Back -> step 1", /Step 1 of 7/.test(els["tourtitle"].textContent));
  S("tourSkip()");
  ok("tour: Skip hides card + sets seen flag", els["tourcard"].style.display === "none" && localStore["jah-tour-seen-mixlab"] === "1");
  S("startTour(false)");
  ok("tour: auto-start suppressed once seen", els["tourcard"].style.display === "none");
  delete localStore["jah-tour-seen-mixlab"];
  S("startTour(false)");
  ok("tour: auto-start fires when unseen", els["tourcard"].style.display === "block");
  S("tourSkip()");
  ok("tour: all 7 steps reachable", (() => { S("startTour(true)"); let n = 0; for (let i = 0; i < 7; i++) { if (/Step \d of 7/.test(els["tourtitle"].textContent)) n++; S("tourNext()"); } S("tourSkip()"); return n === 7; })());
  ok("guide panel present in raw HTML", /id="guidepanel"/.test(html) && /id="tourcard"/.test(html));

  /* ===== 17. stamped initial count in raw HTML (universal loading pattern) ===== */
  ok("raw HTML boots seededCount with real number, not bare …",
    /id="seededCount">16,000</.test(html), (html.match(/id="seededCount">[^<]*/)||["?"])[0]);

  /* ===== 18. chunk naming (stored archive integrity) ===== */
  ok("chunkName(1)", S("chunkName(1)") === "mixes-c00001.jsonl.gz");
  ok("chunkName(16000) -> c00107 exists", S("chunkName(16000)") === "mixes-c00107.jsonl.gz" && fs.existsSync(path.join(ROOT, "data", "mixes", "mixes-c00107.jsonl.gz")));
}

main().then(() => {
  console.log(`\n${passes} passed, ${failures} failed`);
  process.exit(failures ? 1 : 0);
}).catch(e => { console.error("HARNESS ERROR:", e); process.exit(2); });
