# Website Technologies Scraper

## 0. README Contents

This README follows this order:

1. Project Overview
2. Challenge Requirements
3. Final Results
4. Quick Start
5. Repository Structure
6. Input Data and Domain Extraction
7. Crawling Approach
8. Technology Detection Strategy
9. Evidence Model
10. Confidence Levels
11. Output Format
12. Output Files
13. Example Detections
14. Rule Quality and False Positive Guardrails
15. Technology Signature Sources
16. Testing and Validation
17. Main Limitations
18. Scaling To Millions Of Domains
19. Discovering New Technologies In The Future
20. Design Decisions
21. Future Improvements
22. Reproducibility Checklist
23. Submission Notes

## 1. Project Overview

Website Technologies Scraper is a static, evidence-driven crawler built for the Veridion Website Technologies Scraper challenge. The input is a cleaned list of 200 domains, and the goal is to detect visible web technologies used by each website.

The project was created from the perspective of delivering a qualitative output rather than a purely quantitative one. The goal was not to maximize the number of labels at any cost, but to avoid false positives as much as possible and create a system with a correct, trustworthy output. Another important intention was to build a reliable environment where technology rules can be implemented, tested, reviewed, and improved with clear evidence.

The project prioritizes trustworthy, evidence-backed detections over inflated technology counts. Instead of relying on broad signatures that may produce noisy or misleading results, every detection is tied to concrete proof explaining why a technology was identified. This makes the output easier to review, helps spot potential false positives, and allows the rule set to improve over time.

AI could have been useful for discovering new or niche technologies that were not detected by the normal rule set. However, I did not treat AI as a core requirement for this challenge. Instead, I kept the final detector deterministic and evidence-based, and I describe AI-assisted discovery as a future improvement.

## 2. Challenge Requirements

The challenge asks for a scraper that can:

- process the provided website/domain list;
- gather as many relevant website technologies as possible;
- provide proof for each detection;
- generate output files with the detected technologies;
- explain the technical approach;
- discuss limitations, scaling, and future technology discovery.

This repository answers the assignment with a deterministic rule-based detector, structured evidence, JSON/JSONL/CSV outputs, tests, and a discovery report for future rule improvements.

## 3. Final Results

The metrics below are read from the current `data/output/technology_summary.json`, generated from the full input list with:

```bash
python main.py --rewrite 1 --domain-timeout 15
```

| Metric | Value |
| --- | ---: |
| Input domains | 200 |
| Output entries | 200 |
| Reachable domains | 168 |
| Domains with at least one technology | 168 |
| Total detections | 941 |
| Unique technologies found | 200 (pure coincidence, not intended to be equal to the number of input domains) |
| Average technologies per input domain | 4.71 |
| Average technologies per reachable domain | 5.60 |
| High confidence detections | 818 |
| Medium confidence detections | 123 |
| Low confidence detections | 0 |
| Error or timeout entries | 32 |
| Timeout entries | 32 |
| Maximum evidence items per technology | 10 |

Top technologies in the current output:

| Technology | Domains |
| --- | ---: |
| WordPress | 62 |
| jQuery | 50 |
| Cloudflare | 45 |
| Google Fonts | 42 |
| Apache HTTP Server | 39 |
| Font Awesome | 33 |
| Google Analytics | 27 |
| reCAPTCHA | 25 |
| Nginx | 25 |
| PHP | 22 |

Timed-out or failed domains are kept as empty result entries with the existing output schema, so the full run contains one top-level result per input domain.

## 4. Quick Start

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.\.venv\Scripts\activate
```

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
python main.py --rewrite 1 --domain-timeout 15
```

Domain extraction is performed automatically by `main.py` through `src/extract_domains.py`. The script prints fetch information, fetched JavaScript asset counts, detections with evidence, output file paths, unique technology count, and total detection count.

## 5. Repository Structure

