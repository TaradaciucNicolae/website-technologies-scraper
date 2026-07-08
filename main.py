from pathlib import Path
from src.extract_domains import extract_domains
from src.website_fetcher import WebsiteFetchResult, fetch_website

from src.technology_detector import (
    TechnologyDetection,
    detect_technologies,
    load_technology_rules,
)

RULES_PATH = Path("rules/technology_rules.json")
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
    

def print_detected_technologies(detections: list[TechnologyDetection]) -> None:
    print("Technologies:")

    if not detections:
        print("  - None detected")
        return

    for detection in detections:
        print(f"  - {detection.name} ({detection.category}, confidence: {detection.confidence})")

        for evidence in detection.evidence:
            print(f"      Evidence: [{evidence.source}] {evidence.matched}")
            print(f"      Explanation: {evidence.explanation}")



def main() -> None:
    domains = extract_domains(RAW_INPUT_PATH, DOMAINS_OUTPUT_PATH)
    rules = load_technology_rules(RULES_PATH)


    for domain in domains[:3]:
        domain = domain.strip()

        if not domain:
            continue

        result = fetch_website(domain)
        detections = detect_technologies(
            html=result.html,
            headers=result.headers,
            rules=rules
        )

        print_fetch_result(result)
        print_detected_technologies(detections)





if __name__ == "__main__":
    main()