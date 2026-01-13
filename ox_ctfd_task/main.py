from __future__ import annotations
import os
from datetime import datetime, timedelta, timezone

from .cli import parse_args
from .logging_conf import configure_logging
from .github_api import fetch_repo_stats, get_latest_releases, iter_pull_requests
from .data_processing import build_contributors_pr_ranking
from .commit_graph import build_commit_graph_dot



def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logger = configure_logging(
        log_dest=args.log_dest,
        log_file_path=args.log_file_path,
        debug=args.debug,
    )

    logger.info("Fetching GitHub data for %s/%s ...", args.owner, args.repo)

    # Releases (latest 3)
    releases = get_latest_releases(
        token=args.token,
        owner=args.owner,
        repo=args.repo,
        logger=logger,
        n=3,
    )

    # Repo stats + counts
    stats = fetch_repo_stats(
        token=args.token,
        owner=args.owner,
        repo=args.repo,
        logger=logger,
    )

    print("\nLatest 3 releases:")
    for r in releases:
        print(f"- {r.tag_name} | {r.name} | {r.published_at}")

    print("\nRepo stats:")
    print(f"- forks: {stats.forks}")
    print(f"- stars: {stats.stars}")
    print(f"- contributors: {stats.contributors}")
    print(f"- pull requests (all): {stats.pull_requests}")

    prs_iter = iter_pull_requests(
        token=args.token,
        owner=args.owner,
        repo=args.repo,
        logger=logger,
        state="all"
        
    )

    prs_ranking = build_contributors_pr_ranking(prs_iter, logger=logger, exclude_bot_users = args.exclude_bot_users)
    print("\nContributors by number of PRs (desc):")
    for i, row in enumerate(prs_ranking, start=1):
        print(f"{i:>3}. {row.login}: {row.pr_count}")

    
    if args.branch and args.dot_out_path:
        build_commit_graph_dot(
            token=args.token,
            owner=args.owner,
            repo=args.repo,
            branch=args.branch,
            dot_out_path=args.dot_out_path,
            logger=logger,
        )
    

    logger.info("Done.")
    return 0
