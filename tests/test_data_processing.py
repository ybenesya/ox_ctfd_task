from __future__ import annotations

import logging

from ox_ctfd_task.data_processing import build_contributors_pr_ranking, is_bot_user


def test_is_bot_user_detects_type_and_suffix() -> None:
    assert is_bot_user({"type": "Bot", "login": "bot-user"}) is True
    assert is_bot_user({"type": "User", "login": "dependabot[bot]"}) is True
    assert is_bot_user({"type": "User", "login": "alice"}) is False


def test_build_contributors_pr_ranking_counts_and_sorts() -> None:
    prs = [
        {"user": {"login": "alice", "type": "User"}},
        {"user": {"login": "bob", "type": "User"}},
        {"user": {"login": "alice", "type": "User"}},
    ]
    logger = logging.getLogger("test")
    ranking = build_contributors_pr_ranking(prs, logger=logger, exclude_bot_users=False)
    assert [r.login for r in ranking] == ["alice", "bob"]
    assert [r.pr_count for r in ranking] == [2, 1]


def test_build_contributors_pr_ranking_excludes_bots() -> None:
    prs = [
        {"user": {"login": "alice", "type": "User"}},
        {"user": {"login": "dependabot[bot]", "type": "Bot"}},
    ]
    logger = logging.getLogger("test")
    ranking = build_contributors_pr_ranking(prs, logger=logger, exclude_bot_users=True)
    assert [r.login for r in ranking] == ["alice"]
