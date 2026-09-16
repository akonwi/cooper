# Cooper website

A fully static Astro site styled with `@akonwi/mica`. The output is plain HTML,
CSS, and images, using system fonts and Mica's light/dark color roles;
no server adapter, browser JavaScript, API, or external font service is required.

## Develop

Use Node 22.12+ and npm:

```sh
cd website
npm ci
npm run dev
```

## Build for GitHub Pages

For a repository site at `/cooper/`:

```sh
BASE_PATH=/cooper/ npm run build
BASE_PATH=/cooper/ npm test
```

For a custom domain or a root-level user/organization site:

```sh
npm run build
npm test
```

The publish directory is `website/dist`. Upload that directory as the GitHub
Pages artifact when deployment is configured. `.nojekyll` is included for
branch-based publishing too. No deployment workflow or destination is configured
by this change. `BASE_PATH` must include leading and trailing slashes.

`npm test` checks every generated local link, fragment, stylesheet, and image,
including links under the configured base path, and rejects client scripts.
Run it after each build with the same `BASE_PATH`.

## Content and captures

- The guide renders `../docs/declarative.md` directly. Relative Markdown links
  point back to their source documents on GitHub.
- The homepage and getting-started program both use
  `snippets/hello.ard`. Validate it from `snippets/` with
  `ard format --check hello.ard` and `ard check hello.ard`.
- The homepage imports the README's `../screenshots/dashboard.gif` directly.
  Reduced-motion visitors see `public/dashboard.png`, frame 45 of that dashboard
  recording. Regenerate from the repository root with
  `ffmpeg -i screenshots/dashboard.gif -vf 'select=eq(n\,45)' -frames:v 1 -update 1 website/public/dashboard.png`.
- `public/tinear.png` is a real PTY frame from `examples/cui_tinear.ard`, rendered
  at 126 columns × 28 rows with DejaVu Sans Mono. Regenerate from this directory
  with `uv run scripts/capture-tinear.py` (requires Ard, Go, and DejaVu fonts).
  The capture uses the repository's PTY harness and static example data.

No library files need to change to build or serve the site.
