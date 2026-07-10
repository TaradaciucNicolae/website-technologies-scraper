import argparse
import sys
from pathlib import Path
from src.console_output import print_detected_technologies, print_fetch_result
from src.discovery_candidates import (
    collect_discovery_candidates,
    create_discovery_store,
    save_discovery_candidates,
)
from src.domain_processor import (
    build_failed_domain_result,
    process_domain,
    process_domain_with_timeout,
    process_domain_worker,
)
from src.extract_domains import extract_domains
from src.output_writer import (
    build_javascript_asset_metadata,
    build_result_record,
    build_summary_json,
    build_summary_rows,
    delete_output_files,
    load_existing_json_results,
    save_json_results,
    save_jsonl_results,
    save_summary_csv,
    save_summary_json,
)
from src.technology_rules import load_technology_rules


# Configures stdout and stderr to use UTF-8 so printed evidence is readable.
def configure_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


configure_utf8_output()

RULES_PATH = Path("rules/technology_rules")
RAW_INPUT_PATH = Path("data/raw/domains.snappy.parquet")
DOMAINS_OUTPUT_PATH = Path("data/input/domains.txt")
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


# Parses command-line options that control output rewriting, sample size, and per-domain timeout.
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
    parser.add_argument(
        "--domain-timeout",
        type=float,
        default=15,
        help="Maximum time in seconds allowed for processing one domain.",
    )

    return parser.parse_args()


# Orchestrates the scraper run from domain extraction through detection, summaries, and discovery output.
def main() -> None:
    arguments = parse_arguments()

    if arguments.rewrite == 1:
        delete_output_files(OUTPUT_PATHS)
    else:
        print("Rewrite disabled. New results will be appended to existing output files.")

    domains = extract_domains(RAW_INPUT_PATH, DOMAINS_OUTPUT_PATH)
    # Rules are loaded once and reused for every domain so detection is
    # deterministic across JSON, JSONL, CSV, summary, and discovery outputs.
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

        domain_result = process_domain_with_timeout(
            domain=domain,
            rules=rules,
            domain_timeout_seconds=arguments.domain_timeout,
        )

        result, javascript_assets, detections = domain_result

        print_fetch_result(result)
        print(f"JavaScript assets fetched: {len(javascript_assets)}")
        print_detected_technologies(detections)

        # Discovery candidates help future rule writing without changing the
        # current detection result.
        collect_discovery_candidates(
            discovery_store=discovery_store,
            fetch_result=result,
            detections=detections,
            javascript_assets=javascript_assets,
        )
        results.append(build_result_record(result, detections, javascript_assets))


    all_results_for_summary = results

    if arguments.rewrite == 0:
        # Appended runs still produce a summary over the combined JSON result set.
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