```text
data/
  input/domains.txt
  raw/domains.snappy.parquet
  output/

rules/
  technology_rules/

src/
  console_output.py
  discovery_candidates.py
  domain_processor.py
  extract_domains.py
  javascript_asset_fetcher.py
  output_writer.py
  technology_detector.py
  technology_rules.py
  website_fetcher.py

tests/
  test_technology_detector.py
  test_website_fetcher.py

main.py
requirements.txt
README.md
```

- `data/raw/domains.snappy.parquet`: raw input dataset.
- `data/input/domains.txt`: normalized domain list generated from the raw input.
- `data/output/`: generated JSON, JSONL, CSV, summary, and discovery files.
- `rules/technology_rules/`: alphabetically split JSON rule files.
- `src/console_output.py`: prints fetch metadata and detected technologies to the console.
- `src/discovery_candidates.py`: records low-detection domains for future rule research.
- `src/domain_processor.py`: runs the per-domain fetch, JavaScript asset scan, technology detection, timeout, and failure handling.
- `src/extract_domains.py`: reads and normalizes input domains.
- `src/javascript_asset_fetcher.py`: selects and fetches a limited number of JavaScript assets.
- `src/output_writer.py`: builds result records and writes JSON, JSONL, CSV, and summary outputs.
- `src/technology_detector.py`: applies loaded rules and produces evidence-backed detections.
- `src/technology_rules.py`: defines rule and detection data models, loads rule files, and extracts package names from known CDN URLs.
- `src/website_fetcher.py`: fetches homepages and stores fetch metadata.
- `tests/test_technology_detector.py`: detector, evidence, and false-positive tests.
- `tests/test_website_fetcher.py`: website fetcher tests.
- `main.py`: CLI entry point that wires extraction, processing, output writing, and discovery together.

There are no `scripts/` or `configs/` directories in the current project.

## 6. Input Data and Domain Extraction

The raw input file is:

```text
data/raw/domains.snappy.parquet
```

The input contains a `root_domain` column. Domain extraction is implemented in:

```text
src/extract_domains.py
```

The extraction step:

- reads the Parquet file with pandas;
- selects the `root_domain` column;
- removes missing values;
- converts values to strings;
- trims whitespace;
- removes empty strings;
- lowercases domains;
- deduplicates domains;
- sorts the final list;
- writes the normalized result to `data/input/domains.txt`.

The exact command used in normal runs is the main scraper command:

```bash
python main.py --rewrite 1 --domain-timeout 15
```

`main.py` calls `extract_domains(RAW_INPUT_PATH, DOMAINS_OUTPUT_PATH)` before crawling.

## 7. Crawling Approach

Website fetching is implemented in `src/website_fetcher.py`.

For each domain, the scraper:

- tries `https://domain` first;
- falls back to `http://domain` if HTTPS fails;
- follows redirects;
- stores the original domain;
- stores attempted URLs;
- stores the successful URL;
- stores the final URL after redirects;
- stores the HTTP status code;
- stores response headers;
- stores response cookies;
- stores HTML content;
- stores content type;
- stores redirect count;
- stores elapsed time in milliseconds;
- stores an error message if fetching fails.

Browser-like request headers are used so many sites return their normal homepage instead of a simplified bot response.

The scraper has one global per-domain timeout:

```bash
--domain-timeout 15
```

The timeout covers homepage fetching, JavaScript asset fetching, and technology detection for that domain. If the timeout is exceeded, the domain is kept in the output as an empty result with a clear error message. This preserves one output entry per input domain without adding fields to the schema.

The project does not implement retries, rate limiting, async crawling, Scrapy, or browser crawling. Those are discussed as production-scale improvements later in this README.

## 8. Technology Detection Strategy

Rule loading and typed rule models are implemented in `src/technology_rules.py`. Technology detection and evidence collection are implemented in `src/technology_detector.py`.

The detector is rule-based. Rules are stored under:

```text
rules/technology_rules/
```

The current rule files contain 2933 technology rules. They are split alphabetically by technology name so the rule set remains browsable as it grows.

