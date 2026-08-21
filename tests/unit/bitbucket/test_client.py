"""Tests for selecting and configuring Bitbucket API clients."""

from unittest.mock import MagicMock, patch

import pytest

from mcp_atlassian.bitbucket.client import BitbucketClient
from mcp_atlassian.bitbucket.cloud import BitbucketCloudClient
from mcp_atlassian.bitbucket.config import BitbucketConfig
from mcp_atlassian.exceptions import MCPAtlassianAuthenticationError
from mcp_atlassian.utils.oauth import OAuthConfig


class TestBitbucketClient:
    """Test the Cloud versus Server/Data Center client boundary."""

    @pytest.fixture
    def basic_auth_config(self):
        return BitbucketConfig(
            url="https://bitbucket.org",
            auth_type="basic",
            username="test@example.com",
            api_token="api-token",
        )

    @pytest.fixture
    def server_pat_config(self):
        return BitbucketConfig(
            url="https://bitbucket.company.com",
            auth_type="pat",
            username="testuser",
            personal_token="pat-token",
        )

    @pytest.fixture
    def oauth_config(self):
        oauth = OAuthConfig(
            client_id="client-id",
            client_secret="client-secret",
            redirect_uri="http://localhost:8080/callback",
            scope="repository",
            cloud_id=None,
            access_token="oauth-token",
        )
        return BitbucketConfig(
            url="https://api.bitbucket.org",
            auth_type="oauth",
            oauth_config=oauth,
        )

    @patch("mcp_atlassian.bitbucket.client.configure_ssl_verification")
    @patch("mcp_atlassian.bitbucket.client.Session")
    def test_cloud_basic_auth_uses_native_client(
        self, mock_session, mock_ssl, basic_auth_config
    ):
        session = MagicMock()
        session.headers = {}
        session.proxies = {}
        mock_session.return_value = session

        client = BitbucketClient(basic_auth_config)

        assert isinstance(client.bitbucket, BitbucketCloudClient)
        assert client.bitbucket.base_url == "https://api.bitbucket.org/2.0"
        assert session.auth == ("test@example.com", "api-token")
        mock_ssl.assert_called_once()

    @patch("mcp_atlassian.bitbucket.client.configure_ssl_verification")
    @patch("mcp_atlassian.bitbucket.client.Bitbucket")
    def test_server_pat_keeps_legacy_client(
        self, mock_bitbucket, mock_ssl, server_pat_config
    ):
        legacy = MagicMock()
        legacy._session = MagicMock()
        legacy._session.headers = {}
        legacy._session.proxies = {}
        mock_bitbucket.return_value = legacy

        client = BitbucketClient(server_pat_config)

        assert client.bitbucket is legacy
        mock_bitbucket.assert_called_once_with(
            url="https://bitbucket.company.com",
            cloud=False,
            verify_ssl=True,
            token="pat-token",
        )
        mock_ssl.assert_called_once()

    @patch("mcp_atlassian.bitbucket.client.configure_ssl_verification")
    @patch("mcp_atlassian.bitbucket.client.configure_oauth_session")
    @patch("mcp_atlassian.bitbucket.client.Session")
    def test_cloud_oauth_uses_direct_api_without_cloud_id(
        self, mock_session, mock_configure_oauth, mock_ssl, oauth_config
    ):
        session = MagicMock()
        session.headers = {}
        session.proxies = {}
        mock_session.return_value = session
        mock_configure_oauth.return_value = True

        client = BitbucketClient(oauth_config)

        assert isinstance(client.bitbucket, BitbucketCloudClient)
        assert client.bitbucket.base_url == "https://api.bitbucket.org/2.0"
        mock_configure_oauth.assert_called_once_with(session, oauth_config.oauth_config)
        mock_ssl.assert_called_once()

    @patch("mcp_atlassian.bitbucket.client.configure_oauth_session")
    @patch("mcp_atlassian.bitbucket.client.Session")
    def test_oauth_configuration_failure_is_explicit(
        self, mock_session, mock_configure_oauth, oauth_config
    ):
        mock_configure_oauth.return_value = False

        with pytest.raises(
            MCPAtlassianAuthenticationError,
            match="Failed to configure OAuth session",
        ):
            BitbucketClient(oauth_config)

    @patch("mcp_atlassian.bitbucket.client.configure_ssl_verification")
    @patch("mcp_atlassian.bitbucket.client.Session")
    def test_cloud_bearer_token(self, mock_session, mock_ssl):
        session = MagicMock()
        session.headers = {}
        session.proxies = {}
        mock_session.return_value = session
        config = BitbucketConfig(
            url="https://api.bitbucket.org",
            auth_type="pat",
            personal_token="workspace-token",
        )

        BitbucketClient(config)

        assert session.headers["Authorization"] == "Bearer workspace-token"
        mock_ssl.assert_called_once()

    @patch("mcp_atlassian.bitbucket.client.configure_ssl_verification")
    @patch("mcp_atlassian.bitbucket.client.Session")
    def test_proxy_and_custom_header_configuration(self, mock_session, mock_ssl):
        session = MagicMock()
        session.headers = {}
        session.proxies = {}
        mock_session.return_value = session
        config = BitbucketConfig(
            url="https://api.bitbucket.org",
            auth_type="basic",
            username="test@example.com",
            api_token="token",
            http_proxy="http://proxy:8080",
            https_proxy="https://proxy:8443",
            custom_headers={"X-Custom": "value"},
        )

        BitbucketClient(config)

        assert session.proxies == {
            "http": "http://proxy:8080",
            "https": "https://proxy:8443",
        }
        assert session.headers["X-Custom"] == "value"
        mock_ssl.assert_called_once()

    @patch("mcp_atlassian.bitbucket.client.configure_ssl_verification")
    @patch("mcp_atlassian.bitbucket.client.Session")
    def test_cloud_activities_delegate_to_native_client(
        self, mock_session, mock_ssl, basic_auth_config
    ):
        session = MagicMock()
        session.headers = {}
        session.proxies = {}
        mock_session.return_value = session
        client = BitbucketClient(basic_auth_config)
        client.bitbucket.get_pull_request_activities = MagicMock(
            return_value=[{"id": 1}]
        )

        result = client.get_pull_request_activities("workspace", "repo", 1)

        assert result == [{"id": 1}]
        client.bitbucket.get_pull_request_activities.assert_called_once_with(
            "workspace", "repo", 1
        )

    @patch("mcp_atlassian.bitbucket.client.configure_ssl_verification")
    @patch("mcp_atlassian.bitbucket.client.Bitbucket")
    def test_server_activities_use_server_endpoint(
        self, mock_bitbucket, mock_ssl, server_pat_config
    ):
        legacy = MagicMock()
        legacy._session = MagicMock()
        legacy._session.headers = {}
        legacy._session.proxies = {}
        legacy.get.return_value = {"values": [{"id": 1}]}
        mock_bitbucket.return_value = legacy
        client = BitbucketClient(server_pat_config)

        result = client.get_pull_request_activities("project", "repo", 1)

        assert result == [{"id": 1}]
        legacy.get.assert_called_once_with(
            "projects/project/repos/repo/pull-requests/1/activities"
        )
