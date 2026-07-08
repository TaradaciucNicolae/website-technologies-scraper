# Website Technologies Scraper


## Domain Extraction

The raw input file is stored at `data/raw/domains.snappy.parquet`.  
The `src/extract_domains.py` script reads this Parquet file, inspects its columns, extracts the `root_domain` values, removes empty entries and duplicates, normalizes the domains, and writes the cleaned list to `data/domains.txt`.


## Website Fetching

The scraper reads domains from `data/domains.txt` and tries to fetch each website using HTTPS first, then HTTP as a fallback.

For each domain, the fetcher stores:

- the original domain
- all attempted URLs
- the URL that successfully returned a response, if any
- the final URL after redirects
- the HTTP status code
- response headers
- HTML content
- an error message when both HTTPS and HTTP fail

This separation is useful because the technology detector will later use both the response headers and the HTML body as evidence.



## Technology Detection

Technology detection is based on configurable rules stored in `rules/technology_rules.json`.

Each rule defines:

- the technology name
- the technology category
- a confidence level
- HTML signatures
- HTTP header signatures

The detector checks both the fetched HTML and the response headers. When a rule matches, the result includes evidence that explains why the technology was detected.

For example:

- `cdn.shopify.com` in HTML is evidence for Shopify
- `wp-content` in HTML is evidence for WordPress
- `googletagmanager.com` in HTML is evidence for Google Tag Manager
- `server: cloudflare` or the presence of `cf-ray` is evidence for Cloudflare

Rules are stored outside the Python code so new technologies can be added by editing the JSON file.


## Confidence Levels

The current implementation uses rule-level confidence values.

- `high`: strong and specific signatures, such as official CDN domains or vendor-specific headers
- `medium`: useful but less specific signatures
- `low`: weak signals that may need additional evidence

The first rules use `high` confidence because they rely on specific technology signatures.





## Testing

The detector is covered with unit tests using Python's built-in `unittest` module.