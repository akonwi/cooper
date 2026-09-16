import { defineConfig } from 'astro/config';
import { unified } from '@astrojs/markdown-remark';

// The imported guide stays canonical in docs; its sibling links live on GitHub.
function sourceLinks() {
  return function walk(node) {
    if (node.type === 'link' && !/^(?:[a-z]+:|#|\/)/i.test(node.url)) {
      node.url = new URL(node.url, 'https://github.com/akonwi/cooper/blob/main/docs/').href;
    }
    node.children?.forEach(walk);
  };
}

export default defineConfig({
  output: 'static',
  base: process.env.BASE_PATH || '/',
  trailingSlash: 'always',
  markdown: { syntaxHighlight: false, processor: unified({ remarkPlugins: [sourceLinks] }) },
  vite: {
    preview: {
      allowedHosts: process.env.PREVIEW_HOST ? [process.env.PREVIEW_HOST] : [],
    },
  },
});
