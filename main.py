from pathlib import Path

import json
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
RESULTS_OUTPUT_PATH = Path("data/output/technology_detections.json")


def print_fetch_result(result: WebsiteFetchResult) -> None:
    print("=" * 120)
    print(f"Domain:       {result.domain}")
    print(f"Attempted:    {', '.join(result.attempted_urls)}")
    print(f"Successful:   {result.successful_url or '-'}")
    print(f"Final URL:    {result.final_url or '-'}")
    print(f"Status code:  {result.status_code or '-'}")
    print(f"Elapsed:      {result.elapsed_ms if result.elapsed_ms is not None else '-'} ms")
    print(f"Content type: {result.content_type or '-'}")
    print(f"Redirects:    {result.redirect_count}")
    print(f"Headers:      {len(result.headers)}")
    print(f"HTML length:  {len(result.html)} characters")
    print(f"Error:        {result.error or '-'}")
    

def print_detected_technologies(detections: list[TechnologyDetection]) -> None:
    print("Technologies:")

    if not detections:
        print("  - None detected")
        return

    for detection in detections:
        print("-" * 60)
        print(f"  - {detection.name} ({detection.category}, confidence: {detection.confidence})")

        for evidence in detection.evidence:
            print(f"Evidence: [{evidence.type}] {evidence.location} -> {evidence.matched_value}")
            print(f"Excerpt: {evidence.excerpt}")
            print(f"Explanation: {evidence.explanation}")





def build_result_record(
    fetch_result: WebsiteFetchResult,
    detections: list[TechnologyDetection],
) -> dict:

    technologies: list[dict] = []

    for detection in detections:
        evidence_items: list[dict] = []

        for evidence in detection.evidence:
            evidence_items.append(
                {
                    "type": evidence.type,
                    "source": evidence.source,
                    "location": evidence.location,
                    "matched_value": evidence.matched_value,
                    "excerpt": evidence.excerpt,
                    "confidence": evidence.confidence,
                    "explanation": evidence.explanation,
                }
            )

        technologies.append(
            {
                "name": detection.name,
                "category": detection.category,
                "confidence": detection.confidence,
                "evidence": evidence_items,
            }
        )

    errors: list[str] = []

    if fetch_result.error is not None:
        errors.append(fetch_result.error)

    return {
        "domain": fetch_result.domain,
        "normalized_url": fetch_result.successful_url,
        "final_url": fetch_result.final_url,
        "status": fetch_result.status_code,
        "technologies": technologies,
        "errors": errors,
        "fetch_metadata": {
            "attempted_urls": fetch_result.attempted_urls,
            "successful_url": fetch_result.successful_url,
            "elapsed_ms": fetch_result.elapsed_ms,
            "content_type": fetch_result.content_type,
            "redirect_count": fetch_result.redirect_count,
        },
    }



def main() -> None:
    domains = extract_domains(RAW_INPUT_PATH, DOMAINS_OUTPUT_PATH)
    rules = load_technology_rules(RULES_PATH)
    results: list[dict] = []

    for domain in domains[:10]:
        domain = domain.strip()

        if not domain:
            continue

        result = fetch_website(domain)
        detections = detect_technologies(
            domain=result.domain,
            final_url=result.final_url,
            html=result.html,
            headers=result.headers,
            rules=rules
        )

        print_fetch_result(result)
        print_detected_technologies(detections)

        results.append(build_result_record(result, detections))


    RESULTS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_OUTPUT_PATH.write_text(json.dumps(results, indent=2),encoding="utf-8",)
    print(f"Saved results to {RESULTS_OUTPUT_PATH}")
    
    different_technologies: set[str] = set()

    for result_record in results:
        technologies = result_record["technologies"]

        for technology in technologies:
            technology_name = technology["name"]
            different_technologies.add(technology_name)

    print(f"Different technologies found: {len(different_technologies)}")

if __name__ == "__main__":
    main()