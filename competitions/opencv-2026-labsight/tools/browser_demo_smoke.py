"""Real local-browser regression checks; controlled failure cases are labeled.

Optional test dependency: playwright. This never calls AWS or uploads to a
third-party service. Point --url only at a LabSight instance you control.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def exercise(url: str, output: Path, executable: str | None = None) -> dict[str, Any]:
    from playwright.sync_api import expect, sync_playwright

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("--url must identify an authorized HTTP(S) LabSight instance")
    output.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "playwright_version": version("playwright"),
        "evidence_scope": "local_browser_regression_not_aws_or_submission_evidence",
        "purpose": "image_quality_control_only",
        "diagnostic_claims": False,
        "server": url,
        "checks": [],
        "passed": False,
    }

    def checked(name: str, *, induced_failure: bool = False) -> None:
        report["checks"].append({"name": name, "passed": True, "controlled_failure_fixture": induced_failure})

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, executable_path=executable)
            report["browser_version"] = browser.version
            context = browser.new_context(viewport={"width": 1366, "height": 1050}, accept_downloads=True)
            page = context.new_page()
            page.set_default_timeout(15000)
            page_errors: list[str] = []
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.goto(url, wait_until="networkidle")
            health = context.request.get(url.rstrip("/") + "/health")
            assert health.ok, "live service health failed"
            report["observed_runtime"] = health.json()
            checked("live service and runtime observed without cloud authentication")

            page.get_by_role("button", name="Analyze clean", exact=True).click()
            expect(page.locator("#decision")).to_have_text("Accept capture")
            expect(page.locator("#download")).to_be_enabled()
            page.wait_for_function("document.getElementById('preview').naturalWidth > 0")
            assert page.locator("#trace li").count() == 1
            checked("clean action and real deterministic image preview")

            page.get_by_role("button", name="Analyze uneven", exact=True).click()
            expect(page.locator("#status")).to_contain_text("2 perception passes")
            expect(page.locator("#download")).to_be_enabled()
            assert page.locator("#trace li").count() == 2
            assert "Run CLAHE and re-analyze" in page.locator("#trace").inner_text()
            page.screenshot(path=str(output / "uneven-demo.png"), full_page=True)
            checked("two-pass CLAHE trace renders actual measured observations")

            with page.expect_download() as transfer:
                page.get_by_role("button", name="Download evidence JSON", exact=True).click()
            transfer.value.save_as(output / "downloaded-demo-evidence.json")
            receipt = json.loads((output / "downloaded-demo-evidence.json").read_text(encoding="utf-8"))
            assert receipt["evidence_scope"] == "interactive_demo_not_aws_or_submission_evidence"
            assert receipt["diagnostic_claims"] is False
            assert receipt["request_id"]
            assert receipt["response"]["trace"][0]["decision"] == "enhance_and_reanalyze"
            assert "image_base64" not in json.dumps(receipt)
            checked("real evidence download preserves scope and excludes image bytes")

            page.get_by_role("button", name="Run judge suite", exact=True).click()
            expect(page.locator("#status")).to_contain_text("Judge suite: PASS")
            expect(page.locator("#download")).to_be_enabled()
            assert page.locator("#suite article").count() == 4
            assert "Agentic Vision demonstrated" in page.locator("#status").inner_text()
            checked("four live judge scenarios and separate agentic proof")

            raw = context.request.get(url.rstrip("/") + "/demo/image/clean").body()
            page.locator("#file").set_input_files({"name": "synthetic-private-filename.png", "mimeType": "image/png", "buffer": raw})
            expect(page.locator("#download")).to_be_disabled()
            page.get_by_role("button", name="Analyze uploaded image", exact=True).click()
            expect(page.locator("#decision")).to_have_text("Accept capture")
            expect(page.locator("#download")).to_be_enabled()
            assert "synthetic-private-filename" not in page.locator("#result").inner_text()
            checked("actual PNG upload; filename excluded from receipt")

            page.locator("#file").set_input_files({"name": "not-an-image.txt", "mimeType": "text/plain", "buffer": b"local fixture"})
            page.get_by_role("button", name="Analyze uploaded image", exact=True).click()
            expect(page.locator("#status")).to_contain_text("non-empty PNG or JPEG")
            expect(page.locator("#download")).to_be_disabled()
            checked("invalid type rejected and stale evidence cleared", induced_failure=True)

            endpoint = "**/demo/analyze/blurred"
            failures = [
                ("HTTP rejection", {"status": 413, "content_type": "application/json", "body": '{"detail":"controlled upload rejection"}'}, "HTTP 413"),
                ("non-JSON response", {"status": 503, "content_type": "text/plain", "body": "controlled unavailable"}, "non-JSON"),
                ("incomplete response", {"status": 200, "content_type": "application/json", "body": '{"status":"accept","trace":[]}'}, "missing a supported QC action or trace"),
            ]
            for name, response, expected in failures:
                page.route(endpoint, lambda route: route.fulfill(**response))
                page.get_by_role("button", name="Analyze blurred", exact=True).click()
                expect(page.locator("#status")).to_contain_text(expected)
                expect(page.locator("#download")).to_be_disabled()
                expect(page.locator("#judge")).to_be_enabled()
                page.unroute(endpoint)
                checked(name + " fails visibly with controls restored", induced_failure=True)

            page.route(endpoint, lambda route: route.abort("failed"))
            page.get_by_role("button", name="Analyze blurred", exact=True).click()
            expect(page.locator("#status")).to_have_attribute("data-state", "error")
            expect(page.locator("#download")).to_be_disabled()
            page.unroute(endpoint)
            checked("network failure does not masquerade as successful analysis", induced_failure=True)

            page.get_by_role("button", name="Analyze blurred", exact=True).click()
            expect(page.locator("#decision")).to_have_text("Recapture: adjust focus")
            expect(page.locator("#download")).to_be_enabled()
            checked("real analysis recovers after controlled failures")

            page.locator("#judge").focus()
            page.keyboard.press("Enter")
            expect(page.locator("#status")).to_contain_text("Judge suite: PASS")
            expect(page.locator("#download")).to_be_enabled()
            checked("keyboard-triggered judge action")

            page.set_viewport_size({"width": 375, "height": 812})
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "horizontal mobile overflow"
            page.screenshot(path=str(output / "mobile-demo.png"), full_page=True)
            checked("375-pixel viewport without horizontal overflow")
            assert not page_errors, page_errors
            checked("no uncaught browser exceptions")
            context.close()
            browser.close()
        report["passed"] = True
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
    (output / "browser-regression.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8080")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executable", help="Path to an existing Chromium or Edge executable")
    args = parser.parse_args()
    report = exercise(args.url, args.output, args.executable)
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
