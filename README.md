# DFWTravelDeals.com

Flight + hotel package deals priced from DFW Airport and cruise deals sailing from Galveston, re-checked every morning.

Live at **https://dfwtraveldeals.com** (GitHub Pages). Sister site to GetoutofDallas.com, with different deals.

## How it works

- `site/` is the whole website: `index.html`, the deal list `board.json`, and the destination and ship `photos/`.
- The claude.ai board (https://claude.ai/artifact/RWupZWLCKXD7Q6vjzFXTmu) is the source of truth. Its database holds `deals` (flight + hotel), `cruises` (Galveston sailings), `meta/site` and email `signups`.
- Two Claude scheduled tasks keep the deals current: a daily price check (Tue–Sun, about 7:37 AM CT) and a Monday full refresh (about 11:23 AM CT). After each run they save the board to the shared Google Drive folder **DFWTravelDeals.com board data** as `board-YYYY-MM-DD-HHMM-<sha8>.json`, built with `scripts/build_board.py`.
- The tasks never list a hotel, package or sailing that's on GetoutofDallas.com's board, so the two sites show different deals.
- `.github/workflows/deploy.yml` runs at 15:17 and 20:17 UTC (and on every push). It pulls the newest board from Drive with `scripts/pull_board.py`, commits it if it changed, updates the sitemap, writes the deals into the page for crawlers with `scripts/prerender_board.py`, and deploys `site/` to GitHub Pages. A bad, missing or tampered file is skipped and the current board stays up. If the deals go more than two days without an update, the run fails and GitHub emails you.

## Editing

- The page here and the claude.ai board run the same code. Ask Claude to change both together, or edit `site/index.html` and push to `main`; the site redeploys in about a minute.
- To refresh deals right away, open **Actions → Sync deals and deploy → Run workflow**.
- To hide a listing for good, add its title to `blocked` in the board's `meta/site` document; to pin the spotlight, set `spotlight` to `cruises/<id>` or `deals/<id>`.
- Deals past their book-by, travel or sailing dates hide themselves in the browser, so an old board never shows expired trips.

Photos are Creative Commons or public-domain shots from Flickr; credits are listed on the page.
