# Website Technologies Scraper

This project detects technologies used by websites from a list of input domains. For every detected technology, the output includes concrete evidence that explains why the technology was detected and where the matching signal was found.

The project was built for the Veridion Website Technologies Scraper challenge. The input contains 200 cleaned domains, and the scraper can process the full list or a smaller limit during development.

## What The Project Does

The scraper follows this pipeline:

1. Extract and clean domains from the input Parquet file.
2. Fetch each website over HTTPS, then HTTP if needed.
3. Collect response data such as final URL, status code, headers, cookies, HTML, redirects, and timing.
4. Parse HTML with BeautifulSoup for structured signals.
5. Fetch a limited number of JavaScript assets for extra detection signals.
6. Apply rule-based technology detection.
7. Save detailed JSON, JSONL, CSV summary, JSON summary, and discovery output files.

The main reason for this structure is that technologies can expose themselves in many different places. Some appear in HTTP headers, some in cookies, some in script URLs, some in meta tags, and some only inside JavaScript files.

## Project Structure

```text
data/
  domains.txt
  raw/domains.snappy.parquet
  output/discovery_candidates.json
  output/technology_detections.json
  output/technology_detections.jsonl
  output/technology_summary.csv
  output/technology_summary.json

rules/
  technology_rules.json

src/
  discovery_candidates.py
  extract_domains.py
  javascript_asset_fetcher.py
  technology_detector.py
  website_fetcher.py

tests/
  test_technology_detector.py

main.py
requirements.txt
README.md
```

## Input Data

The raw input file is:

```text
data/raw/domains.snappy.parquet
```

`src/extract_domains.py` extracts the domains, removes empty values and duplicates, normalizes the values, and writes the clean list to:

```text
data/domains.txt
```

The current cleaned domain list contains 200 domains.

## Website Fetching

Website fetching is implemented in:

```text
src/website_fetcher.py
```

For each domain, the scraper tries:

1. `https://domain`
2. `http://domain`

The fetch result stores:

- original domain
- attempted URLs
- successful URL
- final URL after redirects
- HTTP status code
- response headers
- response cookies
- HTML content
- elapsed time in milliseconds
- content type
- redirect count
- error message, if the request failed

Cookies were added because many analytics, advertising, security, and ecommerce tools expose stable cookie names.

## Evidence Sources

Technology detection is implemented in:

```text
src/technology_detector.py
```

Rules are stored in:

```text
rules/technology_rules.json
```

The detector currently uses these evidence sources:

- raw HTML signatures
- HTTP header signatures
- cookie names
- domain and final URL signatures
- script URL signatures from `<script src="...">`
- stylesheet URL signatures from `<link href="...">`
- meta generator tags
- DOM markers and common attributes
- JavaScript asset content
- package-like CDN URLs

The rules are split by source:

```json
{
  "name": "Example Technology",
  "category": "Example Category",
  "confidence": "high",
  "domain_signatures": [],
  "html_signatures": [],
  "script_url_signatures": [],
  "stylesheet_url_signatures": [],
  "meta_generator_signatures": [],
  "dom_marker_signatures": [],
  "cookie_signatures": [],
  "header_signatures": {},
  "js_asset_signatures": [],
  "package_url_signatures": []
}
```

Separating rules by source makes the evidence more precise. For example, detecting `wp-content` in a stylesheet URL is more useful than only saying it appeared somewhere in the page HTML.

## Evidence Model

Each technology contains one or more evidence items. Every evidence item has the same structure:

```json
{
  "type": "script_url",
  "source": "html",
  "location": "script[src]",
  "matched_value": "cdn.shopify.com",
  "excerpt": "https://cdn.shopify.com/app.js",
  "confidence": "high",
  "explanation": "Found 'cdn.shopify.com' in a script URL."
}
```

Evidence fields:

- `type`: kind of evidence, such as `header`, `cookie`, `script_url`, or `js_asset`
- `source`: the data source inspected by the detector
- `location`: the exact place where the match was found
- `matched_value`: the signature that matched
- `excerpt`: the concrete header, cookie, URL, HTML snippet, or JavaScript snippet
- `confidence`: confidence level from the rule
- `explanation`: readable explanation of the detection

This is important because the output should not only list technologies. It should also justify each detection.

## JavaScript Asset Scanning

Some technologies do not appear directly in the HTML. They can be hidden inside files such as:

```html
<script src="/assets/app.bundle.js"></script>
```

For this reason, the project includes:

```text
src/javascript_asset_fetcher.py
```

The JavaScript asset scanner:

- extracts script URLs with BeautifulSoup
- selects up to 5 useful JavaScript assets per website
- prioritizes external scripts, CDN files, bundles, app files, vendor files, and analytics files
- fetches each asset with a short timeout
- reads at most 500 KB from each JavaScript file
- searches the content using `js_asset_signatures`

This improves coverage for tools such as analytics platforms, chat widgets, ecommerce apps, frontend libraries, and monitoring scripts.

## Output Files

Running the scraper writes files to:

```text
data/output/
```

### Detailed JSON

```text
data/output/technology_detections.json
```

Contains the full result for every processed domain, including all technologies and all evidence items.

### JSONL

```text
data/output/technology_detections.jsonl
```

Stores one domain result per line. This format is useful for larger datasets because it can be processed line by line.

### CSV Summary

```text
data/output/technology_summary.csv
```

Contains a compact table with domain, final URL, status, technology name, category, confidence, evidence count, evidence types, and first evidence.

### JSON Summary

```text
data/output/technology_summary.json
```

Contains aggregate results:

```json
{
  "total_domains": 5,
  "reachable_domains": 5,
  "total_findings": 77,
  "unique_technologies": 43,
  "confidence_distribution": {
    "high": 55,
    "medium": 22
  },
  "top_technologies": [
    {
      "name": "Cloudflare",
      "domains": 5
    }
  ]
}
```

