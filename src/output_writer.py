import csv
import json
from pathlib import Path

from src.javascript_asset_fetcher import JavaScriptAsset
from src.technology_rules import TechnologyDetection
from src.website_fetcher import WebsiteFetchResult


# Deletes previous generated output files when the run is configured to rewrite results.
def delete_output_files(output_paths: list[Path]) -> None:
    for output_path in output_paths:
        if not output_path.exists():
            continue

        output_path.unlink()
        print(f"Deleted old output file: {output_path}")


# Converts fetch data, detections, and JavaScript asset metadata into the stable JSON output schema.
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

    # This is the public result shape used by all exports, so timeout-specific
    # fields and discovery-only data are not added to the output schema.
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


# Builds compact metadata for fetched JavaScript assets without storing full asset content in output.
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


# Loads existing JSON results when append mode needs to merge new detections with previous output.
def load_existing_json_results(output_path: Path) -> list[dict]:
    if not output_path.exists():
        return []

    if output_path.stat().st_size == 0:
        return []

    existing_results = json.loads(output_path.read_text(encoding="utf-8"))

    if not isinstance(existing_results, list):
        return []

    return existing_results


# Writes the detailed JSON result file, optionally appending to existing results.
def save_json_results(results: list[dict], output_path: Path, rewrite: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if rewrite == 0:
        existing_results = load_existing_json_results(output_path)
        results = existing_results + results

    output_path.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )


# Writes one JSON result per line for streaming-friendly downstream processing.
def save_jsonl_results(results: list[dict], output_path: Path, rewrite: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_mode = "w"

    if rewrite == 0:
        file_mode = "a"

    with output_path.open(file_mode, encoding="utf-8") as jsonl_file:
        for result in results:
            jsonl_file.write(json.dumps(result) + "\n")


# Builds flat CSV rows, one per technology detection or one empty row for domains with no detections.
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


# Builds aggregate metrics such as reachable domains, total findings, confidence counts, and top technologies.
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


# Saves aggregate metrics to the JSON summary output file.
def save_summary_json(summary: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )


# Saves the flat CSV summary and writes the header when creating a new summary file.
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
