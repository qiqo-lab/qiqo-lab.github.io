# QIQO Laboratory website

Static website for the **Quantum Information & Quantum Optics (QIQO) Laboratory** at Instituto Superior Técnico, Lisbon.

## Architecture

- Pure HTML/CSS/JavaScript: no build system required.
- GitHub Pages ready (`.nojekyll` included).
- Base laboratory/research/facility/governance data: `assets/js/data.js`.
- People roster: `assets/js/people-data.js`.
- Main publication catalogue: `assets/js/publications-data.js`.
- Additional current-member publications: `assets/js/member-publications-data.js`.
- Projects and their start/end dates: `assets/js/projects-data.js`.
- QIQO / QuLab / QuantMatt/MOTLab news: `assets/js/news-data.js`.
- Styling: `assets/css/site.css`.
- Navigation, footer, filtering and data-driven rendering: `assets/js/site.js`.

## Updating content

### People
Edit `assets/js/people-data.js`. Leadership and the Steering Board are in `assets/js/data.js`. Personnel changes remain human-managed rather than inferred automatically.

### Publications
Edit `assets/js/publications-data.js` or `assets/js/member-publications-data.js`. The website automatically groups papers by year and builds the topic filters.

### Projects
Edit `assets/js/projects-data.js`. Each project has `startDate` and `endDate`. The website calculates its status from the current date, so a listed project automatically moves from **Ongoing projects** to **Past projects** after its end date.

### News
Edit `assets/js/news-data.js`. Keep newest items first; the homepage automatically displays the three newest entries.

## Weekly human-reviewed auto-update

`.github/workflows/weekly-content-review.yml` runs every Monday at **08:00 UTC** and can also be run manually from the GitHub Actions tab. It runs `scripts/weekly_content_update.py`, which scans approved sources including arXiv, Crossref, IT and IPFN for candidate publications, news and projects.

If candidates are found, the workflow opens or refreshes a pull request on `automation/weekly-content-review`, assigns and requests review from `EmmanuelZambriniCruzeiro`, and places a concise summary in the PR body:

- number of new publication candidates;
- number of new news candidates;
- number of new project candidates;
- a short title list for rapid validation.

**Nothing is merged automatically.** Merge the PR to publish the proposed content or close it to reject the weekly candidates. People/student changes remain manual.

The workflow needs repository Actions permissions that allow `contents: write` and `pull-requests: write`. If GitHub blocks the first PR creation, enable **Settings → Actions → General → Workflow permissions → Read and write permissions** and allow GitHub Actions to create pull requests.

## Publishing with GitHub Pages

When ready to launch, make the repository public and enable GitHub Pages from the `main` branch and `/ (root)`.
