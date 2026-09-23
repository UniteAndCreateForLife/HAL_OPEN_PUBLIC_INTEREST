"""Validate the public contribution index without network access."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ALLOWED_STATUSES = {
    "open_draft",
    "open_awaiting_sponsor",
    "open_approved_portfolio_only",
    "merged",
    "closed",
}
ALLOWED_REWARD_MODELS = {
    "competitive_prize",
    "competitive_bounty",
    "fixed_per_contribution",
    "not_verified_eligible",
}
MONEY_FIELDS = (
    "advertised_amount",
    "prize_pool_maximum",
    "category_award",
)


class ContributionIndexError(ValueError):
    """Raised when the public index violates its evidence contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContributionIndexError(message)


def _is_money(value: Any) -> bool:
    return value is None or (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value >= 0
    )


def _github_url(value: Any, field: str, *, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    _require(isinstance(value, str) and value, f"{field} must be a URL")
    parsed = urlparse(value)
    _require(
        parsed.scheme == "https" and parsed.netloc == "github.com",
        f"{field} must be an https://github.com URL",
    )
def validate_index(document: dict[str, Any]) -> dict[str, Any]:
    """Validate and return a contribution-index document."""

    _require(document.get("schema_version") == 1, "schema_version must be 1")
    as_of = document.get("as_of_utc")
    _require(isinstance(as_of, str) and as_of.endswith("Z"), "as_of_utc must end in Z")
    try:
        datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContributionIndexError("as_of_utc must be ISO-8601") from exc

    verified = document.get("verified_cash_received_usd")
    _require(_is_money(verified) and verified is not None, "verified cash total is invalid")

    entries = document.get("contributions")
    _require(isinstance(entries, list) and entries, "contributions must be non-empty")
    seen: set[str] = set()

    for position, entry in enumerate(entries):
        prefix = f"contributions[{position}]"
        _require(isinstance(entry, dict), f"{prefix} must be an object")
        entry_id = entry.get("id")
        _require(isinstance(entry_id, str) and entry_id, f"{prefix}.id is required")
        _require(entry_id not in seen, f"duplicate contribution id: {entry_id}")
        seen.add(entry_id)

        for field in ("title", "repository", "remaining_action"):
            _require(
                isinstance(entry.get(field), str) and entry[field].strip(),
                f"{prefix}.{field} is required",
            )
        _require(entry.get("status") in ALLOWED_STATUSES, f"{prefix}.status is invalid")
        _require(isinstance(entry.get("submitted"), bool), f"{prefix}.submitted must be boolean")
        _require(entry.get("accepted") in (True, False, None), f"{prefix}.accepted is invalid")
        _github_url(entry.get("pull_request_url"), f"{prefix}.pull_request_url")
        _github_url(entry.get("issue_url"), f"{prefix}.issue_url", nullable=True)

        awarded = entry.get("amount_awarded")
        received = entry.get("amount_received")
        _require(_is_money(awarded), f"{prefix}.amount_awarded is invalid")
        _require(_is_money(received), f"{prefix}.amount_received is invalid")
        _require(received is None or awarded is not None, f"{prefix} cannot receive an unknown award")
        if received is not None and awarded is not None:
            _require(received <= awarded, f"{prefix} received more than awarded")
        reward = entry.get("reward")
        _require(isinstance(reward, dict), f"{prefix}.reward is required")
        _require(
            reward.get("model") in ALLOWED_REWARD_MODELS,
            f"{prefix}.reward.model is invalid",
        )
        currency = reward.get("currency")
        _require(
            currency is None or (isinstance(currency, str) and len(currency) == 3),
            f"{prefix}.reward.currency is invalid",
        )
        for field in MONEY_FIELDS:
            _require(_is_money(reward.get(field)), f"{prefix}.reward.{field} is invalid")

        evidence = entry.get("evidence_urls")
        _require(isinstance(evidence, list) and evidence, f"{prefix}.evidence_urls is required")
        for index, url in enumerate(evidence):
            _github_url(url, f"{prefix}.evidence_urls[{index}]")

    return document


def load_and_validate(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        document = json.load(handle)
    _require(isinstance(document, dict), "index root must be an object")
    return validate_index(document)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path("portfolio/contributions.json"),
    )
    args = parser.parse_args()
    document = load_and_validate(args.path)
    print(
        f"validated {len(document['contributions'])} public contributions; "
        f"verified cash received: USD {document['verified_cash_received_usd']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