The detector uses these evidence sources:

- HTTP headers;
- response cookies;
- original domain;
- final redirected URL;
- raw HTML;
- meta generator tags;
- script URLs from `<script src="...">`;
- stylesheet URLs from `<link href="...">`;
- DOM attributes and markers;
- selected JavaScript asset contents;
- package-like CDN URLs from jsDelivr, unpkg, cdnjs, esm.sh, and Skypack.

Rule-based detection was chosen because it is:

- deterministic;
- explainable;
- easy to debug;
- easy to test;
- safer for false-positive review;
- able to produce evidence for every match.

A black-box model could suggest candidate technologies, but it would be harder to trust as the final production detector unless each claim was converted into explicit, testable signatures.

## 9. Evidence Model

Evidence means the concrete signal that caused a technology to be detected. Every detection contains one or more evidence items.

Each evidence item includes:

- `type`;
- `source`;
- `location`;
- `matched_value`;
- `excerpt`;
- `confidence`;
- `explanation`.

Example:

```json
{
  "name": "Cloudflare",
  "category": "CDN / Security",
  "confidence": "high",
  "evidence": [
    {
      "type": "header",
      "source": "headers",
      "location": "server",
      "matched_value": "cloudflare",
      "excerpt": "server: cloudflare",
      "confidence": "high",
      "explanation": "Found 'cloudflare' in HTTP header 'server'."
    }
  ]
}
```

Evidence fields:

- `type`: the kind of signal, such as `header`, `cookie`, `script_url`, `stylesheet_url`, `meta_generator`, `dom_marker`, `js_asset`, or `package_url`.
- `source`: where the detector looked, such as `headers`, `cookies`, `html`, `url`, or `javascript`.
- `location`: the exact location, such as `server`, `cookie_name`, `script[src]`, or `meta[name="generator"]`.
- `matched_value`: the rule signature that matched.
- `excerpt`: the concrete header, cookie, URL, HTML snippet, or JavaScript snippet.
- `confidence`: the confidence level from the rule.
- `explanation`: a human-readable explanation of the detection.

The evidence model makes the output auditable. The scraper should not make unsupported claims; it should show the signal behind each claim.

## 10. Confidence Levels

The project mainly uses `high` and `medium` confidence. Low-confidence rules are intentionally avoided because weak signatures are likely to create noisy output.

- `high`: explicit and vendor-specific evidence, such as official script URLs, exact headers, unique cookies, meta generator values, or official CDN paths.
- `medium`: strong but slightly less direct evidence, such as a reliable HTML marker, package URL, JavaScript library marker, or asset path.

Examples of high-confidence evidence:

- `server: cloudflare`;
- `cf-ray` header;
- `__cf_bm` cookie;
- `link: https://api.w.org`;
- `googletagmanager.com/gtag/js`;
- `fonts.googleapis.com/css`;
- `x-powered-by: WP Engine`.

Examples of signatures intentionally avoided or removed:

- generic words such as `app`, `server`, `cloud`, `script`, or `analytics`;
- Magento detection from generic `static/version`;
- Squarespace detection from a bare `Squarespace` string inside third-party JavaScript bundles;
- weak Medallia matches from unrelated map or generic bundle content.

## 11. Output Format

The main output file is:

```text
data/output/technology_detections.json
```

Each top-level result keeps this schema:

```json
{
  "domain": "example.com",
  "normalized_url": "https://example.com",
  "final_url": "https://www.example.com/",
  "status": 200,
  "technologies": [],
  "errors": [],
  "fetch_metadata": {
    "attempted_urls": [],
    "successful_url": "https://example.com",
    "elapsed_ms": 1234,
    "content_type": "text/html",
    "redirect_count": 1,
    "cookies": {},
    "javascript_assets": []
  }
}
```

Important fields:

