# Website Technologies Scraper

Website Technologies Scraper is a static, evidence-driven crawler for the Veridion Website Technologies Scraper challenge. It processes a cleaned list of 200 domains and detects visible website technologies such as ecommerce platforms, Shopify apps, analytics tools, advertising tags, payment providers, review widgets, chat/support tools, CMSs, CDNs, hosting providers, security services, and frontend libraries.

The business context matters: companies that sell to Shopify or ecommerce stores often need to know which platforms and tools a website uses. A raw technology name is not enough for that use case. The output should explain why the technology was detected so a reviewer can trust the result, inspect false positives, and improve the rule set over time.

## Approach

The detector is rule-based and evidence-first. Each rule contains explicit signatures for one technology, and each match produces structured evidence with the matched value, location, excerpt, confidence, and explanation.

The scraper looks for signals in:

- HTTP response headers
- response cookies
- original domain and final redirected URL
- raw HTML
- meta generator tags
- script URLs
- stylesheet URLs
- DOM attributes and markers
- selected JavaScript asset contents
- package-like CDN URLs such as jsDelivr, unpkg, cdnjs, esm.sh, and Skypack

This design is intentionally deterministic instead of black-box. A rule-based detector is easier to debug, explain, test, and improve than a model that only returns a label. It also fits the challenge requirement that detections should be supported by evidence.

The main trade-off is that the scraper uses static crawling, not a real browser. It fetches pages and a limited number of JavaScript assets, but it does not execute JavaScript. This keeps the implementation simple and fast enough for the challenge while still covering many real-world signals.

## Architecture

The pipeline is:

1. Read the raw Parquet input and normalize domains into `data/domains.txt`.
2. For each domain, try `https://domain` first and fall back to `http://domain`.
3. Store fetch metadata such as attempted URLs, final URL, status, headers, cookies, content type, redirect count, elapsed time, and errors.
4. Parse HTML with BeautifulSoup.
5. Extract evidence sources from headers, cookies, URLs, meta tags, script tags, stylesheet links, DOM markers, and raw HTML.
6. Fetch a small, prioritized set of JavaScript assets and scan their contents.
7. Load technology rules from `rules/technology_rules/`.
8. Apply rules and build evidence-backed detections.
9. Write detailed JSON, JSONL, CSV summary, JSON summary, and discovery candidate output files.

One per-domain timeout is available through `--domain-timeout`. If a domain takes too long, the scraper skips that domain and continues with the next one without changing the output schema.

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
  technology_rules/
    a_rules.json
    b_rules.json
    ...

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

## Evidence Model

Every detected technology contains one or more evidence items:

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

- `type`: the kind of signal, such as `header`, `cookie`, `script_url`, `stylesheet_url`, `meta_generator`, `dom_marker`, `js_asset`, or `package_url`
- `source`: where the detector looked, such as `headers`, `cookies`, `html`, `url`, or `javascript`
- `location`: the exact location, such as `server`, `cookie_name`, `script[src]`, or `meta[name="generator"]`
- `matched_value`: the rule signature that matched
- `excerpt`: the concrete header, cookie, URL, HTML snippet, or JavaScript snippet
- `confidence`: the rule confidence, usually `high` or `medium`
- `explanation`: a human-readable reason for the detection

This model makes the output auditable. The scraper should not make unsupported claims; it should show the signal behind each claim. That is especially important when rules are expanded from discovery data because false positives are easier to inspect and fix when the evidence is visible.

## Rule System

Rules are stored in alphabetically split JSON files under `rules/technology_rules/`. The split keeps the rule set browsable as it grows. The current rule files contain 2933 technology rules.

A rule can include different signature types:

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

The rules favor strict signatures: vendor domains, product-specific cookie names, exact headers, recognizable CDN paths, package names, meta generator values, and stable DOM markers. Generic words such as `app`, `server`, `cloud`, `script`, or `analytics` are avoided as standalone signatures because they can create false positives.

## JavaScript Asset Scanning

