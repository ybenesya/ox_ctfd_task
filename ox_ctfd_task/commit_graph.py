from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, List, Set, Tuple

import pydot

from .github_api import (
    find_merged_pr_for_branch,
    list_pr_commits,
    get_commit,
    GitHubApiError,
)


@dataclass(frozen=True)
class CommitNode:
    sha: str
    label: str


def _short(sha: str) -> str:
    return sha[:7]


def _safe_label(text: str) -> str:
    """
    Ensure label is ASCII-only so Graphviz won't render � characters.
    """
    return text.encode("ascii", errors="ignore").decode("ascii")


def _title_from_commit_obj(obj: dict[str, Any], max_len: int = 22) -> str:
    """
    Extract a human-friendly commit title (1st line of commit message).
    Keep it short so ellipse nodes stay readable.
    """
    commit = obj.get("commit") if isinstance(obj.get("commit"), dict) else {}
    msg = str(commit.get("message", "")).splitlines()[0].strip()

    if not msg:
        sha = str(obj.get("sha", ""))
        return _short(sha) if sha else "commit"

    msg = _safe_label(msg)
    return (msg[: max_len - 1] + "...") if len(msg) > max_len else msg


def build_commit_graph_dot(
    *,
    token: str,
    owner: str,
    repo: str,
    branch: str,
    dot_out_path: str,
    logger: logging.Logger,
) -> None:
    """
    Build a commit graph for a merged branch:
      - find the merged PR for the branch
      - include PR commits
      - include merge commit + its parents (main + branch tip)
      - output .dot using pydot (Graphviz-compatible)
    """
    pr = find_merged_pr_for_branch(
        token=token, owner=owner, repo=repo, branch=branch, logger=logger
    )
    if not pr:
        raise GitHubApiError(
            f"Could not find a merged PR for branch '{branch}'. "
            f"Make sure the branch existed and was merged via PR."
        )

    pr_number = int(pr.get("number", 0))
    merge_sha = str(pr.get("merge_commit_sha", ""))
    if not merge_sha:
        raise GitHubApiError(f"PR #{pr_number} has no merge_commit_sha")

    logger.info("Building commit graph for branch '%s' via merged PR #%d", branch, pr_number)

    pr_commits = list_pr_commits(
        token=token, owner=owner, repo=repo, pr_number=pr_number, logger=logger
    )
    logger.info("PR #%d commits fetched: %d", pr_number, len(pr_commits))

    # Graph styling:
    # - ellipse like the PDF
    # - allow node to grow with label (no fixedsize), so text won't overflow
    graph = pydot.Dot(graph_type="digraph", rankdir="TB")
    graph.set_node_defaults(
        shape="ellipse",
        fontsize="10",
        margin="0.20,0.12",  # padding inside the ellipse
    )
    graph.set_edge_defaults(arrowsize="0.8")

    nodes_added: Set[str] = set()
    edges_added: Set[Tuple[str, str]] = set()

    def add_node(sha: str, label: str) -> None:
        if sha in nodes_added:
            return
        graph.add_node(pydot.Node(sha, label=label))
        nodes_added.add(sha)

    def add_edge(parent: str, child: str) -> None:
        key = (parent, child)
        if key in edges_added:
            return
        graph.add_edge(pydot.Edge(parent, child))
        edges_added.add(key)

    # PR commits as a chain
    pr_shas: List[str] = []
    for idx, c in enumerate(pr_commits, start=1):
        sha = str(c.get("sha", ""))
        if not sha:
            continue

        pr_shas.append(sha)

        title = _title_from_commit_obj(c, max_len=22)
        label = f"{title}\\n{branch}\\n{_short(sha)}"
        add_node(sha, label)

        if idx % 25 == 0:
            logger.info("Graph progress: processed %d/%d PR commits", idx, len(pr_commits))

    for i in range(len(pr_shas) - 1):
        add_edge(pr_shas[i], pr_shas[i + 1])

    # Merge commit node
    merge_commit = get_commit(token=token, owner=owner, repo=repo, sha=merge_sha, logger=logger)
    merge_label = f"MR commit\\nmain branch\\n{_short(merge_sha)}"
    add_node(merge_sha, merge_label)

    # Parents of the merge commit represent main + branch tip in the merge structure
    parents = merge_commit.get("parents") if isinstance(merge_commit.get("parents"), list) else []
    parent_shas = [
        str(p.get("sha", "")) for p in parents if isinstance(p, dict) and p.get("sha")
    ]

    for psha in parent_shas:
        parent_obj = get_commit(token=token, owner=owner, repo=repo, sha=psha, logger=logger)
        parent_title = _title_from_commit_obj(parent_obj, max_len=22)

        parent_label = f"{parent_title}\\nmain branch\\n{_short(psha)}"
        add_node(psha, parent_label)
        add_edge(psha, merge_sha)

    # Connect PR tip to merge commit
    if pr_shas:
        add_edge(pr_shas[-1], merge_sha)

    graph.write_raw(dot_out_path)
    logger.info(
        "Wrote commit graph to %s (nodes=%d, edges=%d)",
        dot_out_path,
        len(nodes_added),
        len(edges_added),
    )
