import argparse
import csv
import json
from pathlib import Path
from src.discovery_candidates import (
    collect_discovery_candidates,
    create_discovery_store,
    save_discovery_candidates,
)
from src.extract_domains import extract_domains
from src.javascript_asset_fetcher import JavaScriptAsset, fetch_javascript_assets
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
RESULTS_JSONL_OUTPUT_PATH = Path("data/output/technology_detections.jsonl")
SUMMARY_CSV_OUTPUT_PATH = Path("data/output/technology_summary.csv")
SUMMARY_JSON_OUTPUT_PATH = Path("data/output/technology_summary.json")
DISCOVERY_CANDIDATES_OUTPUT_PATH = Path("data/output/discovery_candidates.json")
OUTPUT_PATHS = [
    RESULTS_OUTPUT_PATH,
    RESULTS_JSONL_OUTPUT_PATH,
    SUMMARY_CSV_OUTPUT_PATH,
    SUMMARY_JSON_OUTPUT_PATH,
    DISCOVERY_CANDIDATES_OUTPUT_PATH,
]


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch websites and detect technologies."
    )
    parser.add_argument(
        "--rewrite",
        type=int,
        choices=[0, 1],
        default=1,
        help="Use 1 to delete old output files before writing new results. Use 0 to append new results to existing output files.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional number of domains to process. Useful for quick test runs.",
    )

    return parser.parse_args()


def delete_output_files(output_paths: list[Path]) -> None:
    for output_path in output_paths:
        if not output_path.exists():
            continue

        output_path.unlink()
        print(f"Deleted old output file: {output_path}")


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





def build_result_record(
    fetch_result: WebsiteFetchResult,
    detections: list[TechnologyDetection],
    javascript_assets: list[JavaScriptAsset] | None = None,
) -> dict:

    if javascript_assets is None:
        javascript_assets = []

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
            "cookies": fetch_result.cookies,
            "javascript_assets": build_javascript_asset_metadata(javascript_assets),
        },
    }


def build_javascript_asset_metadata(javascript_assets: list[JavaScriptAsset]) -> list[dict]:
    asset_metadata_items: list[dict] = []

    for javascript_asset in javascript_assets:
        asset_metadata_items.append(
            {
                "url": javascript_asset.url,
                "status_code": javascript_asset.status_code,
                "content_type": javascript_asset.content_type,
                "bytes_read": len(javascript_asset.content.encode("utf-8")),
                "error": javascript_asset.error,
            }
        )

    return asset_metadata_items



def load_existing_json_results(output_path: Path) -> list[dict]:
    if not output_path.exists():
        return []

    if output_path.stat().st_size == 0:
        return []

    existing_results = json.loads(output_path.read_text(encoding="utf-8"))

    if not isinstance(existing_results, list):
        return []

    return existing_results


def save_json_results(results: list[dict], output_path: Path, rewrite: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if rewrite == 0:
        existing_results = load_existing_json_results(output_path)
        results = existing_results + results

    output_path.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )


