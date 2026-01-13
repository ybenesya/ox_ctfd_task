from __future__ import annotations

import json
import logging

import pytest
import requests
import tenacity.nap as tenacity_nap

from ox_ctfd_task import github_api


def _make_response(status: int, json_body: object, headers: dict[str, str] | None = None) -> requests.Response:
    resp = requests.Response()
    resp.status_code = status
    resp._content = json.dumps(json_body).encode("utf-8")
    resp.headers = headers or {}
    resp.url = "https://api.github.com/test"
    resp.request = requests.Request("GET", resp.url).prepare()
    return resp


def test_get_retries_on_transient_status(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    responses = [
        _make_response(500, {"error": "boom"}),
        _make_response(200, {"ok": True}),
    ]

    def fake_get(*args: object, **kwargs: object) -> requests.Response:
        calls.append(1)
        return responses.pop(0)

    monkeypatch.setattr(tenacity_nap, "sleep", lambda _: None)
    monkeypatch.setattr(requests, "get", fake_get)

    logger = logging.getLogger("test")
    data, _ = github_api._get(token="t", logger=logger, path="/test", params=None)
    assert data == {"ok": True}
    assert len(calls) == 2


def test_get_raises_after_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(*args: object, **kwargs: object) -> requests.Response:
        return _make_response(503, {"error": "down"})

    monkeypatch.setattr(tenacity_nap, "sleep", lambda _: None)
    monkeypatch.setattr(requests, "get", fake_get)

    logger = logging.getLogger("test")
    with pytest.raises(github_api.GitHubApiError):
        github_api._get(token="t", logger=logger, path="/test", params=None)


def test_iter_pull_requests_paginates(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyResp:
        def __init__(self, link: str) -> None:
            self.headers = {"Link": link}

    def fake_get(*, token: str, logger: logging.Logger, path: str, params: dict[str, int] | None = None):
        page = params["page"] if params else 1
        if page == 1:
            return [{"id": 1}, {"id": 2}], DummyResp('<x>; rel="next"')
        return [], DummyResp("")

    monkeypatch.setattr(github_api, "_get", fake_get)

    logger = logging.getLogger("test")
    prs = list(github_api.iter_pull_requests(token="t", owner="o", repo="r", logger=logger))
    assert [pr["id"] for pr in prs] == [1, 2]


def test_count_via_pagination_uses_last_page(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyResp:
        def __init__(self, link: str) -> None:
            self.headers = {"Link": link}

    def fake_get(*, token: str, logger: logging.Logger, path: str, params: dict[str, int] | None = None):
        link = '<https://api.github.com/x?page=5>; rel="last"'
        return [{"id": 1}], DummyResp(link)

    monkeypatch.setattr(github_api, "_get", fake_get)
    logger = logging.getLogger("test")
    assert github_api._count_via_pagination(token="t", logger=logger, path="/x") == 5


def test_count_via_pagination_no_link(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyResp:
        def __init__(self) -> None:
            self.headers = {"Link": ""}

    def fake_get(*, token: str, logger: logging.Logger, path: str, params: dict[str, int] | None = None):
        return [{"id": 1}, {"id": 2}], DummyResp()

    monkeypatch.setattr(github_api, "_get", fake_get)
    logger = logging.getLogger("test")
    assert github_api._count_via_pagination(token="t", logger=logger, path="/x") == 2
