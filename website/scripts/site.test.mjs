import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { parseHTML } from 'linkedom';

const base = process.env.BASE_PATH || '/';
const root = new URL('../dist/', import.meta.url).pathname;
const files = readdirSync(root, { recursive: true });
const pages = files.filter(file => file.endsWith('.html'));
const origin = 'https://example.test';

function resolveLocal(value, from) {
  const url = new URL(value, from);
  if (url.origin !== origin) return null;
  assert.ok(url.pathname.startsWith(base), `URL escaped deployment base ${base}: ${url}`);
  const relative = decodeURIComponent(url.pathname.slice(base.length));
  const path = join(root, relative.endsWith('/') || !relative ? `${relative}index.html` : relative);
  assert.ok(existsSync(path), `Missing target: ${url} (from ${from})`);
  return { path, url };
}

test('four static pages and the GitHub Pages marker are emitted', () => {
  assert.deepEqual(pages.sort(), ['examples/index.html', 'get-started/index.html', 'guide/index.html', 'index.html']);
  assert.ok(existsSync(join(root, '.nojekyll')));
});

for (const page of pages) {
  test(`${page}: local URLs, fragments, semantics, and zero scripts`, () => {
    const { document } = parseHTML(readFileSync(join(root, page), 'utf8'));
    const from = `${origin}${base}${page.replace(/index\.html$/, '')}`;
    assert.equal(document.querySelectorAll('h1').length, 1);
    assert.equal(document.documentElement.lang, 'en');
    assert.ok(document.querySelector('main#main'));
    assert.ok(document.querySelector('meta[name="description"]')?.content);
    assert.equal(document.querySelectorAll('script').length, 0);
    for (const node of document.querySelectorAll('[href], [src]')) {
      const target = resolveLocal(node.getAttribute('href') || node.getAttribute('src'), from);
      if (target?.url.hash && target.path.endsWith('.html')) {
        const destination = parseHTML(readFileSync(target.path, 'utf8')).document;
        assert.ok(destination.getElementById(decodeURIComponent(target.url.hash.slice(1))), `Missing anchor: ${target.url}`);
      }
      if (node.tagName === 'IMG') assert.ok(node.getAttribute('alt'));
      if (node.tagName === 'LINK' || node.tagName === 'IMG') assert.ok(target, 'Assets must be self-hosted');
    }
  });
}

test('stylesheets reference only emitted local assets, including fonts', () => {
  for (const file of files.filter(file => file.endsWith('.css'))) {
    const css = readFileSync(join(root, file), 'utf8');
    assert.ok(!css.includes('https://'), 'External stylesheet dependency');
    for (const [, value] of css.matchAll(/url\(["']?([^"')]+)["']?\)/g)) {
      if (!value.startsWith('data:')) assert.ok(resolveLocal(value, `${origin}${base}${file}`));
    }
  }
});

test('the guide keeps its source-document links instead of broken relative routes', () => {
  const html = readFileSync(join(root, 'guide/index.html'), 'utf8');
  assert.ok(html.includes('https://github.com/akonwi/cooper/blob/main/docs/cui-virtual-list-benchmark.md'));
});
