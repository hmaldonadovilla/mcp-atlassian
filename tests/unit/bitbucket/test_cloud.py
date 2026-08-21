"""Contract tests for the native Bitbucket Cloud REST API client."""

import json
from unittest.mock import MagicMock

import pytest
from requests import Request, Response, Session
from requests.exceptions import HTTPError

from mcp_atlassian.bitbucket.cloud import BitbucketCloudClient
from mcp_atlassian.models.bitbucket.common import (
    BitbucketBranch,
    BitbucketCommit,
    BitbucketPullRequest,
    BitbucketRepository,
    BitbucketUser,
    BitbucketWorkspace,
    CommitChanges,
)

API = "https://api.bitbucket.org/2.0"


def make_response(
    payload=None,
    *,
    status: int = 200,
    url: str = API,
    content: bytes | None = None,
):
    """Create a real requests response suitable for client contract tests."""
    response = Response()
    response.status_code = status
    response.url = url
    response.request = Request("GET", url).prepare()
    response.headers["Content-Type"] = "application/json"
    if content is not None:
        response._content = content
    elif payload is None:
        response._content = b""
    else:
        response._content = json.dumps(payload).encode()
    return response


@pytest.fixture
def session():
    return MagicMock(spec=Session)


@pytest.fixture
def client(session):
    return BitbucketCloudClient(session, "https://bitbucket.org")


def test_workspace_pagination_follows_next_link(client, session):
    next_url = f"{API}/workspaces?page=2"
    session.request.side_effect = [
        make_response({"values": [{"slug": "one"}], "next": next_url}),
        make_response({"values": [{"slug": "two"}]}),
    ]

    result = client.project_list()

    assert [item["slug"] for item in result] == ["one", "two"]
    assert session.request.call_args_list[0].args == ("GET", f"{API}/workspaces")
    assert session.request.call_args_list[0].kwargs["params"] == {"pagelen": 50}
    assert session.request.call_args_list[1].args == ("GET", next_url)


def test_repository_routes_and_global_role_filter(client, session):
    session.request.side_effect = [
        make_response({"values": [{"slug": "global"}]}),
        make_response({"values": [{"slug": "scoped"}]}),
        make_response({"slug": "repo"}),
    ]

    assert client.get_repositories() == [{"slug": "global"}]
    assert client.get_repositories("my workspace") == [{"slug": "scoped"}]
    assert client.get_repo("my workspace", "a/repo") == {"slug": "repo"}

    assert session.request.call_args_list[0].args == ("GET", f"{API}/repositories")
    assert session.request.call_args_list[0].kwargs["params"] == {
        "role": "member",
        "pagelen": 50,
    }
    assert (
        session.request.call_args_list[1]
        .args[1]
        .endswith("/repositories/my%20workspace")
    )
    assert (
        session.request.call_args_list[2]
        .args[1]
        .endswith("/repositories/my%20workspace/a%2Frepo")
    )


def test_file_and_directory_routes(client, session):
    session.request.side_effect = [
        make_response(content=b"hello"),
        make_response({"values": [{"path": "src/main.py"}]}),
    ]

    content = client.get_content_of_file(
        "workspace", "repo", "src/main.py", "feature/test"
    )
    entries = client.get_file_list("workspace", "repo", "src", "main")

    assert content == b"hello"
    assert entries == [{"path": "src/main.py"}]
    assert (
        session.request.call_args_list[0]
        .args[1]
        .endswith("/repositories/workspace/repo/src/feature%2Ftest/src/main.py")
    )
    assert (
        session.request.call_args_list[1]
        .args[1]
        .endswith("/repositories/workspace/repo/src/main/src")
    )


def test_branch_routes_filter_and_default_branch(client, session):
    session.request.side_effect = [
        make_response(
            {
                "values": [
                    {"name": "main"},
                    {"name": "feature/cloud"},
                    {"name": "feature/other"},
                ]
            }
        ),
        make_response({"mainbranch": {"name": "main", "target": {"hash": "abc"}}}),
    ]

    branches = client.get_branches(
        "workspace", "repo", filter="feature", start=1, limit=1
    )
    default = client.get_default_branch("workspace", "repo")

    assert branches == [{"name": "feature/other"}]
    assert default["name"] == "main"
    assert default["isDefault"] is True
    assert (
        session.request.call_args_list[0]
        .args[1]
        .endswith("/repositories/workspace/repo/refs/branches")
    )


def test_commit_and_diffstat_routes(client, session):
    session.request.side_effect = [
        make_response({"values": [{"hash": "abc"}, {"hash": "def"}]}),
        make_response({"values": [{"status": "modified"}]}),
    ]

    commits = client.get_commits(
        "workspace", "repo", limit=1, until="main", since="base"
    )
    changes = client.get_commit_changes(
        project_key="workspace",
        repository_slug="repo",
        commit_id="abc",
        hash_newest="def",
    )

    assert commits == [{"hash": "abc"}]
    assert changes["values"] == [{"status": "modified"}]
    assert session.request.call_args_list[0].kwargs["params"] == {
        "include": "main",
        "exclude": "base",
        "pagelen": 50,
    }
    assert (
        session.request.call_args_list[1]
        .args[1]
        .endswith("/repositories/workspace/repo/diffstat/abc..def")
    )