- `domain`: input domain.
- `normalized_url`: the successful URL attempted by the fetcher.
- `final_url`: final URL after redirects.
- `status`: HTTP status code.
- `technologies`: detected technologies and their evidence.
- `errors`: fetch, timeout, or processing errors.
- `fetch_metadata`: attempted URLs, successful URL, elapsed time, content type, redirect count, cookies, and JavaScript asset metadata.

Timed-out and failed domains use the same structure. They have `final_url: null`, `status: null`, `technologies: []`, and a clear error message.

The project also writes JSONL, CSV summary, JSON summary, and discovery output. Parquet export is not implemented.

## 12. Output Files

Generated files:

- `data/output/technology_detections.json`: full evidence-based results for every input domain.
- `data/output/technology_detections.jsonl`: one domain result per line, useful for larger streaming or batch processing.
- `data/output/technology_summary.csv`: flat table with domain, final URL, status, technology name, category, confidence, evidence count, evidence types, first evidence, and errors.
- `data/output/technology_summary.json`: aggregate metrics, confidence distribution, and top technologies.
- `data/output/discovery_candidates.json`: undetected and low-detection domains for future rule improvement.

`discovery_candidates.json` is intentionally separate from the main result output. It is a research tool for new rules, not a new detection schema.

## 13. Example Detections

Examples from the current output:

| Domain | Technology | Evidence | Why it is reliable |
| --- | --- | --- | --- |
| `100wwcstlw.org` | Cloudflare | `__cf_bm` cookie and Cloudflare headers such as `cf-ray` / `server: cloudflare` | Cloudflare-specific cookie and headers are strong vendor signals. |
| `11thhourracing.org` | WordPress | `link` header containing `https://api.w.org` | `api.w.org` is a WordPress REST API discovery signal. |
| `2-com.net` | Google Analytics | script URL `https://www.googletagmanager.com/gtag/js?id=...` | The official Google tag URL is a direct analytics signal. |
| `11thhourracing.org` | Kinsta | headers such as `x-kinsta-cache`, `ki-edge`, and `ki-origin` | Vendor-specific Kinsta headers are explicit hosting evidence. |
| `100wwcstlw.org` | Canva Websites | `content-security-policy` containing `canva.com` and `csp.canva.com`, plus `x-deployment-id` | Canva website deployments expose specific CSP and deployment headers. |

The output may contain multiple evidence items for one technology. To reduce noise, evidence is capped at 10 items per technology per domain.

## 14. Rule Quality and False Positive Guardrails

False positives are the biggest risk in rule-based technology detection. The project uses conservative rule quality rules:

- avoid generic word matching;
- avoid standalone words such as `app`, `server`, `cloud`, `script`, `image`, or `analytics`;
- prefer vendor domains, exact cookies, exact headers, package URLs, meta generator values, and stable DOM markers;
- avoid detections from translation files or UI text where possible;
- avoid detections from consent-manager vendor catalogs that merely list many vendors;
- avoid detections from Google internal bundles except for Google products;
- avoid noisy duplicate aliases from the same evidence during rule review;
- keep only web technologies relevant to website technology detection;
- use conservative confidence levels;
- cap evidence items to avoid very noisy technology entries;
- add tests for important false-positive cases.

Recent guardrails include:

- Magento is not detected from `static1.squarespace.com/static/versioned-site-css/...`;
- Squarespace is not detected from a bare `Squarespace` string inside Google Tag Manager or analytics bundles;
- Medallia is not detected from unrelated Google Maps or generic JavaScript content;
- generic payment text does not detect payment providers;
- generic social links do not detect chat widgets;
- generic security headers do not invent security technologies.

Some related technologies may still share evidence when the rules intentionally model separate products. Those cases should be reviewed conservatively during rule maintenance.

## 15. Technology Signature Sources

Rules come from:

- manually curated signatures;
- real crawl evidence from the 200-domain dataset;
- `data/output/discovery_candidates.json`;
- selected external signature candidates reviewed manually;
- focused false-positive cleanup from test cases and output inspection.

