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
- QIQO / QuLab / QuMatt/MOTLab news: `assets/js/news-data.js`.
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

`.github/workflows/weekly-content-review.yml` runs every Monday at **08:17 UTC** and can also be run manually from the GitHub Actions tab. It runs `scripts/weekly_content_update.py`, which scans approved sources including arXiv, Crossref, IT and IPFN for candidate publications, news and projects.

If candidates are found, the workflow opens or refreshes a pull request on `automation/weekly-content-review`, assigns and requests review from `EmmanuelZambriniCruzeiro`, and places a concise summary in the PR body:

- number of new publication candidates;
- number of new news candidates;
- number of new project candidates;
- a short title list for rapid validation.

**Nothing is merged automatically.** Merge the PR to publish the proposed content or close it to reject the weekly candidates. People/student changes remain manual.

The workflow explicitly requests `contents: write` and `pull-requests: write`. Separately, enable **Settings → Actions → General → Workflow permissions → Allow GitHub Actions to create and approve pull requests** and click **Save**. An organization policy may also need to allow this. The workflow never approves or merges PRs. This repository setting cannot be enabled from workflow YAML.

Scanner/workflow fixes pushed to `main` run tests only, with read-only permissions; they never scan live sources or create/refresh review PRs. Every run preserves its summary and candidate data as a 30-day Actions artifact before trying to open a PR. PR creation/refresh failures remain visible; assignment failures are warnings. Source failures are listed explicitly in the summary. Projects are deduplicated by acronym as well as URL; news without a verifiable recent date is skipped. The scanner discovers additions, not changes to existing publication metadata or project dates; these still need editorial review.

## Publishing with GitHub Pages

When ready to launch, make the repository public and enable GitHub Pages from the `main` branch and `/ (root)`.
## Licensing

The website source code (HTML, CSS, JavaScript, Python scripts and GitHub Actions workflow files) is available under the MIT License. QIQO branding, the QIQO logo, photographs, written/editorial content, research descriptions, news content and other media assets are **not** covered by the MIT License. See `NOTICE.md` for details.

## Search visibility and static HTML

The nine main pages have canonical URLs, unique titles and descriptions, Open Graph / Twitter metadata, and JSON-LD. The homepage identifies QIQO and its institutional parents. `sitemap.xml` lists the canonical pages and is advertised in `robots.txt`; no guessed or automatically refreshed modification dates are emitted.

Navigation, publications and news are also included directly in HTML. After editing the data files, run `python scripts/render_static_content.py` (requires Node.js and beautifulsoup4). The weekly review workflow does this before opening its PR and includes the changed publication/news pages. JavaScript continues to handle filters and mobile navigation. The renderer is deterministic and can be rerun safely.

To finish Google setup, add a URL-prefix property for `https://qiqo-lab.github.io/` in Google Search Console. Use its HTML file or HTML meta-tag verification method; publish the exact file/tag supplied by Google, then click Verify. Submit `sitemap.xml` and request indexing of the homepage and key pages. Keep the verification file/tag in place. Indexing and ranking are controlled by Google and are not guaranteed by submission.

Ask the maintainers of the official IT QIQO announcement, QuLab, QPI, IPFN/GoLP and Técnico pages to link to `https://qiqo-lab.github.io/` with the anchor text “QIQO — Quantum Information and Quantum Optics Laboratory”. These institutional records are managed outside this repository.

### Duplicate-review prevention

Scheduled and manual reviews run separately from push-triggered tests. The Monday schedule is 08:17 UTC (09:17 in Lisbon during summer, 08:17 during winter); GitHub can still delay scheduled jobs. Before scanning and again before writing a PR, the workflow checks paginated closed PRs for a content review already merged that calendar day in Europe/Lisbon. This includes reviews created through the connected account. Both scheduled and manual runs skip if a matching merged review exists; the reason appears in the Actions summary.

A PR is only created/refreshed when the scanner changes a publication, news or project data file. HTML serialization changes alone do not generate a review. The scanner report and source warnings remain available in the Actions summary and artifact when a scan runs without candidates.
