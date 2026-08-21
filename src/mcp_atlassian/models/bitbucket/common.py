"""
Common Bitbucket entity models.

This module provides Pydantic models for common Bitbucket entities like users, workspaces,
repositories, branches, pull requests, and commits.
"""

import logging
from typing import Any

from pydantic import Field

from ..base import ApiModel, TimestampMixin
from ..constants import (
    UNKNOWN,
)

logger = logging.getLogger(__name__)


class BitbucketUser(ApiModel):
    """Model representing a Bitbucket user."""

    name: str | None = None
    email: str | None = None
    active: bool | None = None
    display_name: str | None = None
    type: str | None = None
    links: dict[str, Any] | None = None
    uuid: str | None = None
    nickname: str | None = None
    account_id: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any], **kwargs: Any) -> "BitbucketUser":
        """Create a BitbucketUser from a Bitbucket API response."""
        if not data:
            return cls()

        nested_user = data.get("user")
        source = nested_user if isinstance(nested_user, dict) else data
        raw_author = str(data.get("raw") or "")
        raw_name, _, raw_email = raw_author.partition("<")
        return cls(
            name=source.get("name")
            or source.get("nickname")
            or source.get("username")
            or raw_name.strip()
            or None,
            email=source.get("emailAddress")
            or source.get("email")
            or raw_email.rstrip(">").strip()
            or None,
            display_name=source.get("displayName")
            or source.get("display_name")
            or raw_name.strip()
            or UNKNOWN,
            active=source.get("active"),
            type=source.get("type") or data.get("type"),
            links=source.get("links", {}),
            uuid=source.get("uuid"),
            nickname=source.get("nickname"),
            account_id=source.get("account_id"),
        )


class BitbucketWorkspace(ApiModel):
    """Model representing a Bitbucket workspace."""

    key: str | None = None
    name: str | None = None
    description: str | None = None
    public: bool = False
    type: str | None = None
    links: dict[str, Any] | None = None
    slug: str | None = None
    uuid: str | None = None
    is_private: bool | None = None
    created_on: str | None = None
    updated_on: str | None = None

    @classmethod
    def from_api_response(
        cls, data: dict[str, Any], **kwargs: Any
    ) -> "BitbucketWorkspace":
        """Create a BitbucketWorkspace from a Bitbucket API response."""
        if not data:
            return cls()

        return cls(
            name=data.get("name")
            or data.get("slug")
            or data.get("key")
            or data.get("uuid")
            or UNKNOWN,
            type=data.get("type"),
            description=data.get("description"),
            public=data.get("public", not data.get("is_private", True)),
            links=data.get("links"),
            key=data.get("key"),
            slug=data.get("slug"),
            uuid=data.get("uuid"),
            is_private=data.get("is_private"),
            created_on=data.get("created_on"),
            updated_on=data.get("updated_on"),
        )


class BitbucketRepository(ApiModel):
    """Model representing a Bitbucket repository."""

    slug: str | None = None
    name: str | None = None
    description: str | None = None
    state: str | None = None
    forkable: bool | None = True
    project: dict[str, Any] | None = None
    public: bool | None = False
    archived: bool | None = False
    links: dict[str, Any] | None = None
    uuid: str | None = None
    full_name: str | None = None
    is_private: bool | None = None
    scm: str | None = None
    language: str | None = None
    size: int | None = None
    mainbranch: dict[str, Any] | None = None
    owner: dict[str, Any] | None = None
    created_on: str | None = None
    updated_on: str | None = None

    @classmethod
    def from_api_response(
        cls, data: dict[str, Any], **kwargs: Any
    ) -> "BitbucketRepository":
        """Create a BitbucketRepository from a Bitbucket API response."""
        if not data:
            return cls()

        return cls(
            slug=data.get("slug"),
            name=data.get("name"),
            description=data.get("description"),
            state=data.get("state"),
            forkable=data.get("forkable", data.get("fork_policy") != "no_forks"),
            project=data.get("project", {}),
            public=data.get("public", not data.get("is_private", True)),
            archived=data.get("archived", False),
            links=data.get("links", {}),
            uuid=data.get("uuid"),
            full_name=data.get("full_name"),
            is_private=data.get("is_private"),
            scm=data.get("scm"),
            language=data.get("language"),
            size=data.get("size"),
            mainbranch=data.get("mainbranch"),
            owner=data.get("owner"),
            created_on=data.get("created_on"),
            updated_on=data.get("updated_on"),
        )


class BitbucketBranch(ApiModel):
    """Model representing a Bitbucket branch."""

    id_: str | None = Field(default=None, alias="id")
    name: str | None = None
    type: str | None = None
    latest_commit: str | None = None
    latest_changeset: str | None = None
    is_default: bool | None = False
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_api_response(
        cls, data: dict[str, Any], **kwargs: Any
    ) -> "BitbucketBranch":
        """Create a BitbucketBranch from a Bitbucket API response."""
        if not data:
            return cls()

        target = data.get("target") if isinstance(data.get("target"), dict) else {}
        branch_name = data.get("displayId") or data.get("name") or UNKNOWN
        return cls(
            name=branch_name,
            id=data.get("id") or branch_name,
            type=data.get("type"),
            latest_commit=data.get("latestCommit") or target.get("hash"),
            latest_changeset=data.get("latestChangeset"),
            is_default=data.get("isDefault", False),
            metadata=data.get("metadata") or target,
        )


