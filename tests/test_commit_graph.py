from __future__ import annotations

import logging
from pathlib import Path

import pytest

from ox_ctfd_task import commit_graph


def test_build_commit_graph_dot_writes_file(tmp_path: Path, monkeypatch) -> None:
    def fake_find_pr(*, token: str, owner: str, repo: str, branch: str, logger: logging.Logger):
        return {"number": 101, "merge_commit_sha": "m123"}

    def fake_list_pr_commits(*, token: str, owner: str, repo: str, pr_number: int, logger: logging.Logger):
        return [
            {"sha": "c1", "commit": {"message": "Add feature"}},
            {"sha": "c2", "commit": {"message": "Fix bug"}},
        ]

    def fake_get_commit(*, token: str, owner: str, repo: str, sha: str, logger: logging.Logger):
        if sha == "m123":
            return {
                "sha": "m123",
                "commit": {"message": "Merge branch"},
                "parents": [{"sha": "p1"}, {"sha": "p2"}],
            }
        return {"sha": sha, "commit": {"message": f"Parent {sha}"}, "parents": []}

    monkeypatch.setattr(commit_graph, "find_merged_pr_for_branch", fake_find_pr)
    monkeypatch.setattr(commit_graph, "list_pr_commits", fake_list_pr_commits)
    monkeypatch.setattr(commit_graph, "get_commit", fake_get_commit)

    dot_path = tmp_path / "graph.dot"
    logger = logging.getLogger("test")
    commit_graph.build_commit_graph_dot(
        token="t",
        owner="o",
        repo="r",
        branch="feature-x",
        dot_out_path=str(dot_path),
        logger=logger,
    )

    content = dot_path.read_text(encoding="utf-8")
    assert "m123" in content
    assert "c1" in content
    assert "p1" in content


def test_build_commit_graph_dot_raises_when_missing_pr(monkeypatch) -> None:
    def fake_find_pr(*, token: str, owner: str, repo: str, branch: str, logger: logging.Logger):
        return None

    monkeypatch.setattr(commit_graph, "find_merged_pr_for_branch", fake_find_pr)

    with pytest.raises(commit_graph.GitHubApiError):
        commit_graph.build_commit_graph_dot(
            token="t",
            owner="o",
            repo="r",
            branch="feature-x",
            dot_out_path="graph.dot",
            logger=logging.getLogger("test"),
        )
