from __future__ import annotations

import argparse
from dataclasses import dataclass

DEFAULT_OWNER = "ybenesya"
DEFAULT_REPO = "CTFd"
DEFAULT_DOT_OUT_PATH = "graph.dot"


@dataclass(frozen=True)
class CliArgs:
    token: str
    owner: str
    repo: str
    branch: str
    log_dest: str
    log_file_path: str | None
    debug: bool
    dot_out_path: str | None
    exclude_bot_users: bool | None


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ox-ctfd-task",
        description="Fetch repo stats from GitHub and generate commit graph (CTFd).",
    )

    p.add_argument(
        "--token",
        required=True,
        help="GitHub Personal Access Token.",
    )
    p.add_argument("--owner", default=DEFAULT_OWNER, help="GitHub repository owner/org.")
    p.add_argument("--repo", default=DEFAULT_REPO, help="GitHub repository name.")
    p.add_argument(
        "--branch",
        help="Branch name (merged to main) to build a commit graph for (later stage).",
    )

    p.add_argument(
        "--log-dest",
        choices=["stdout", "file"],
        default="stdout",
        help="Where to write logs: stdout or file.",
    )
    p.add_argument(
        "--log-file-path",
        default=None,
        help="Log file path (required if --log-dest=file).",
    )
    p.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging (DEBUG level). Default is INFO.",
    )

    
    p.add_argument(
        "--dot-out-path",
        default=DEFAULT_DOT_OUT_PATH,
        help="Output path for .dot graph file (later stage).",
    )

    p.add_argument(
        "--exclude-bot-users",
        action="store_true",
        help="Excludes bot users in contributors list. Default is False.",
    )

    return p


def parse_args(argv: list[str] | None = None) -> CliArgs:
    parser = build_parser()
    ns = parser.parse_args(argv)

    if ns.log_dest == "file" and not ns.log_file_path:
        parser.error("--log-file-path is required when --log-dest=file")
    
    
    if not ns.branch:
        parser.error("Missing required argument: --branch")


    return CliArgs(
        token=ns.token,
        owner=ns.owner,
        repo=ns.repo,
        log_dest=ns.log_dest,
        log_file_path=ns.log_file_path,
        debug=bool(ns.debug),
        dot_out_path=ns.dot_out_path,
        branch=ns.branch,
        exclude_bot_users=bool(ns.exclude_bot_users),
    )
