# Website Technologies Scraper


## Domain Extraction

The raw input file is stored at `data/raw/domains.snappy.parquet`.  
The `scripts/extract_domains.py` script reads this Parquet file, inspects its columns, extracts the `root_domain` values, removes empty entries and duplicates, normalizes the domains, and writes the cleaned list to `data/domains.txt`.