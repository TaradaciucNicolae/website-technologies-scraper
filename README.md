# Website Technologies Scraper

This project detects technologies used by websites from a list of input domains.

For each domain, the scraper fetches the website, applies rule-based technology detection, and saves the detected technologies together with concrete evidence. The evidence explains why a technology was detected and where the matching signal was found.

The project is designed around the following pipeline:

1. extract and clean input domains
2. fetch each website
3. detect technologies from multiple evidence sources
4. save detailed and summary outputs

## Project Structure

```text
data/
  domains.txt
  raw/domains.snappy.parquet
  output/technology_detections.json
  output/technology_detections.jsonl
  output/technology_summary.csv

rules/
  technology_rules.json

src/
  extract_domains.py
  website_fetcher.py
  technology_detector.py

tests/
  test_technology_detector.py

main.py
requirements.txt
README.md
```

## Input Data

The raw input file is stored at:

```text
data/raw/domains.snappy.parquet
```

`src/extract_domains.py` reads the Parquet file, extracts domain values, removes empty entries and duplicates, normalizes the domains, and writes the cleaned list to:

```text
data/domains.txt
```

Reason: the scraper should work with a clean and predictable domain list before fetching websites.

## Website Fetching

Website fetching is implemented in:

```text
src/website_fetcher.py
```

For every domain, the fetcher tries:

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
- error message, if fetching fails

Reason: technology evidence can appear in different parts of a response. Headers, cookies, final URLs, redirects, and HTML content can all provide useful detection signals.

## Technology Detection

Technology detection is implemented in:

```text
src/technology_detector.py
```

Detection rules are stored in:

```text
rules/technology_rules.json
```

The detector checks each website response against configurable signatures. A technology is detected when at least one signature from its rule matches.

Rules can use these signature groups:

- `domain_signatures`
- `html_signatures`
- `script_url_signatures`
- `stylesheet_url_signatures`
- `meta_generator_signatures`
- `dom_marker_signatures`
- `cookie_signatures`
- `header_signatures`

Reason: separating signatures by source makes the rules easier to understand and produces more precise evidence. For example, a match in `script[src]` is more specific than a match somewhere in the raw HTML.

## Structured HTML Parsing

The detector uses BeautifulSoup to parse HTML and extract structured evidence from:

- script URLs: `<script src="...">`
- stylesheet URLs: `<link href="...">`
- meta generator tags: `<meta name="generator" ...>`
- DOM attributes and markers

Reason: structured parsing makes the evidence more accurate. Instead of only saying that a signature appeared somewhere in the HTML, the detector can report that it appeared specifically in a script URL, stylesheet URL, meta tag, or DOM attribute.

## Evidence Model

Each detected technology includes evidence items.

Example:

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

- `type`: type of evidence found
- `source`: source inspected by the detector
- `location`: exact location of the match
- `matched_value`: signature that matched
- `excerpt`: concrete response snippet or value
- `confidence`: confidence level from the rule
- `explanation`: readable explanation of the match

Supported evidence types:

- `html_contains`
- `script_url`
- `stylesheet_url`
- `meta_generator`
- `dom_marker`
- `header`
- `cookie`
- `domain`

Reason: the output should not only list technologies. It should also explain why each technology was detected.

## Example Detection Signals

Examples of supported signals:

- Shopify from `cdn.shopify.com` in a script URL
- WordPress from `wp-content` in script or stylesheet URLs
- Cloudflare from `server: cloudflare` or `cf-ray`
- Google Analytics from `_ga` cookies or analytics script URLs
- React from `data-reactroot`
- Drupal from a `meta generator` tag
- Amazon CloudFront from CloudFront headers
- Microsoft Clarity from `_clck` or `_clsk` cookies

## Output Files

Running the project creates output files in:

```text
data/output/
```

### Detailed JSON

```text
data/output/technology_detections.json
```

This file contains the full result list. It is useful for inspecting complete detections and all evidence items.

