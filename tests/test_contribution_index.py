import copy
import json
from pathlib import Path

import pytest

from hal_public_interest.contribution_index import (
    ContributionIndexError,
    load_and_validate,
    validate_index,
)

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "portfolio" / "contributions.json"
README_PATH = ROOT / "CONTRIBUTIONS.md"
CANARY_PATH = (
    ROOT
    / "competitions"
    / "global-smart-campus-2026"
    / "evidence"
    / "public-demo-canary-receipt.json"
)


def _document() -> dict:
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def test_public_contribution_index_is_valid():
    document = load_and_validate(INDEX_PATH)

    assert len(document["contributions"]) == 4
    assert document["verified_cash_received_usd"] == 0


def test_contribution_ids_must_be_unique():
    document = _document()
    duplicate = copy.deepcopy(document["contributions"][0])
    document["contributions"].append(duplicate)

    with pytest.raises(ContributionIndexError, match="duplicate contribution id"):
        validate_index(document)


def test_received_money_requires_a_known_award():
    document = _document()
    document["contributions"][0]["amount_received"] = 1

    with pytest.raises(ContributionIndexError, match="unknown award"):
        validate_index(document)


def test_chain_love_merge_is_not_bounty_acceptance_or_payment():
    document = _document()
    chain_love = next(
        entry for entry in document["contributions"] if entry["id"] == "chain-love-3925"
    )

    assert chain_love["status"] == "merged_portfolio_only"
    assert chain_love["merged"] is True
    assert chain_love["accepted"] is None
    assert chain_love["amount_awarded"] is None
    assert chain_love["amount_received"] is None


def test_global_smart_campus_merge_is_not_competition_submission_or_payment():
    document = _document()
    campus = next(
        entry
        for entry in document["contributions"]
        if entry["id"] == "global-smart-campus-2026"
    )

    assert campus["status"] == "merged"
    assert campus["submitted"] is False
    assert campus["merged"] is True
    assert campus["accepted"] is None
    assert campus["amount_awarded"] is None
    assert campus["amount_received"] is None
    assert campus["reward"]["currency"] == "INR"
    assert campus["reward"]["advertised_amount"] == 50000
    assert campus["demo_url"] == (
        "https://hal-campus-evidence-desk.therealjakobhedrich.workers.dev"
    )


def test_demo_urls_must_use_https():
    document = _document()
    document["contributions"][0]["demo_url"] = "http://example.test/demo"

    with pytest.raises(ContributionIndexError, match="demo_url must be an HTTPS URL"):
        validate_index(document)


def test_global_smart_campus_public_canary_is_source_bound_and_safe():
    receipt = json.loads(CANARY_PATH.read_text(encoding="utf-8"))
    document = _document()
    campus = next(
        entry
        for entry in document["contributions"]
        if entry["id"] == "global-smart-campus-2026"
    )

    assert receipt["passed"] is True
    assert receipt["target"] == campus["demo_url"]
    assert receipt["source_pr_head_sha"] == ("69669e09facae1a923423beb31c2bb6970fbd410")
    assert len(receipt["checks"]) == 30
    assert all(check["passed"] is True for check in receipt["checks"])

    checks = {check["name"]: check["detail"] for check in receipt["checks"]}
    assert checks["public_demo_true"]["public_demo"] is True
    assert checks["live_external_false"]["live_model_external"] is False
    assert checks["live_mode_still_review_gated"]["review_gate"]["status"] == (
        "PENDING_HUMAN_REVIEW"
    )


def test_merged_flag_must_match_status():
    document = _document()
    document["contributions"][0]["merged"] = True

    with pytest.raises(ContributionIndexError, match="merged must match status"):
        validate_index(document)


def test_public_markdown_links_every_indexed_contribution():
    document = _document()
    markdown = README_PATH.read_text(encoding="utf-8")

    for contribution in document["contributions"]:
        assert contribution["id"] in markdown
        assert contribution["pull_request_url"] in markdown
        for evidence_url in contribution["evidence_urls"]:
            assert evidence_url in markdown
        if contribution["demo_url"] is not None:
            assert contribution["demo_url"] in markdown


def test_public_markdown_keeps_financial_boundary_explicit():
    markdown = README_PATH.read_text(encoding="utf-8")

    assert "Verified cash received: **USD 0**" in markdown
    assert "A merged PR is not payment evidence." in markdown
    assert "Unknown amounts remain unknown." in markdown
