from pathlib import Path
from src.extract_domains import extract_domains
from src.website_fetcher import WebsiteFetchResult, fetch_website

RAW_INPUT_PATH = Path("data/raw/domains.snappy.parquet")
DOMAINS_OUTPUT_PATH = Path("data/domains.txt")


def print_fetch_result(result: WebsiteFetchResult) -> None:
    print("=" * 80)
    print(f"Domain:       {result.domain}")
    print(f"Attempted:    {', '.join(result.attempted_urls)}")
    print(f"Successful:   {result.successful_url or '-'}")
    print(f"Final URL:    {result.final_url or '-'}")
    print(f"Status code:  {result.status_code or '-'}")
    print(f"Headers:      {len(result.headers)}")
    print(f"HTML length:  {len(result.html)} characters")
    print(f"Error:        {result.error or '-'}")
    

def main() -> None:
    domains = extract_domains(RAW_INPUT_PATH, DOMAINS_OUTPUT_PATH)



    for domain in domains[:3]:
        domain = domain.strip()

        if not domain:
            continue

        result = fetch_website(domain)
        print_fetch_result(result)















if __name__ == "__main__":
    main()