Some technologies do not appear directly in the HTML but do appear inside JavaScript bundles or vendor files. The project includes a limited JavaScript asset scanner in `src/javascript_asset_fetcher.py`.

The scanner:

- extracts script URLs from the page
- skips non-fetchable pseudo URLs such as `data:`, `blob:`, and `javascript:`
- scores scripts so CDNs, bundles, vendor files, app files, and analytics files are more likely to be inspected
- fetches up to 5 JavaScript assets per domain
- uses a short per-asset request timeout
- reads at most 500 KB from each asset
- sends the fetched content to the same rule-based detector

This improves coverage while keeping the crawler simple. It is a middle ground between only scanning HTML and running a full browser.

## Output Files

Running the scraper writes these files under `data/output/`:

- `data/output/technology_detections.json`: full domain results with technologies, evidence, errors, and fetch metadata
- `data/output/technology_detections.jsonl`: one domain result per line, useful for larger processing jobs
- `data/output/technology_summary.csv`: compact row-based summary for spreadsheets or quick inspection
- `data/output/technology_summary.json`: aggregate counts, confidence distribution, and top technologies
- `data/output/discovery_candidates.json`: low-detection and undetected domains for rule improvement

`discovery_candidates.json` is intentionally separate from the main detection output. It is a research tool for future rules, not a new detection schema.

## Current Results

The metrics below are read from the current `data/output/technology_summary.json`, generated by the validation command `python main.py --limit 5 --rewrite 1`. They are run-specific; regenerate them with `python main.py --rewrite 1` before a final full benchmark run.

Because timed-out domains are skipped without adding output fields, a limited run can contain fewer result records than the requested limit.

- total domains in the current summary: 4
- reachable domains: 4
- total findings: 13
- unique technologies: 8
- confidence distribution: 12 high, 1 medium

Top technologies in the current summary:

- Cloudflare: 4 domains
- Cloudflare Bot Management: 3 domains
- Canva Websites: 1 domain
- Luxury Presence: 1 domain
- Kinsta: 1 domain
- WordPress: 1 domain
- Cloudflare Web Analytics: 1 domain
- Tailwind CSS: 1 domain

## How The Solution Evolved

The project started with simple homepage fetching and basic signatures. It then improved in stages:

1. Added structured evidence so every detection explains itself.
2. Collected response headers and cookies because many ecommerce, analytics, security, and hosting tools expose stable names there.
3. Parsed HTML for script URLs, stylesheet URLs, meta generator tags, and DOM markers.
4. Added limited JavaScript asset scanning for technologies that appear inside bundles.
5. Split rules alphabetically to make a growing rule set maintainable.
6. Added JSONL, CSV, JSON summary, and discovery candidate outputs.
7. Used discovery reports from real crawl data to reinforce rules.
8. Reviewed curated external signature sources carefully while avoiding blind copying and license risk.

The development loop was: run a small sample, inspect evidence, add focused rules, add tests for important paths, rerun, and compare summary/discovery output.

## Main Issues And How They Were Handled

False positives are the biggest risk in rule-based detection. The project handles this by preferring specific signatures over generic text and by attaching evidence to every finding.

False negatives are also expected because some technologies only appear after JavaScript execution, login, consent interaction, geolocation, or browser-specific behavior. The project reduces this with headers, cookies, DOM markers, CDN package extraction, and limited JavaScript asset scanning, while still staying static.

Rule maintainability becomes harder as coverage grows. Splitting rules alphabetically and keeping one clear schema for all rule files makes the rule database easier to review.

Network issues are normal when crawling real websites. Some domains fail DNS, block automated requests, redirect unexpectedly, return challenge pages, or take too long. The scraper records fetch errors and uses a global per-domain timeout so one domain cannot block the full scan.

Static crawling has clear limits. It is faster and simpler than browser crawling, but it cannot observe client-side runtime state. For this challenge, static crawling is a practical first layer because it captures many useful website technologies without the cost of a browser.

External technology signatures can help, but they must be handled carefully. Open-source databases should only be used after license review, and new signatures should still be tested against real evidence instead of copied blindly.

