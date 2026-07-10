from multiprocessing import Process, Queue
from queue import Empty

from src.javascript_asset_fetcher import JavaScriptAsset, fetch_javascript_assets
from src.technology_detector import detect_technologies
from src.technology_rules import TechnologyDetection
from src.website_fetcher import WebsiteFetchResult, fetch_website


# Runs the complete static analysis pipeline for one domain.
def process_domain(
    domain: str,
    rules,
) -> tuple[WebsiteFetchResult, list[JavaScriptAsset], list[TechnologyDetection]]:
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

    return result, javascript_assets, detections


# Executes per-domain processing inside a child process and sends either the result or error back.
def process_domain_worker(
    domain: str,
    rules,
    result_queue: Queue,
) -> None:
    try:
        domain_result = process_domain(domain, rules)
        result_queue.put(("ok", domain_result))
    except Exception as error:
        result_queue.put(("error", str(error)))


# Builds a schema-compatible empty result tuple so failed domains still appear in the output.
def build_failed_domain_result(
    domain: str,
    error_message: str,
    elapsed_ms: int | None = None,
) -> tuple[WebsiteFetchResult, list[JavaScriptAsset], list[TechnologyDetection]]:
    fetch_result = WebsiteFetchResult(
        domain=domain,
        attempted_urls=[f"https://{domain}", f"http://{domain}"],
        successful_url=None,
        final_url=None,
        status_code=None,
        headers={},
        cookies={},
        html="",
        error=error_message,
        elapsed_ms=elapsed_ms,
        content_type=None,
        redirect_count=0,
    )

    return fetch_result, [], []


# Runs one domain with a hard timeout and returns an empty result for timeout or worker failure.
def process_domain_with_timeout(
    domain: str,
    rules,
    domain_timeout_seconds: float,
) -> tuple[WebsiteFetchResult, list[JavaScriptAsset], list[TechnologyDetection]]:
    # The domain is processed in a separate process so it can be stopped if it
    # exceeds the configured timeout, allowing the scan to continue.
    result_queue: Queue = Queue()
    process = Process(
        target=process_domain_worker,
        args=(domain, rules, result_queue),
    )
    process.start()

    try:
        status, domain_result = result_queue.get(timeout=domain_timeout_seconds)
    except Empty:
        print(
            f"Skipping {domain} because it exceeded {domain_timeout_seconds:g} seconds."
        )
        process.terminate()
        process.join()
        result_queue.close()
        return build_failed_domain_result(
            domain=domain,
            error_message=f"Processing exceeded {domain_timeout_seconds:g} seconds.",
            elapsed_ms=int(domain_timeout_seconds * 1000),
        )

    process.join()
    result_queue.close()

    if status == "error":
        print(f"Skipping {domain} because processing failed: {domain_result}")
        return build_failed_domain_result(
            domain=domain,
            error_message=f"Processing failed: {domain_result}",
        )

    return domain_result
