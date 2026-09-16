# Cooper website

One static HTML page, CSS, and images. No build step, npm dependencies, or browser
JavaScript. Mica 0.14.0 loads from jsDelivr; `public/style.css` supplies the page
layout. Documentation and examples link to GitHub.

## Preview and check

From the repository root:

```sh
python3 -m http.server 4321 --directory website/public
python3 -m unittest discover -s website/scripts -v
```

The tests check local assets and fragments at both `/` and `/cooper/`, the CDN
stylesheet, page semantics, and the embedded example.

## Publish

Publish `website/public` directly. Relative asset URLs work at either a domain
root or a repository subpath; no base-path configuration is needed.

The `Website` workflow validates pull requests and deploys changes on `main` to
`https://akonwi.github.io/cooper/`. It also supports manual runs on `main`.
Before the first deployment, select **GitHub Actions** in repository Settings →
Pages → Build and deployment → Source.

## Content and captures

- Keep the HTML code example and `snippets/hello.ard` in sync. Validate the Ard
  example from `snippets/` with `ard format --check hello.ard` and `ard check hello.ard`.
- `public/dashboard.gif` is a copy of the README's `screenshots/dashboard.gif`.
  After updating the recording, copy it with
  `cp screenshots/dashboard.gif website/public/dashboard.gif` from the repo root.
- Reduced-motion visitors see `public/dashboard.png`, frame 45 of the recording.
  Regenerate it with
  `ffmpeg -i screenshots/dashboard.gif -vf 'select=eq(n\,45)' -frames:v 1 -update 1 website/public/dashboard.png`.