Each result contains:

- domain
- normalized URL
- final URL
- status
- detected technologies
- errors
- fetch metadata

### JSONL

```text
data/output/technology_detections.jsonl
```

This file stores one domain result per line.

Reason: JSONL is easier to process line by line and works better for larger datasets.

### CSV Summary

```text
data/output/technology_summary.csv
```

This file contains a compact summary that can be opened in spreadsheet tools.

It includes:

- domain
- final URL
- status
- number of technologies found
- technology name
- category
- confidence
- evidence count
- evidence types
- first evidence
- errors

Reason: the CSV output is useful for quickly reviewing results without opening the full JSON structure.

## Output Record Example

A result record follows this general structure:

```json
{
  "domain": "example.com",
  "normalized_url": "https://example.com",
  "final_url": "https://www.example.com/",
  "status": 200,
  "technologies": [
    {
      "name": "Shopify",
      "category": "Ecommerce",
      "confidence": "high",
      "evidence": [
        {
          "type": "script_url",
          "source": "html",
          "location": "script[src]",
          "matched_value": "cdn.shopify.com",
          "excerpt": "https://cdn.shopify.com/app.js",
          "confidence": "high",
          "explanation": "Found 'cdn.shopify.com' in a script URL."
        }
      ]
    }
  ],
  "errors": [],
  "fetch_metadata": {
    "attempted_urls": ["https://example.com"],
    "successful_url": "https://example.com",
    "elapsed_ms": 1234,
    "content_type": "text/html",
    "redirect_count": 1,
    "cookies": {}
  }
}
```

## Installation

Install dependencies with:

```bash
pip install -r requirements.txt
```

Dependencies:

- `pandas`
- `pyarrow`
- `requests`
- `beautifulsoup4`

## Running the Scraper

Run:

```bash
python main.py
```

The script will:

1. extract domains
2. fetch websites
3. detect technologies
4. write JSON, JSONL, and CSV outputs
5. print detection summary counts

At the end, it prints:

```text
Different technologies found: X
Total technologies found: Y
```

`Different technologies found` is the number of unique technology names.

`Total technologies found` is the total number of technology detections across all processed domains.

## Running Tests

Run:

```bash
python -m unittest discover
```

The tests cover:

- raw HTML detection
- header detection
- domain detection
- cookie detection
- script URL evidence
- stylesheet URL evidence
- meta generator evidence
- DOM marker evidence
- selected expanded technology rules

## Adding New Technology Rules

New technologies can be added by editing:

```text
rules/technology_rules.json
```

Example:

```json
{
  "name": "Example Technology",
  "category": "Example Category",
  "confidence": "high",
  "domain_signatures": [],
  "html_signatures": [],
  "script_url_signatures": ["example-cdn.com"],
  "stylesheet_url_signatures": [],
  "meta_generator_signatures": [],
  "dom_marker_signatures": [],
  "cookie_signatures": [],
  "header_signatures": {}
}
```


## Current Detection Coverage

The current rule set includes technologies from several categories:

- CMS platforms
- ecommerce platforms
- analytics tools
- marketing tools
- customer support tools
- JavaScript frameworks
- CSS frameworks
- backend frameworks
- hosting providers
- CDN and security providers
- monitoring tools
- build tools

## Limitations

The detector works only with information visible in the fetched response.

Important limitations:

- JavaScript is not executed
- browser-only runtime behavior is not observed
- some backend technologies do not expose public signatures
- some sites may block automated requests
- some signatures may produce false positives if they are too generic
- results depend on the HTML, headers, cookies, and URLs returned at fetch time

Because of these limitations, every detection includes evidence so the result can be inspected and justified.

## Current Status

The project currently supports detection from:

- domain and final URL
- raw HTML
- script URLs
- stylesheet URLs
- meta generator tags
- DOM attributes
- HTTP headers
- cookies

It exports:

- detailed JSON
- JSONL
- CSV summary

