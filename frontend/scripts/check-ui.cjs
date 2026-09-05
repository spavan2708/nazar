/* eslint-disable @typescript-eslint/no-require-imports -- This standalone CommonJS harness installs a TS loader; application code uses ESM. */
/* Static React rendering checks. These do not simulate a browser or layout. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
for (const ext of ['.ts', '.tsx']) {
  require.extensions[ext] = (module, filename) => {
    const output = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 },
    });
    module._compile(output.outputText, filename);
  };
}
const render = (Component, props = {}) => renderToStaticMarkup(React.createElement(Component, props));
const { default: AnalysisCard, agreementLabels } = require('../app/analysis-card.tsx');
const { default: Timeline } = require('../app/investigation-timeline.tsx');
const { default: Home } = require('../app/page.tsx');
const { default: Guidance } = require('../app/trusted-guidance.tsx');
const { default: Composer } = require('../app/evidence-composer.tsx');
const { RiskBadge, AnalyzerTabs, ExpandablePanel, FileDropzone, Notice, LoadingStatus } = require('../app/components/ui.tsx');
const { validateUpload } = require('../app/upload-utils.ts');
const base = { score: 35, risk_level: 'medium', signals: [], explanation: 'Review this request.', recommended_action: 'Verify independently.' };
for (const level of ['low', 'medium', 'high', 'critical']) {
  assert.match(render(RiskBadge, { level }), new RegExp(`${level[0].toUpperCase()+level.slice(1)} risk`));
}
assert.match(render(AnalysisCard, { analysis: base }), /No explicit signals detected/);
assert.match(render(AnalysisCard, { analysis: base }), /Unavailable/);
assert.doesNotMatch(render(AnalysisCard, { analysis: base }), /Trusted guidance/);
const source = { available: true, suspicious: false, signals: [], safety_warning: false };
for (const [status, label] of Object.entries(agreementLabels)) {
  const analysis = { ...base, intelligence: {
    deterministic: { ...source, risk_before_fusion: 0 },
    ml: { ...source, suspicious: true, score: .31, semantic_neighbors: { available: true, suspicious: [{ text: 'Synthetic request example', similarity: .42, language: 'English', category: 'otp' }], safe: [] } },
    llm: { ...source, available: false }, agreement: { status, explanation: 'Sources may interpret wording differently.' },
  } };
  const html = render(AnalysisCard, { analysis });
  assert.ok(html.includes(label));
  assert.ok(!html.includes(status));
  assert.match(html, /Local ML suspiciousness score: 0.31/);
  assert.doesNotMatch(html, /31%/);
  assert.match(html, /Synthetic training examples/);
  assert.match(html, /aria-expanded="false"/);
}
const unsafe = 'http://192.0.2.1:8080/login/verify/account';
const linkAnalysis = { normalized_url: unsafe, domain: '192.0.2.1', valid: true, structural_risk_score: 80, risk_level: 'high', indicators: [], explanation: 'Structural indicators detected.' };
const html = render(AnalysisCard, { analysis: { ...base, urls: [linkAnalysis] } });
assert.ok(html.includes(unsafe));
assert.ok(!html.includes(`href="${unsafe}"`));
const ref = { source_id: 'reference', chunk_id: 'reference-1', title: 'Safety reference', source_name: 'SBI', source_url: 'https://sbi.co.in/web/customer-care/contact-centre', guidance: 'Keep OTPs private.', topics: ['otp'], matched_signals: ['OTP_REQUEST'], matched_topics: [], matched_stages: [], similarity: .4, relevance: 'signal' };
const trusted = render(Guidance, { grounding: { available: true, results: [ref] } });
assert.match(trusted, /rel="noopener noreferrer"/);
assert.match(trusted, /trusted reference link/);
for (const source_url of ['javascript:alert(1)', 'https://sbi.co.in.evil.example', 'https://user@sbi.co.in']) {
  assert.doesNotMatch(render(Guidance, { grounding: { available: true, results: [{ ...ref, source_url }] } }), /<a /);
}
const item = { interaction_id: 'test', order: 2, type: 'text', created_at: '2026-09-05T00:00:00Z', display_text: '<script>untrusted</script>', analysis: base, metadata: {}, canonical_signal_codes: [], campaign_score_after: 35, campaign_risk_level_after: 'medium', risk_delta: 0, contextual_reinforcements: [{ stage: 'AUTHENTICATION_TAKEOVER', source_evidence_id: 'earlier', source_evidence_order: 1, explanation: 'This wording reinforces an earlier OTP request.' }] };
const timeline = render(Timeline, { evidence: [item] });
assert.match(timeline, /Reinforces earlier pattern/);
assert.match(timeline, /No explicit signals detected/);
assert.match(timeline, /does not add a signal/);
assert.ok(timeline.includes('&lt;script&gt;'));
assert.ok(!timeline.includes('<script>untrusted'));
const tabs = render(AnalyzerTabs, { id: 'test', label: 'Test tabs', options: [{ value: 'one', label: 'One' }, { value: 'two', label: 'Two' }], value: 'one', onChange() {} });
assert.equal((tabs.match(/role="tab"/g) || []).length, 2);
assert.equal((tabs.match(/tabindex="0"/g) || []).length, 1);
assert.match(tabs, /aria-controls="test-panel-one"/);
assert.match(render(ExpandablePanel, { title: 'Details', children: 'Hidden detail' }), /hidden=""/);
assert.match(render(FileDropzone, { id: 'file', label: 'File', help: 'PNG', accept: 'image/png', file: null, disabled: true, onSelect() {} }), /type="file"[^>]*disabled=""/);
assert.match(render(Notice, { error: true, children: 'OCR unavailable.' }), /role="alert"/);
assert.match(render(LoadingStatus, { children: 'Checking.' }), /role="status"/);
assert.equal(validateUpload({ name: 'bad.exe', type: 'application/octet-stream', size: 1 }, 'screenshot'), 'Choose a PNG, JPEG or WEBP screenshot.');
assert.match(validateUpload({ name: 'large.wav', type: 'audio/wav', size: 21*1024*1024 }, 'audio'), /20 MiB/);
const page = render(Home);
for (const value of ['message','link','screenshot','audio']) assert.ok(page.includes(`id="analyzer-panel-${value}"`));
for (const id of ['message-input','link-input','screenshot-file','audio-file']) assert.ok(page.includes(`for="${id}"`));
const composer = render(Composer, { campaignId: 'test', disabled: false, onAdded() {}, onBusy() {}, onUnavailable() {} });
for (const value of ['text','url','screenshot','audio']) assert.ok(composer.includes(`id="evidence-panel-${value}"`));
console.log('Static UI state, accessibility markup, upload validation and safe-link checks passed.');

// Actual API fixtures can be checked without claiming browser layout coverage.
if (process.env.NAZAR_E2E_RESULTS) {
  const report = JSON.parse(fs.readFileSync(process.env.NAZAR_E2E_RESULTS, 'utf8'));
  for (const item of [...report.cases, ...(report.adversarial ?? [])]) {
    const html = render(AnalysisCard, { analysis: item.analysis });
    assert.match(html, /Risk assessment/);
    assert.match(html, /What you should do/);
    assert.ok(html.includes(String(item.score ?? item.analysis.score)));
  }
  for (const campaign of report.investigation) {
    const timeline = render(Timeline, { evidence: campaign.interactions });
    assert.ok(timeline.includes(campaign.interactions.length ? 'Evidence' : 'Your timeline is ready.'));
  }
  console.log(`Rendered ${report.cases.length + (report.adversarial?.length ?? 0)} actual API analysis fixtures and ${report.investigation.length} campaign states.`);
}