### Discovery Candidates

```text
data/output/discovery_candidates.json
```

This file helps improve the rule set using real crawl data. Instead of guessing new rules, the scraper records sites with no detections or only a low number of detections.

The current structure is:

```json
{
  "undetected": [],
  "detected_low_number": [],
  "max_detection_count_shown_in_discovery": 5
}
```

Each site record can include useful signals such as:

- headers
- cookies
- script URLs
- stylesheet URLs
- JavaScript asset URLs
- meta generator values
- meta tags
- package candidates from known CDN URLs

This makes it easier to inspect low-detection websites and decide which new rules should be added next.

## Current Generated Results

The committed output files currently represent a validation run over 5 domains. The full cleaned input list contains 200 domains.

Current summary from `data/output/technology_summary.json`:

- domains scanned in current output: 5
- reachable domains: 5
- total findings: 77
- unique technologies found: 43
- high confidence findings: 55
- medium confidence findings: 22

Top technologies in the current output include:

- Cloudflare: 5 domains
- Google Analytics: 4 domains
- Zendesk: 4 domains
- jQuery: 4 domains
- Tailwind CSS: 4 domains

During development, small runs were used first to validate the logic quickly. After the rules and tests looked correct, the same pipeline could be run on the full 200-domain list.

## Running The Project

Install dependencies:

```bash
pip install -r requirements.txt
```

Run on all domains:

```bash
python main.py
```

Run on a small sample:

```bash
python main.py --limit 5
```

Delete and recreate output files:

```bash
python main.py --rewrite 1
```

Append to existing output files:

```bash
python main.py --rewrite 0
```

Example quick run:

```bash
python main.py --limit 5 --rewrite 1
```

At the end, the script prints:

```text
Different technologies found: X
Total technologies found: Y
```

`Different technologies found` means unique technology names. `Total technologies found` means all technology detections across all processed domains.

## Running Tests

Run:

```bash
python -m unittest discover
```

The tests cover the main detection paths:

- HTML evidence
- header evidence
- domain evidence
- cookie evidence
- script URL evidence
- stylesheet URL evidence
- meta generator evidence
- DOM marker evidence
- JavaScript asset evidence
- selected expanded rules

## Development Process

The project was improved step by step instead of rewriting everything at once.

Completed steps:

1. Improved the evidence model so every detection has structured evidence.
2. Added cookie collection in the fetcher and cookie signatures in the rules.
3. Added BeautifulSoup parsing for meta generator tags, script URLs, stylesheet URLs, and DOM markers.
4. Split rules by source: HTML, headers, cookies, meta generator, script URLs, stylesheet URLs, domain signatures, JavaScript assets, and package URLs.
5. Added JSONL output and CSV summary output.
6. Added limited JavaScript asset scanning with timeouts and max file size.
7. Added `technology_summary.json` with aggregate counts and top technologies.
8. Added `discovery_candidates.json` to inspect domains with no detections or few detections.
9. Expanded the rule set with more CMS, ecommerce, payments, analytics, support, CDN, hosting, and frontend technologies.

The development workflow was:

1. Run on a small subset of domains.
2. Check whether expected technologies were detected.
3. Add focused rules based on real evidence.
4. Add or update tests for important detection paths.
5. Run a larger dataset and inspect the summary/discovery outputs.
6. Repeat with more rules only when there was useful evidence.

## Detection Coverage

The rule set currently covers technologies from categories such as:

- CMS platforms
- ecommerce platforms and Shopify apps
- payment providers
- analytics and advertising tools
- marketing and CRM tools
- support and chat tools
- JavaScript frameworks
- frontend libraries
- CSS frameworks
- CDN and security providers
- hosting platforms
- monitoring and product analytics tools

The rule file currently contains 200 technology rules.

## Limitations

The scraper works with the data returned by normal HTTP requests. It does not run a real browser.

Important limitations:

- JavaScript is fetched and inspected, but it is not executed.
- Browser-only runtime behavior is not observed.
- Some websites block automated requests or return challenge pages.
- Some backend technologies do not expose public signatures.
- Some generic signatures can create false positives.
- Results can change depending on redirects, location, cookies, A/B tests, and response time.
- The JavaScript asset scanner is intentionally limited to avoid slow or heavy crawling.

Because of these limitations, every detection includes evidence so the result can be reviewed.

## How This Could Scale To Millions Of Domains

For millions of domains, the same idea should be kept, but the execution model should change.

Possible scaling plan:

- store domains in a queue instead of a text file
- run many worker processes or containers
- use asynchronous HTTP fetching for higher throughput
- set strict timeouts, retry limits, and maximum response sizes
- store raw fetch metadata and detections in a database or object storage
- write JSONL files in batches instead of keeping everything in memory
- deduplicate domains and normalize URLs before crawling
- separate fetching, detection, summary generation, and discovery into separate jobs
- monitor error rates, blocked domains, response times, and detection rates
- update rules from discovery data, then rerun only the domains affected by new rules

The current project keeps the implementation simple, but the output formats and evidence model are compatible with this kind of larger pipeline.

## How New Technologies Can Be Discovered

The discovery process should be data-driven:

1. Run the scraper on real domains.
2. Open `discovery_candidates.json`.
3. Inspect the `undetected` and `detected_low_number` sections.
4. Look at repeated headers, cookies, script domains, stylesheet domains, meta generator values, and JavaScript asset URLs.
5. Add new rules only when there is a concrete signal.
6. Add a focused test when the new rule covers an important detection path.
7. Rerun the scraper and compare `technology_summary.json`.

This avoids guessing rules randomly and makes the rule set easier to justify.