def save_jsonl_results(results: list[dict], output_path: Path, rewrite: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_mode = "w"

    if rewrite == 0:
        file_mode = "a"

    with output_path.open(file_mode, encoding="utf-8") as jsonl_file:
        for result in results:
            jsonl_file.write(json.dumps(result) + "\n")


def build_summary_rows(results: list[dict]) -> list[dict]:
    rows: list[dict] = []

    for result in results:
        technologies = result["technologies"]
        errors = result["errors"]

        if not technologies:
            rows.append(
                {
                    "domain": result["domain"],
                    "final_url": result["final_url"],
                    "status": result["status"],
                    "technologies_found": 0,
                    "technology_name": "",
                    "category": "",
                    "confidence": "",
                    "evidence_count": 0,
                    "evidence_types": "",
                    "first_evidence": "",
                    "errors": " | ".join(errors),
                }
            )
            continue

        for technology in technologies:
            evidence_items = technology["evidence"]
            evidence_types = sorted(
                set(evidence["type"] for evidence in evidence_items)
            )

            first_evidence = ""

            if evidence_items:
                first_evidence_item = evidence_items[0]
                first_evidence = (
                    f'{first_evidence_item["type"]}: '
                    f'{first_evidence_item["matched_value"]}'
                )

            rows.append(
                {
                    "domain": result["domain"],
                    "final_url": result["final_url"],
                    "status": result["status"],
                    "technologies_found": len(technologies),
                    "technology_name": technology["name"],
                    "category": technology["category"],
                    "confidence": technology["confidence"],
                    "evidence_count": len(evidence_items),
                    "evidence_types": ", ".join(evidence_types),
                    "first_evidence": first_evidence,
                    "errors": " | ".join(errors),
                }
            )

    return rows


def build_summary_json(results: list[dict]) -> dict:
    confidence_distribution: dict[str, int] = {}
    technology_domains: dict[str, set[str]] = {}
    total_findings = 0
    reachable_domains = 0

    for result in results:
        status = result["status"]

        if status is not None:
            reachable_domains = reachable_domains + 1

        for technology in result["technologies"]:
            technology_name = technology["name"]
            confidence = technology["confidence"]
            total_findings = total_findings + 1

            if confidence not in confidence_distribution:
                confidence_distribution[confidence] = 0

            confidence_distribution[confidence] = confidence_distribution[confidence] + 1

            if technology_name not in technology_domains:
                technology_domains[technology_name] = set()

            technology_domains[technology_name].add(result["domain"])

    top_technologies: list[dict] = []

    for technology_name, domains in technology_domains.items():
        top_technologies.append(
            {
                "name": technology_name,
                "domains": len(domains),
            }
        )

    top_technologies.sort(
        key=lambda technology: technology["domains"],
        reverse=True,
    )

    return {
        "total_domains": len(results),
        "reachable_domains": reachable_domains,
        "total_findings": total_findings,
        "unique_technologies": len(technology_domains),
        "confidence_distribution": confidence_distribution,
        "top_technologies": top_technologies[:30],
    }


def save_summary_json(summary: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )


def save_summary_csv(rows: list[dict], output_path: Path, rewrite: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "domain",
        "final_url",
        "status",
        "technologies_found",
        "technology_name",
        "category",
        "confidence",
        "evidence_count",
        "evidence_types",
        "first_evidence",
        "errors",
    ]

    file_has_content = output_path.exists() and output_path.stat().st_size > 0
    file_mode = "w"

    if rewrite == 0:
        file_mode = "a"

    with output_path.open(file_mode, encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

        if rewrite == 1 or not file_has_content:
            writer.writeheader()

        writer.writerows(rows)


def main() -> None:
    arguments = parse_arguments()

    if arguments.rewrite == 1:
        delete_output_files(OUTPUT_PATHS)
    else:
        print("Rewrite disabled. New results will be appended to existing output files.")

    domains = extract_domains(RAW_INPUT_PATH, DOMAINS_OUTPUT_PATH)
    rules = load_technology_rules(RULES_PATH)
    results: list[dict] = []
    discovery_store = create_discovery_store()
    domains_to_process = domains

    if arguments.limit is not None:
        domains_to_process = domains[:arguments.limit]

    for domain in domains_to_process:
        domain = domain.strip()

        if not domain:
            continue

        result = fetch_website(domain)
        javascript_assets = fetch_javascript_assets(
            html=result.html,
            base_url=result.final_url,
        )
        detections = detect_technologies(
            domain=result.domain,
            final_url=result.final_url,
            html=result.html,
            headers=result.headers,
            rules=rules,
            cookies=result.cookies,
            javascript_assets=javascript_assets,
        )

        print_fetch_result(result)
        print(f"JavaScript assets fetched: {len(javascript_assets)}")
        print_detected_technologies(detections)

        collect_discovery_candidates(
            discovery_store=discovery_store,
            fetch_result=result,
            detections=detections,
            javascript_assets=javascript_assets,
        )
        results.append(build_result_record(result, detections, javascript_assets))


    all_results_for_summary = results

    if arguments.rewrite == 0:
        existing_results = load_existing_json_results(RESULTS_OUTPUT_PATH)
        all_results_for_summary = existing_results + results

    save_json_results(results, RESULTS_OUTPUT_PATH, arguments.rewrite)
    save_jsonl_results(results, RESULTS_JSONL_OUTPUT_PATH, arguments.rewrite)

    summary_rows = build_summary_rows(results)
    save_summary_csv(summary_rows, SUMMARY_CSV_OUTPUT_PATH, arguments.rewrite)
    summary_json = build_summary_json(all_results_for_summary)
    save_summary_json(summary_json, SUMMARY_JSON_OUTPUT_PATH)
    save_discovery_candidates(discovery_store, DISCOVERY_CANDIDATES_OUTPUT_PATH, arguments.rewrite)

    print(f"Saved JSON results to {RESULTS_OUTPUT_PATH}")
    print(f"Saved JSONL results to {RESULTS_JSONL_OUTPUT_PATH}")
    print(f"Saved CSV summary to {SUMMARY_CSV_OUTPUT_PATH}")
    print(f"Saved JSON summary to {SUMMARY_JSON_OUTPUT_PATH}")
    print(f"Saved discovery candidates to {DISCOVERY_CANDIDATES_OUTPUT_PATH}")
    
    different_technologies: set[str] = set()
    total_technologies_found = 0

    for result_record in results:
        technologies = result_record["technologies"]
        total_technologies_found = total_technologies_found + len(technologies)

        for technology in technologies:
            technology_name = technology["name"]
            different_technologies.add(technology_name)

    print(f"Different technologies found: {len(different_technologies)}")
    print(f"Total technologies found: {total_technologies_found}")

if __name__ == "__main__":
    main()