External technology databases were not bulk imported. Bulk imports can introduce licensing risk and many false positives because signatures often need project-specific context. A candidate signature is accepted only when it has concrete evidence and fits the detector's evidence model.

The development loop is:

1. Run the scraper on a small sample.
2. Inspect evidence.
3. Add focused rules from concrete signals.
4. Add tests for important detection paths or false-positive risks.
5. Rerun the scraper.
6. Compare `technology_summary.json` and `discovery_candidates.json`.

## 16. Testing and Validation

The test suite is implemented in:

```text
tests/test_technology_detector.py
tests/test_website_fetcher.py
```

It covers:

- website fetching behavior;
- raw HTML signatures;
- HTTP header signatures;
- cookie signatures;
- domain and final URL signatures;
- script URL signatures;
- stylesheet URL signatures;
- meta generator signatures;
- DOM marker signatures;
- JavaScript asset signatures;
- package URL signatures;
- evidence field structure;
- selected reinforced rules;
- false-positive guardrail tests;
- evidence capping.

Run the tests:

```bash
python -m unittest discover
```

`pytest` is not listed in `requirements.txt`, so it is not required for reproducibility. If it is installed in the local environment, the unittest suite can also be run with:

```bash
python -m pytest -q
```

Validation commands used during development:

```bash
python -m unittest discover
python main.py --limit 20 --rewrite 1
python main.py --rewrite 1 --domain-timeout 15
```

## 17. Main Limitations

Current limitations:

- JavaScript assets are fetched and inspected, but JavaScript is not executed.
- Browser-only runtime behavior is not observed.
- Some websites block automated requests or return Cloudflare/security pages.
- Some domains fail DNS, SSL, or network fetching.
- Some technologies are intentionally hidden and expose no public signatures.
- Third-party bundles can create false positives if rules are too broad.
- Technology version detection is limited.
- Results can vary with redirects, location, cookies, A/B tests, bot protection, and response time.
- Browser mode would detect more runtime technologies but is more expensive.
- JavaScript asset scanning is intentionally limited to keep the project readable and avoid heavy crawling.

How these could be improved:

- add a browser-based deep scan for low-detection domains;
- add retries with backoff for transient network failures;
- add per-host rate limits for production crawling;
- add better version extraction for technologies with stable version markers;
- deduplicate JavaScript assets by URL or content hash;
- benchmark against labeled data;
- review low-confidence candidates manually before adding rules.

These limitations are why the evidence model is central to the project.

## 18. Scaling To Millions Of Domains

For millions of domains, I would keep the evidence-based detector but change the execution architecture. A realistic production target over 1-2 months would be a distributed static crawler with a slower browser tier for selected domains.

Scaling plan:

- store domains in a distributed queue such as Kafka, SQS, RabbitMQ, or RQ;
- run many worker processes or containers;
- use async HTTP workers or a mature crawler framework for higher throughput;
- enforce strict request timeouts, retry limits, response-size limits, and per-domain budgets;
- use retries with exponential backoff for transient failures;
- enforce per-host rate limits;
- cache DNS and HTTP results where appropriate;
- store raw crawl artifacts in S3/GCS or equivalent object storage;
- write detections to Postgres, BigQuery, ClickHouse, or Parquet datasets;
- keep JSONL or columnar batch outputs for streaming pipelines;
- deduplicate and normalize domains before crawling;
- deduplicate JavaScript assets by hash so common libraries are scanned once;
- cache repeated asset/signature matches;
- separate cheap static crawling from expensive browser crawling;
- send only low-detection or JavaScript-heavy domains to Playwright/browser analysis;
- monitor crawl success rate, average time per domain, error rates, throughput, findings per domain, and confidence distribution;
- respect robots.txt where applicable, rate limits, terms of service, and legal requirements.

Scrapy could be useful at larger scale because it provides mature crawling primitives such as concurrency, retries, middlewares, throttling, and pipelines. However, the key challenge remains the evidence-based technology detector, not just the crawler framework.

