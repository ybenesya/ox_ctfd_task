from __future__ import annotations

import logging
from datetime import datetime, timezone
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union
from urllib.parse import urlparse, parse_qs

import requests
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


GITHUB_API_BASE = "https://api.github.com"


class GitHubApiError(RuntimeError):
    pass


class RetryableGitHubError(RuntimeError):
    pass


@dataclass(frozen=True)
class RepoStats:
    owner: str
    repo: str
    forks: int
    stars: int
    contributors: int
    pull_requests: int


@dataclass(frozen=True)
class ReleaseInfo:
    tag_name: str
    name: str
    published_at: str


def _headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ox-ctfd-task",
    }


def _raise_for_status(resp: requests.Response, logger: logging.Logger) -> None:
    if 200 <= resp.status_code < 300:
        return
    try:
        detail = resp.json()
    except Exception:
        detail = resp.text
    logger.error("GitHub API error: %s %s -> %s", resp.request.method, resp.url, detail)
    raise GitHubApiError(f"GitHub API request failed ({resp.status_code})")


def _request_with_retry(
    *,
    url: str,
    headers: Dict[str, str],
    params: Optional[Dict[str, Any]],
    logger: logging.Logger,
) -> requests.Response:
    retryable_status = {429, 500, 502, 503, 504}

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((requests.RequestException, RetryableGitHubError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _do_request() -> requests.Response:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code in retryable_status:
            raise RetryableGitHubError(
                f"Retryable status {resp.status_code} for {resp.request.method} {resp.url}"
            )
        return resp

    return _do_request()


def _get(
    *,
    token: str,
    logger: logging.Logger,
    path: str,
    params: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any] | List[Dict[str, Any]], requests.Response]:
    url = f"{GITHUB_API_BASE}{path}"
    logger.debug("GET %s params=%s", url, params)
    try:
        resp = _request_with_retry(
            url=url,
            headers=_headers(token),
            params=params,
            logger=logger,
        )
    except (requests.RequestException, RetryableGitHubError) as exc:
        raise GitHubApiError(f"GitHub API request failed after retries: {exc}") from exc
    _raise_for_status(resp, logger)
    return resp.json(), resp


def _parse_last_page_from_link(link_header: str) -> Optional[int]:
    """
    Parses GitHub 'Link' header and returns the 'page' value of rel="last".
    Example:
      <...&page=2>; rel="next", <...&page=34>; rel="last"
    """
    if not link_header:
        return None
    parts = [p.strip() for p in link_header.split(",")]
    last_url = None
    for p in parts:
        if 'rel="last"' in p:
            m = re.search(r"<([^>]+)>", p)
            if m:
                last_url = m.group(1)
                break
    if not last_url:
        return None
    qs = parse_qs(urlparse(last_url).query)
    if "page" not in qs:
        return None
    try:
        return int(qs["page"][0])
    except Exception:
        return None


def _count_via_pagination(
    *,
    token: str,
    logger: logging.Logger,
    path: str,
    extra_params: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Efficient count:
    - request per_page=1
    - if Link: rel="last" exists => total = last_page
    - else total = len(items)
    """
    params = {"per_page": 1, "page": 1}
    if extra_params:
        params.update(extra_params)

    data, resp = _get(token=token, logger=logger, path=path, params=params)
    items = data if isinstance(data, list) else []
    link = resp.headers.get("Link", "")
    last_page = _parse_last_page_from_link(link)
    if last_page is not None:
        return last_page
    return len(items)

def _parse_github_dt(value: str) -> Optional[datetime]:
    """
    GitHub timestamps look like: '2026-01-10T12:34:56Z'
    Convert to timezone-aware datetime (UTC).
    """
    if not value:
        return None
    try:
        # 'Z' => UTC
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except Exception:
        return None



def get_latest_releases(
    *,
    token: str,
    owner: str,
    repo: str,
    logger: logging.Logger,
    n: int = 3,
) -> List[ReleaseInfo]:
    data, _ = _get(
        token=token,
        logger=logger,
        path=f"/repos/{owner}/{repo}/releases",
        params={"per_page": n, "page": 1},
    )
    if not isinstance(data, list):
        raise GitHubApiError("Unexpected releases response format")

    releases: List[ReleaseInfo] = []
    for r in data[:n]:
        releases.append(
            ReleaseInfo(
                tag_name=str(r.get("tag_name", "")),
                name=str(r.get("name", "")),
                published_at=str(r.get("published_at", "")),
            )
        )
    return releases


def get_repo_info(
    *,
    token: str,
    owner: str,
    repo: str,
    logger: logging.Logger,
) -> Tuple[int, int]:
    data, _ = _get(token=token, logger=logger, path=f"/repos/{owner}/{repo}")
    if not isinstance(data, dict):
        raise GitHubApiError("Unexpected repo response format")

    forks = int(data.get("forks_count", 0))
    stars = int(data.get("stargazers_count", 0))
    return forks, stars


def count_contributors(
    *,
    token: str,
    owner: str,
    repo: str,
    logger: logging.Logger,
) -> int:
    return _count_via_pagination(
        token=token,
        logger=logger,
        path=f"/repos/{owner}/{repo}/contributors",
        extra_params={"anon": "true"},
    )


def count_pull_requests(
    *,
    token: str,
    owner: str,
    repo: str,
    logger: logging.Logger,
    state: str = "all",
) -> int:
    return _count_via_pagination(
        token=token,
        logger=logger,
        path=f"/repos/{owner}/{repo}/pulls",
        extra_params={"state": state},
    )

def iter_pull_requests(
    *,
    token: str,
    owner: str,
    repo: str,
    logger: logging.Logger,
    state: str = "all",
    per_page: int = 100,
    max_pages: Optional[int] = None,
) -> Iterable[Dict[str, Any]]:
    """
    Generator to iterate PRs efficiently with an optional time window.
    """
    threshold: Optional[datetime] = None

    page = 1
    yielded_total = 0

    while True:
        if max_pages is not None and page > max_pages:
            logger.info("Stopping PR iteration due to max_pages=%d", max_pages)
            return

        params: Dict[str, Any] = {
            "state": state,
            "per_page": per_page,
            "page": page,
        }

        # Key optimization: newest -> oldest so we can stop early by time
        if threshold is not None:
            params["sort"] = "updated"
            params["direction"] = "desc"

        data, resp = _get(
            token=token,
            logger=logger,
            path=f"/repos/{owner}/{repo}/pulls",
            params=params,
        )

        if not isinstance(data, list) or not data:
            logger.info("No more PRs (page=%d). Total yielded=%d", page, yielded_total)
            return

        logger.info("Fetched PR page %d: %d items (yielded so far=%d)", page, len(data), yielded_total)

        for pr in data:
            if threshold is not None:
                updated_at_str = str(pr.get("updated_at", ""))
                updated_at = _parse_github_dt(updated_at_str)

                # If we can't parse updated_at, we choose to keep it (don't lose data)
                # but you can change this behavior if you want.
                if updated_at is not None and updated_at < threshold:
                    logger.info(
                        "Stopping by time window at page=%d: PR updated_at=%s < %s",
                        page,
                        updated_at.isoformat(),
                        threshold.isoformat(),
                    )
                    return

            yielded_total += 1
            yield pr

        link = resp.headers.get("Link", "")
        if 'rel="next"' not in link:
            logger.info("No next page link. Total yielded=%d", yielded_total)
            return

        page += 1


def fetch_repo_stats(
    *,
    token: str,
    owner: str,
    repo: str,
    logger: logging.Logger,
) -> RepoStats:
    forks, stars = get_repo_info(token=token, owner=owner, repo=repo, logger=logger)
    contributors = count_contributors(token=token, owner=owner, repo=repo, logger=logger)
    prs = count_pull_requests(token=token, owner=owner, repo=repo, logger=logger)

    return RepoStats(
        owner=owner,
        repo=repo,
        forks=forks,
        stars=stars,
        contributors=contributors,
        pull_requests=prs,
    )


def find_merged_pr_for_branch(
    *,
    token: str,
    owner: str,
    repo: str,
    branch: str,
    logger: logging.Logger,
) -> Optional[dict[str, Any]]:
    """
    Find a merged PR whose head branch is `branch`.
    We look for closed PRs with head=owner:branch and pick the most recently updated merged one.
    """
    data, _ = _get(
        token=token,
        logger=logger,
        path=f"/repos/{owner}/{repo}/pulls",
        params={
            "state": "closed",
            "head": f"{owner}:{branch}",
            "per_page": 100,
            "page": 1,
            "sort": "updated",
            "direction": "desc",
        },
    )
    if not isinstance(data, list):
        raise GitHubApiError("Unexpected pulls response format")

    for pr in data:
        if isinstance(pr, dict) and pr.get("merged_at"):
            return pr

    return None


def list_pr_commits(
    *,
    token: str,
    owner: str,
    repo: str,
    pr_number: int,
    logger: logging.Logger,
) -> List[dict[str, Any]]:
    """
    List commits that belong to a PR (in order).
    """
    commits: List[dict[str, Any]] = []
    page = 1
    per_page = 100
    while True:
        data, resp = _get(
            token=token,
            logger=logger,
            path=f"/repos/{owner}/{repo}/pulls/{pr_number}/commits",
            params={"per_page": per_page, "page": page},
        )
        if not isinstance(data, list) or not data:
            break
        commits.extend([c for c in data if isinstance(c, dict)])

        link = resp.headers.get("Link", "")
        if 'rel="next"' not in link:
            break
        page += 1

    return commits


def get_commit(
    *,
    token: str,
    owner: str,
    repo: str,
    sha: str,
    logger: logging.Logger,
) -> dict[str, Any]:
    data, _ = _get(
        token=token,
        logger=logger,
        path=f"/repos/{owner}/{repo}/commits/{sha}",
        params=None,
    )
    if not isinstance(data, dict):
        raise GitHubApiError("Unexpected commit response format")
    return data