## Scaling To Millions Of Domains

For millions of domains, I would keep the evidence-based detector but change the execution architecture:

- store domains in a queue such as Kafka, SQS, RabbitMQ, or RQ instead of a local text file
- run many worker processes or containers
- store raw fetch metadata and detections in S3/GCS plus a database such as Postgres, BigQuery, or ClickHouse
- write JSONL or columnar batches instead of keeping all results in memory
- enforce strict timeouts, retry limits, maximum response sizes, and per-domain budgets
- deduplicate and normalize domains before crawling
- cache repeated assets and known signatures
- separate static crawling from slower browser-based deep crawling
- send only low-detection or JavaScript-heavy domains to Playwright/browser analysis
- monitor crawl success rate, average time per domain, error rates, findings per domain, and confidence distribution
- respect robots.txt where applicable, rate limits, terms of service, and legal requirements

Scrapy could be useful at larger scale because it provides mature crawling primitives such as concurrency, retries, middlewares, throttling, and pipelines. However, the key challenge remains the evidence-based technology detector, not just the crawler framework.

## Discovering New Technologies

I would discover new technologies by building a feedback loop around the crawler.

The scraper already produces `discovery_candidates.json`, which groups domains with zero or low detections. Future discovery work should track repeated unknown signals:

- unknown script domains
- unknown stylesheet domains
- unknown cookie names
- unknown HTTP headers
- repeated JavaScript asset patterns
- unknown meta generator values
- package names from CDN URLs
- recurring DOM attributes or HTML markers

Strong repeated signals should be grouped, manually reviewed, converted into explicit rules, covered by tests, and validated by rerunning the crawler. The before/after comparison should use `technology_summary.json` and `discovery_candidates.json`.

For domains where the normal scraper finds fewer than a threshold number of technologies, for example fewer than 2 or 3, I would send them to a slower deep analysis workflow. That workflow could use a browser crawler and optionally an AI agent to inspect pages, network requests, scripts, and DOM state. The AI should not directly write final detections without evidence. Instead, it should propose candidate technologies and candidate signatures. Those candidates would then be manually reviewed or automatically validated before being added to the rule database.

Detection should remain deterministic and evidence-based. AI can help with discovery, but final production rules should still be explicit, testable, and auditable.

## Running The Project

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the unit tests:

```bash
python -m unittest discover
```

Run a small validation sample:

```bash
python main.py --limit 5 --rewrite 1
```

Run a larger development sample:

```bash
python main.py --limit 20 --rewrite 1
```

Run the full input list:

```bash
python main.py --rewrite 1
```

Run the full input list with the default per-domain timeout stated explicitly:

```bash
python main.py --rewrite 1 --domain-timeout 15
```

The script prints the fetch result, fetched JavaScript asset count, detections with evidence, output file paths, unique technology count, and total detection count.

## CLI Options

- `--rewrite 1`: delete old output files before writing new results
- `--rewrite 0`: append new results to existing JSON/JSONL/CSV outputs
- `--limit N`: process only the first `N` normalized domains
- `--domain-timeout SECONDS`: maximum seconds allowed for processing one domain, default `15`

## Tests

The test suite focuses on the detector and rule behavior. It covers:

- raw HTML signatures
- HTTP header signatures
- cookie signatures
- domain and final URL signatures
- script URL signatures
- stylesheet URL signatures
- meta generator signatures
- DOM marker signatures
- JavaScript asset signatures
- package URL signatures
- selected reinforced rules and false-positive guards

Run:

```bash
python -m unittest discover
```

## Limitations

- JavaScript assets are fetched and inspected, but JavaScript is not executed.
- Browser-only runtime behavior is not observed.
- Some websites block automated requests or return challenge pages.
- Some backend technologies do not expose public signatures.
- Some detections are only medium confidence because the signal is indirect.
- Results can vary with redirects, location, cookies, A/B tests, bot protection, and response time.
- The JavaScript asset scanner is intentionally limited to keep the project readable and avoid heavy crawling.

These limitations are why the evidence model is central to the project.
