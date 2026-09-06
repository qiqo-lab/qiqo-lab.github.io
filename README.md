# QIQO Laboratory website

Static website for the **Quantum Information & Quantum Optics (QIQO) Laboratory** at Instituto Superior Técnico, Lisbon.

## Architecture

- Pure HTML/CSS/JavaScript: no build system required.
- GitHub Pages ready (`.nojekyll` included).
- Base laboratory/research/facility data: `assets/js/data.js`.
- People roster: `assets/js/people-data.js`.
- Main publication catalogue: `assets/js/publications-data.js`.
- Additional current-member publications: `assets/js/member-publications-data.js`.
- Projects and their start/end dates: `assets/js/projects-data.js`.
- QIQO / QuLab / QuMatt / MOTLab news: `assets/js/news-data.js`.
- Styling: `assets/css/site.css`.
- Navigation, footer, filtering and data-driven rendering: `assets/js/site.js`.

## Updating content

Routine updates are intentionally separated by content type so that the scientific record can be maintained without editing page markup.

### People
Edit `assets/js/people-data.js`. Leadership and steering-board information remains in `assets/js/data.js`.

### Publications
Edit `assets/js/publications-data.js` or `assets/js/member-publications-data.js`. The website automatically groups papers by year and builds the topic filters.

### Projects
Edit `assets/js/projects-data.js`. Each project has `startDate` and `endDate`. The website calculates its status from the current date, so a listed project automatically moves from **Ongoing projects** to **Past projects** after its end date.

### News
Edit `assets/js/news-data.js`. Keep newest items first; the homepage automatically displays the three newest entries.

## Publishing with GitHub Pages

When ready to launch, make the repository public and enable GitHub Pages from the `main` branch and `/ (root)`.

## Future automation

GitHub Pages itself does not discover new external content. A scheduled GitHub Actions workflow can be added to query approved sources (for example ORCID/arXiv/Crossref/OpenAlex for publications and IT/IPFN pages for news/projects), generate candidate data updates, and open a pull request for review before publication.