def test_create_branch_resolves_source_hash(client, session):
    session.request.side_effect = [
        make_response({"target": {"hash": "abc123"}}),
        make_response({"name": "feature/cloud"}),
    ]

    result = client.create_branch("workspace", "repo", "feature/cloud", "main")

    assert result == {"name": "feature/cloud"}
    assert session.request.call_args_list[0].args[0] == "GET"
    assert session.request.call_args_list[1].args == (
        "POST",
        f"{API}/repositories/workspace/repo/refs/branches",
    )
    assert session.request.call_args_list[1].kwargs["json"] == {
        "name": "feature/cloud",
        "target": {"hash": "abc123"},
    }


def test_pull_request_read_routes(client, session):
    session.request.side_effect = [
        make_response({"values": [{"id": 1}]}),
        make_response({"id": 1}),
        make_response({"values": [{"hash": "abc"}]}),
        make_response({"values": [{"approval": {}}]}),
    ]

    assert client.get_pull_requests("workspace", "repo") == [{"id": 1}]
    assert client.get_pull_request("workspace", "repo", 1) == {"id": 1}
    assert client.get_pull_requests_commits("workspace", "repo", 1) == [{"hash": "abc"}]
    assert client.get_pull_request_activities("workspace", "repo", 1) == [
        {"approval": {}}
    ]
    assert session.request.call_args_list[0].kwargs["params"] == {
        "state": "OPEN",
        "pagelen": 50,
    }
    assert (
        session.request.call_args_list[3].args[1].endswith("/pullrequests/1/activity")
    )


def test_create_pull_request_translates_server_payload(client, session):
    session.request.return_value = make_response({"id": 9})
    payload = {
        "title": "Cloud support",
        "description": "Native routes",
        "fromRef": {"id": "refs/heads/feature/cloud"},
        "toRef": {"id": "refs/heads/main"},
        "state": "OPEN",
    }

    assert client.create_pull_request("workspace", "repo", payload) == {"id": 9}
    assert session.request.call_args.kwargs["json"] == {
        "title": "Cloud support",
        "description": "Native routes",
        "source": {"branch": {"name": "feature/cloud"}},
        "destination": {"branch": {"name": "main"}},
    }


def test_comment_uses_cloud_content_schema(client, session):
    session.request.side_effect = [
        make_response({"id": 5}),
        make_response({"id": 6, "state": "UNRESOLVED"}),
    ]

    result = client.add_pull_request_comment("workspace", "repo", 1, "Looks good")

    assert result == {"id": 5}
    assert session.request.call_args.kwargs["json"] == {
        "content": {"raw": "Looks good"}
    }
    task = client.add_pull_request_blocker_comment(
        "workspace", "repo", 1, "Block this", "BLOCKER"
    )
    assert task == {"id": 6, "state": "UNRESOLVED"}
    assert session.request.call_args.args[1].endswith("/pullrequests/1/tasks")
    assert session.request.call_args.kwargs["json"] == {
        "content": {"raw": "Block this"}
    }


def test_cloud_error_includes_nested_message(client, session):
    session.request.return_value = make_response(
        {"type": "error", "error": {"message": "Repository not found"}},
        status=404,
        url=f"{API}/repositories/workspace/missing",
    )

    with pytest.raises(HTTPError, match="HTTP 404: Repository not found"):
        client.get_repo("workspace", "missing")


def test_cloud_models_normalize_response_shapes():
    workspace = BitbucketWorkspace.from_api_response(
        {"name": "Team", "slug": "team", "uuid": "{ws}", "is_private": True}
    )
    repository = BitbucketRepository.from_api_response(
        {
            "name": "Repo",
            "slug": "repo",
            "uuid": "{repo}",
            "full_name": "team/repo",
            "is_private": False,
            "mainbranch": {"name": "main"},
        }
    )
    branch = BitbucketBranch.from_api_response(
        {"name": "main", "target": {"hash": "abc"}}
    )
    commit = BitbucketCommit.from_api_response(
        {
            "hash": "abc",
            "message": "Initial",
            "date": "2026-08-20T10:00:00+00:00",
            "author": {"raw": "Test User <test@example.com>"},
        }
    )
    pull_request = BitbucketPullRequest.from_api_response(
        {
            "id": 1,
            "title": "Cloud",
            "state": "OPEN",
            "source": {"branch": {"name": "feature"}},
            "destination": {"branch": {"name": "main"}},
            "created_on": "2026-08-20T10:00:00+00:00",
        }
    )
    changes = CommitChanges.from_api_response(
        {
            "fromHash": "abc",
            "toHash": "def",
            "values": [
                {
                    "status": "modified",
                    "lines_added": 2,
                    "lines_removed": 1,
                    "new": {"path": "src/main.py"},
                }
            ],
        }
    )
    user = BitbucketUser.from_api_response(
        {"display_name": "Test User", "nickname": "test", "uuid": "{user}"}
    )

    assert (workspace.slug, workspace.uuid, workspace.public) == (
        "team",
        "{ws}",
        False,
    )
    assert (repository.full_name, repository.public) == ("team/repo", True)
    assert (branch.name, branch.latest_commit) == ("main", "abc")
    assert commit.id_ == "abc"
    assert commit.author and commit.author.email == "test@example.com"
    assert pull_request.open is True
    assert pull_request.from_ref == {"branch": {"name": "feature"}}
    assert changes.values and changes.values[0].lines_added == 2
    assert (user.display_name, user.nickname) == ("Test User", "test")