class BitbucketCommit(ApiModel):
    """Model representing a Bitbucket commit."""

    id_: str | None = Field(default=None, alias="id")
    message: str | None = None
    author: BitbucketUser | None = None
    committer: BitbucketUser | None = None
    parents: list[dict[str, Any]] = Field(default_factory=list)
    author_timestamp: int | str | None = None
    committer_timestamp: int | str | None = None

    @classmethod
    def from_api_response(
        cls, data: dict[str, Any], **kwargs: Any
    ) -> "BitbucketCommit":
        """Create a BitbucketCommit from a Bitbucket API response."""
        if not data:
            return cls()

        return cls(
            id=data.get("id") or data.get("hash"),
            message=data.get("message"),
            author=BitbucketUser.from_api_response(data.get("author", {}))
            if data.get("author")
            else None,
            committer=BitbucketUser.from_api_response(data.get("committer", {})),
            author_timestamp=data.get("authorTimestamp") or data.get("date"),
            committer_timestamp=data.get("committerTimestamp") or data.get("date"),
            parents=data.get("parents", []),
        )


class BitbucketPullRequest(ApiModel, TimestampMixin):
    """Model representing a Bitbucket pull request."""

    id_: int | None = Field(default=None, alias="id")
    version: int | None = None
    title: str | None = None
    description: str | None = None
    state: str | None = None
    open: bool | None = False
    draft: bool | None = False
    closed: bool | None = False
    created_date: int | str | None = None
    updated_date: int | str | None = None
    closed_date: int | str | None = None
    from_ref: dict[str, Any] | None = None
    to_ref: dict[str, Any] | None = None
    locked: bool | None = False
    author: dict[str, Any] | None = None
    reviewers: list[dict[str, Any]] | None = None
    participants: list[dict[str, Any]] | None = None
    links: dict[str, Any] | None = None

    @classmethod
    def from_api_response(
        cls, data: dict[str, Any], **kwargs: Any
    ) -> "BitbucketPullRequest":
        """Create a BitbucketPullRequest from a Bitbucket API response."""
        if not data:
            return cls()

        state = data.get("state")
        return cls(
            id=data.get("id"),
            version=data.get("version"),
            title=data.get("title", UNKNOWN),
            description=data.get("description"),
            state=data.get("state"),
            open=data.get("open", state == "OPEN"),
            draft=data.get("draft", False),
            closed=data.get("closed", state in {"MERGED", "DECLINED", "SUPERSEDED"}),
            author=data.get("author"),
            created_date=data.get("createdDate") or data.get("created_on"),
            updated_date=data.get("updatedDate") or data.get("updated_on"),
            closed_date=data.get("closedDate") or data.get("closed_on"),
            from_ref=data.get("fromRef") or data.get("source"),
            to_ref=data.get("toRef") or data.get("destination"),
            locked=data.get("locked"),
            reviewers=data.get("reviewers", []),
            participants=data.get("participants", []),
            links=data.get("links"),
        )


class CommitChange(ApiModel):
    content_id: str | None = None
    from_content_id: str | None = None
    path: dict[str, Any] | None = None
    executable: bool | None = None
    percent_unchanged: int | None = None
    type: str | None = None
    node_type: str | None = None
    src_executable: bool | None = None
    links: dict[str, Any] | None = None
    properties: dict[str, Any] | None = None
    status: str | None = None
    old: dict[str, Any] | None = None
    new: dict[str, Any] | None = None
    lines_added: int | None = None
    lines_removed: int | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any], **kwargs: Any) -> "CommitChange":
        if not data:
            return cls()
        old = data.get("old") if isinstance(data.get("old"), dict) else None
        new = data.get("new") if isinstance(data.get("new"), dict) else None
        path = data.get("path") or new or old
        return cls(
            content_id=data.get("contentId"),
            from_content_id=data.get("fromContentId"),
            path=path,
            executable=data.get("executable"),
            percent_unchanged=data.get("percentUnchanged"),
            type=data.get("type"),
            node_type=data.get("nodeType"),
            src_executable=data.get("srcExecutable"),
            links=data.get("links"),
            properties=data.get("properties"),
            status=data.get("status"),
            old=old,
            new=new,
            lines_added=data.get("lines_added"),
            lines_removed=data.get("lines_removed"),
        )


class CommitChanges(ApiModel):
    from_hash: str | None = None
    to_hash: str | None = None
    properties: dict[str, Any] | None = None
    values: list[CommitChange] | None = None
    size: int | None = None
    is_last_page: bool | None = None
    start: int | None = 0
    limit: int | None = 25
    next_page_start: int | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any], **kwargs: Any) -> "CommitChanges":
        if not data:
            return cls()
        return cls(
            from_hash=data.get("fromHash"),
            to_hash=data.get("toHash"),
            properties=data.get("properties"),
            values=[
                CommitChange.from_api_response(item) for item in data.get("values", [])
            ]
            if data.get("values")
            else None,
            size=data.get("size", len(data.get("values", []))),
            is_last_page=data.get("isLastPage", not bool(data.get("next"))),
            start=data.get("start", 0),
            limit=data.get("limit", 25),
            next_page_start=data.get("nextPageStart"),
        )
