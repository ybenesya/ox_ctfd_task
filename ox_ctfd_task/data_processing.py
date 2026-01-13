from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, List


@dataclass(frozen=True)
class ContributorPrCount:
    """A single contributor and their PR count."""
    login: str
    pr_count: int


def is_bot_user(user: dict[str, Any]) -> bool:
    """
    Return True if the GitHub user represents a bot.
    We detect bots by:
      - user['type'] == 'Bot'
      - login ends with '[bot]'
    """
    if not isinstance(user, dict):
        return False

    login = user.get("login", "")
    user_type = user.get("type", "")

    return user_type == "Bot" or str(login).endswith("[bot]")


def build_contributors_pr_ranking(
    prs: Iterable[dict[str, Any]],
    *,
    logger: logging.Logger,
    exclude_bot_users: bool
) -> List[ContributorPrCount]:
    """
    Compute a descending list of contributors by number of PRs.
    """
    counter: Counter[str] = Counter()
    total_prs = 0
    skipped_bots = 0

    for pr in prs:
        total_prs += 1

        if not isinstance(pr, dict):
            continue

        user = pr.get("user")
        if not isinstance(user, dict):
            continue

        if exclude_bot_users and is_bot_user(user):
            skipped_bots += 1
            continue

        login = user.get("login")
        if not login:
            continue

        counter[str(login)] += 1

    logger.debug(
        "Processed %d PRs | %d contributors | %d bot PRs skipped",
        total_prs,
        len(counter),
        skipped_bots,
    )

    ranking = [
        ContributorPrCount(login=login, pr_count=count)
        for login, count in counter.items()
    ]
    ranking.sort(key=lambda x: (-x.pr_count, x.login.lower()))
    return ranking
