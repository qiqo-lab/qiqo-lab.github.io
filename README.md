# QIQO Laboratory website

Static website for the **Quantum Information & Quantum Optics (QIQO) Laboratory** at Instituto Superior Técnico, Lisbon.

## Architecture

- Pure HTML/CSS/JavaScript: no build system required.
- GitHub Pages ready (`.nojekyll` included).
- Shared site content lives in `assets/js/data.js`.
- Styling lives in `assets/css/site.css`.
- Navigation, footer and data-driven cards are rendered by `assets/js/site.js`.

## Updating content

Most routine updates only require editing `assets/js/data.js`:

- `leadership` / `members` — people
- `research` — research themes
- `publications` — papers
- `projects` — funded projects and research programmes
- `news` — news items

## Publishing with GitHub Pages

When ready to launch, make the repository public and enable GitHub Pages from the `main` branch and `/ (root)`.

## First-release checklist

Before public launch, replace/expand the initial member list with the complete QIQO roster and optionally add laboratory/team photography under `assets/img/`.
