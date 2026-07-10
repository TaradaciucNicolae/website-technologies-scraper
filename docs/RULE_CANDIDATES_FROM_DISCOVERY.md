# Rule Candidates From Discovery

This report summarizes concrete signals found in `data/output/discovery_candidates.json` and the rule updates made from them.

## Repeated Signals Found

- PHP appeared on 26 low-detection candidates through `X-Powered-By: PHP/...` and `PHPSESSID`.
- WP Engine appeared on 7 candidates through `X-Powered-By: WP Engine`; `X-Cacheable` and `X-Cache-Group` appeared nearby but are less specific by themselves.
- Wix/Fastly/Varnish edge signals appeared on 10 candidates through `Server-Timing` values such as `fastly_g` and `varnish`, plus the `ssr-caching` cookie.
- Kinsta appeared on 4 candidates through vendor-specific headers such as `x-kinsta-cache`, `ki-edge`, `ki-origin`, `ki-cache-type`, and `ki-cf-cache-status`.
- Akamai Bot Manager appeared on 9 candidates through cookies such as `_abck`, `bm_sz`, `AKA_A2`, and `ddc_akam_bot`, plus `X-Akamai-Transformed`.
- DDoS-Guard appeared on 1 candidate through cookies beginning with `__ddg`.
- Cloudflare Web Analytics appeared on 3 candidates through `performance.radar.cloudflare.com/beacon.js`.
- GoDaddy Website Builder appeared on 2 candidates through `dps_site_id`, `DPS/...`, `img1.wsimg.com/.../website-builder-data-prod`, and GoDaddy CSP evidence.
- Breakdance appeared on 1 candidate through `breakdance_view_count`, `breakdance_session_count`, and `breakdance_last_session_id`.
- WordPress plugin/theme paths appeared as exact `/wp-content/plugins/.../` or `/wp-content/themes/.../` URLs on individual candidates.
- Microsoft Word generated HTML appeared on 1 candidate through `Microsoft Word 10` and `Word.Document`.

## Signatures Added Or Reinforced

- Reinforced `PHP` with `x-powered-by: PHP/` and `server: PHP/`; `PHPSESSID` already existed.
- Added `WP Engine` using `x-powered-by: WP Engine`.
- Added `Fastly` using `server-timing: fastly_g` with medium confidence.
- Reinforced `Varnish` using `server-timing: varnish` and `ssr-caching`, and set the rule to medium confidence because the new evidence is indirect.
- Added `Kinsta` using vendor-specific Kinsta headers.
- Reinforced `Akamai Bot Manager` with `_abck`, `AKA_A2`, `ddc_akam_bot`, and `x-akamai-transformed`.
- Reinforced `DDoS-Guard` with cookie prefix `^__ddg`.
- Added `Cloudflare Web Analytics` using `performance.radar.cloudflare.com/beacon.js`.
- Reinforced `GoDaddy Website Builder` with `DPS/`, `godaddy.com` in CSP, and the existing `dps_site_id`/`img1.wsimg.com` evidence.
- Reinforced `Breakdance` with its visitor/session cookie names.
- Added exact WordPress plugin/theme path rules for WP Accessibility, Accessibility Checker, Accessibility New Window Warnings, Album and Image Gallery Plus Lightbox, Kadence Theme, Catch Box Theme, Parabola Theme, and Titan Digital Agency Theme.
- Added `Microsoft Word` as a medium-confidence document-authoring generator rule.

## Signals Intentionally Skipped

- `x-served-by: cache-...` was not added for Fastly because `cache-` alone is too generic and the test suite already guards against that false positive.
- `Akamai-GRN` was not added to Akamai Bot Manager because the existing tests treat it as Akamai CDN evidence, not bot-management evidence.
- WP Engine `X-Cacheable` and `X-Cache-Group` were documented but not added because they are weaker than `X-Powered-By: WP Engine`.
- DDC/dealer automotive cookies were skipped because the discovery data did not provide enough local evidence to attribute them to a specific technology rule safely.
- Plain words such as `cache`, `cdn`, `cloud`, `analytics`, `wp`, `script`, and company marketing text were not added as signatures.
