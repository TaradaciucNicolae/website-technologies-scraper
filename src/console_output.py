from src.technology_rules import TechnologyDetection
from src.website_fetcher import WebsiteFetchResult


# Prints the fetch metadata for one domain so a scan can be inspected from the console.
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
    print(f"Cookies:      {len(result.cookies)}")
    print(f"HTML length:  {len(result.html)} characters")
    print(f"Error:        {result.error or '-'}")


# Prints every detected technology and its evidence for one processed domain.
def print_detected_technologies(detections: list[TechnologyDetection]) -> None:
    print("Technologies:")

    if not detections:
        print("  - None detected")
        return

    for detection in detections:
        print("\n","-" * 60)
        print(f"  - {detection.name} ({detection.category}, confidence: {detection.confidence})")

        for evidence in detection.evidence:
            print(f"\nEvidence: [{evidence.type}] {evidence.location} -> {evidence.matched_value}")
            print(f"Excerpt: {evidence.excerpt}")
            print(f"Explanation: {evidence.explanation}")
