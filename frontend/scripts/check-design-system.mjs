// Architectural guardrails for future frontend work; not a browser/visual test.
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
const failures = [];
function inspect(directory) {
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) { inspect(path); continue; }
    if (!/\.(tsx|css)$/.test(path)) continue;
    const source = readFileSync(path, 'utf8');
    for (const [index, line] of source.split('\n').entries()) {
      const report = message => failures.push(`${path}:${index + 1}: ${message}`);
      if (/(?:text|bg|border|ring|outline|from|to|via)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d/.test(line)) report('Use a named Nazar palette token.');
      if (/style=\{/.test(line)) report('Move visual styles into the design system.');
      if (/\bshadow-(?:sm|md|lg|xl|2xl|\[)/.test(line) || /box-shadow\s*:/.test(line)) report('Do not add conventional card shadows.');
      if (/font-(?:bold|extrabold|black)/.test(line)) report('Use light display headings; bold is reserved for documented small labels.');
      if (path.endsWith('.tsx') && /#[\da-f]{3,8}\b/i.test(line)) report('Keep literal colors in central tokens.');
    }
  }
}
inspect('app');
if (failures.length) { console.error(failures.join('\n')); process.exitCode = 1; }
else console.log('Nazar design contract checks passed.');
