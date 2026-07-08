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