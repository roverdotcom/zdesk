import pytest
from unittest.mock import MagicMock, patch

from zdesk import Zendesk
from zdesk.zdesk import AuthenticationError

ZDESK_URL = 'https://example.zendesk.com'
CLIENT_ID = 'test_client_id'
CLIENT_SECRET = 'test_client_secret'
ACCESS_TOKEN = 'test_access_token'

TOKEN_RESPONSE = {
    'access_token': ACCESS_TOKEN,
    'token_type': 'bearer',
    'expires_in': 3600,
}


def _mock_token_response(status_code=200, json_data=None):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data or TOKEN_RESPONSE
    mock_resp.content = b'{"access_token": "test_access_token"}'
    return mock_resp


class TestFetchOauthToken:
    def test_sets_zdesk_oauth_on_success(self):
        zd = Zendesk(ZDESK_URL)
        zd.client.post = MagicMock(return_value=_mock_token_response())

        zd.fetch_oauth_token(CLIENT_ID, CLIENT_SECRET)

        assert zd.zdesk_oauth == ACCESS_TOKEN

    def test_returns_full_token_response(self):
        zd = Zendesk(ZDESK_URL)
        zd.client.post = MagicMock(return_value=_mock_token_response())

        result = zd.fetch_oauth_token(CLIENT_ID, CLIENT_SECRET)

        assert result == TOKEN_RESPONSE

    def test_returns_expires_in(self):
        zd = Zendesk(ZDESK_URL)
        zd.client.post = MagicMock(return_value=_mock_token_response())

        result = zd.fetch_oauth_token(CLIENT_ID, CLIENT_SECRET)

        assert 'expires_in' in result

    def test_posts_correct_payload_to_oauth_tokens_endpoint(self):
        zd = Zendesk(ZDESK_URL)
        zd.client.post = MagicMock(return_value=_mock_token_response())

        zd.fetch_oauth_token(CLIENT_ID, CLIENT_SECRET)

        zd.client.post.assert_called_once_with(
            ZDESK_URL + '/oauth/tokens',
            data={
                'grant_type': 'client_credentials',
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
            },
        )

    def test_raises_authentication_error_on_failure(self):
        zd = Zendesk(ZDESK_URL)
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.content = b'Unauthorized'
        zd.client.post = MagicMock(return_value=mock_resp)

        with pytest.raises(AuthenticationError) as exc_info:
            zd.fetch_oauth_token(CLIENT_ID, CLIENT_SECRET)

        assert exc_info.value.error_code == 401

    def test_bearer_token_used_in_auth_header(self):
        zd = Zendesk(ZDESK_URL)
        zd.client.post = MagicMock(return_value=_mock_token_response())

        zd.fetch_oauth_token(CLIENT_ID, CLIENT_SECRET)

        assert zd.headers.get('Authorization') == 'Bearer ' + ACCESS_TOKEN
        assert zd.client.auth is None


class TestTokenRefresh:
    def test_call_refreshes_when_token_expired(self):
        zd = Zendesk(ZDESK_URL)
        zd.client.post = MagicMock(return_value=_mock_token_response())
        zd.fetch_oauth_token(CLIENT_ID, CLIENT_SECRET)

        # Force the token to look expired.
        zd._oauth_expires_at = 0
        zd.client.request = MagicMock(
            return_value=MagicMock(status_code=200, headers={}, content=b''))

        zd.call('/api/v2/tickets.json')

        # One initial fetch plus one refresh triggered by the expired token.
        assert zd.client.post.call_count == 2

    def test_call_does_not_refresh_when_token_valid(self):
        zd = Zendesk(ZDESK_URL)
        zd.client.post = MagicMock(return_value=_mock_token_response())
        zd.fetch_oauth_token(CLIENT_ID, CLIENT_SECRET)

        zd.client.request = MagicMock(
            return_value=MagicMock(status_code=200, headers={}, content=b''))

        zd.call('/api/v2/tickets.json')

        # Only the initial fetch; the token is still well within its lifetime.
        assert zd.client.post.call_count == 1

    def test_no_refresh_when_expires_in_absent(self):
        zd = Zendesk(ZDESK_URL)
        no_expiry = {'access_token': ACCESS_TOKEN, 'token_type': 'bearer'}
        zd.client.post = MagicMock(
            return_value=_mock_token_response(json_data=no_expiry))
        zd.fetch_oauth_token(CLIENT_ID, CLIENT_SECRET)

        assert zd._oauth_expires_at is None

        zd.client.request = MagicMock(
            return_value=MagicMock(status_code=200, headers={}, content=b''))
        zd.call('/api/v2/tickets.json')

        # Non-expiring token is never proactively refreshed.
        assert zd.client.post.call_count == 1

    def test_no_refresh_for_non_oauth_auth(self):
        zd = Zendesk(ZDESK_URL, zdesk_email='user@example.com',
                     zdesk_api='api_token')
        zd.client.post = MagicMock()
        zd.client.request = MagicMock(
            return_value=MagicMock(status_code=200, headers={}, content=b''))

        zd.call('/api/v2/tickets.json')

        zd.client.post.assert_not_called()


class TestUseOauthConstructor:
    def test_fetches_token_when_use_oauth_true(self):
        with patch.object(Zendesk, 'fetch_oauth_token') as mock_fetch:
            mock_fetch.return_value = TOKEN_RESPONSE
            Zendesk(ZDESK_URL, use_oauth=True, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)

        mock_fetch.assert_called_once_with(CLIENT_ID, CLIENT_SECRET)

    def test_raises_without_client_id(self):
        with pytest.raises(ValueError, match='client_id and client_secret are required'):
            Zendesk(ZDESK_URL, use_oauth=True, client_secret=CLIENT_SECRET)

    def test_raises_without_client_secret(self):
        with pytest.raises(ValueError, match='client_id and client_secret are required'):
            Zendesk(ZDESK_URL, use_oauth=True, client_id=CLIENT_ID)

    def test_no_oauth_fetch_when_use_oauth_false(self):
        with patch.object(Zendesk, 'fetch_oauth_token') as mock_fetch:
            Zendesk(ZDESK_URL, use_oauth=False, zdesk_email='user@example.com', zdesk_api='api_token')

        mock_fetch.assert_not_called()

    def test_no_oauth_fetch_by_default(self):
        with patch.object(Zendesk, 'fetch_oauth_token') as mock_fetch:
            Zendesk(ZDESK_URL)

        mock_fetch.assert_not_called()

    def test_api_token_auth_used_when_use_oauth_false(self):
        zd = Zendesk(ZDESK_URL, use_oauth=False,
                     zdesk_email='user@example.com', zdesk_api='api_token')

        assert zd.client.auth == ('user@example.com/token', 'api_token')
        assert 'Authorization' not in zd.headers
