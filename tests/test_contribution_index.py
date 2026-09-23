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


def _document() -> dict:
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def test_public_contribution_index_is_valid():
    document = load_and_validate(INDEX_PATH)

    assert len(document["contributions"]) == 3
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


def test_public_markdown_links_every_indexed_contribution():
    document = _document()
    markdown = README_PATH.read_text(encoding="utf-8")

    for contribution in document["contributions"]:
        assert contribution["id"] in markdown
        assert contribution["pull_request_url"] in markdown
        for evidence_url in contribution["evidence_urls"]:
            assert evidence_url in markdown


def test_public_markdown_keeps_financial_boundary_explicit():
    markdown = README_PATH.read_text(encoding="utf-8")

    assert "Verified cash received: **USD 0**" in markdown
    assert "A merged PR is not payment evidence." in markdown
    assert "Unknown amounts remain unknown." in markdown