## 19. Discovering New Technologies In The Future

Future discovery should be a feedback loop around the crawler.

The project already writes:

```text
data/output/discovery_candidates.json
```

This file groups domains with zero detections or only a low number of detections. Future discovery work should:

- collect unknown script domains;
- collect unknown stylesheet domains;
- cluster frequent unknown cookie names;
- cluster frequent unknown HTTP headers;
- cluster unknown meta generator values;
- inspect high-frequency JavaScript asset URLs;
- inspect recurring package names from CDN URLs;
- inspect recurring DOM attributes and HTML markers;
- compare candidates against external databases carefully after license review;
- manually validate candidate rules;
- add tests for each important new rule;
- monitor false positives after every rule update;
- update signatures regularly as tools change.

For domains where the normal scraper finds fewer than a threshold number of technologies, for example fewer than 2 or 3, I would send them to a slower deep analysis workflow. That workflow could use a browser crawler and optionally an AI agent to inspect pages, network requests, scripts, and DOM state. The AI should not directly write final detections without evidence. Instead, it should propose candidate technologies and candidate signatures. Those candidates would then be manually reviewed or automatically validated before being added to the rule database.

Detection should remain deterministic and evidence-based. AI can help with discovery, but final production rules should still be explicit, testable, and auditable.

## 20. Design Decisions

Important choices:

- Rule-based detection instead of ML/LLM for final detections.
- Evidence-first schema so every claim can be inspected.
- JSON output for full result review.
- JSONL output for streaming and larger batch workflows.
- CSV summary for spreadsheet inspection.
- JSON summary for aggregate metrics and top technologies.
- Conservative signatures instead of broad keyword matching.
- Static crawl first, optional browser crawl later.
- Limited JavaScript asset scanning as a middle ground between HTML-only and browser crawling.
- Alphabetically split rule files for maintainability.
- One global per-domain timeout instead of a complex time-budget system.
- Keep timed-out domains in output without changing the schema.
- No bulk import of external signature databases.
- Discovery candidates separated from main results so future research does not change the detection schema.

These choices are meant to keep the project simple, auditable, and practical for the challenge.

## 21. Future Improvements

Possible improvements:

- Playwright/browser deep scan for low-detection or JavaScript-heavy domains;
- better JavaScript asset prioritization;
- JavaScript asset caching and hash-based deduplication;
- technology version extraction;
- better scoring model for evidence quality;
- dashboard for browsing detections and evidence;
- more tests for high-risk false positives;
- automatic signature discovery from repeated unknown signals;
- better retry and backoff logic;
- rate limiting;
- Parquet export;
- benchmark against labeled data;
- more category cleanup and alias review;
- optional comparison against licensed external technology databases.

These are future improvements, not current dependencies or requirements.

## 22. Reproducibility Checklist

1. Create and activate a virtual environment:

```bash
python -m venv .venv
.\.venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run tests:

```bash
python -m unittest discover
```

4. Run a small smoke test:

```bash
python main.py --limit 5 --rewrite 1
```

5. Run a larger validation sample:

```bash
python main.py --limit 20 --rewrite 1
```

6. Run the full scraper and generate outputs:

```bash
python main.py --rewrite 1 --domain-timeout 15
```

7. Inspect final metrics:

```text
data/output/technology_summary.json
```

8. Inspect full evidence-based results:

```text
data/output/technology_detections.json
```

## 23. Submission Notes

Repository:

```text
https://github.com/TaradaciucNicolae/website-technologies-scraper
```

Final output files are located in:

```text
data/output/
```

The main evidence-based result is:

```text
data/output/technology_detections.json
```

The aggregate metrics are in:

```text
data/output/technology_summary.json
```

This README documents the approach, results, limitations, scaling plan, and future discovery process.

The most important point: this project is not only scraping websites. It is building a reliable evidence-based technology detection pipeline where quality and proof matter more than inflated detection counts.
