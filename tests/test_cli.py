from __future__ import annotations

import pytest

from ox_ctfd_task import cli


def test_parse_args_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(SystemExit):
        cli.parse_args(["--branch", "feature-x"])


def test_parse_args_token_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    args = cli.parse_args(["--token", "token123", "--branch", "feature-x"])
    assert args.token == "token123"
    assert args.branch == "feature-x"


def test_parse_args_requires_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(SystemExit):
        cli.parse_args(["--token", "token123"])


def test_parse_args_log_file_required(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(SystemExit):
        cli.parse_args(["--token", "token123", "--branch", "feature-x", "--log-dest", "file"])


def test_parse_args_exclude_bot_users_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    args = cli.parse_args(["--token", "token123", "--branch", "feature-x", "--exclude-bot-users"])
    assert args.exclude_bot_users is True
