"""
Tests unitaires — legifrance/auth.py
Teste get_token() (OAuth2) et hdrs() (headers HTTP).
"""
import pytest
import requests
from unittest.mock import patch, MagicMock

from legifrance.auth import get_token, hdrs


# ── get_token() ───────────────────────────────────────────────────────────────

class TestGetToken:
    def _mock_ok(self, token_value="tok_abc"):
        resp = MagicMock()
        resp.json.return_value = {"access_token": token_value}
        resp.raise_for_status.return_value = None
        return resp

    def test_returns_access_token_string(self):
        with patch("requests.post", return_value=self._mock_ok("returned_token")):
            tok = get_token()
        assert tok == "returned_token"

    def test_return_type_is_str(self):
        with patch("requests.post", return_value=self._mock_ok("xyz")):
            tok = get_token()
        assert isinstance(tok, str)

    def test_calls_oauth_url(self):
        from legifrance.config import OAUTH_URL
        with patch("requests.post", return_value=self._mock_ok()) as mock_post:
            get_token()
        called_url = mock_post.call_args[0][0]
        assert called_url == OAUTH_URL

    def test_sends_client_credentials_grant_type(self):
        with patch("requests.post", return_value=self._mock_ok()) as mock_post:
            get_token()
        data = mock_post.call_args[1]["data"]
        assert data.get("grant_type") == "client_credentials"

    def test_sends_client_id_and_secret(self):
        from legifrance.config import CLIENT_ID, CLIENT_SECRET
        with patch("requests.post", return_value=self._mock_ok()) as mock_post:
            get_token()
        data = mock_post.call_args[1]["data"]
        assert data.get("client_id") == CLIENT_ID
        assert data.get("client_secret") == CLIENT_SECRET

    def test_sends_openid_scope(self):
        with patch("requests.post", return_value=self._mock_ok()) as mock_post:
            get_token()
        data = mock_post.call_args[1]["data"]
        assert data.get("scope") == "openid"

    def test_raises_http_error_on_bad_status(self):
        resp = MagicMock()
        resp.raise_for_status.side_effect = requests.HTTPError("401 Unauthorized")
        with patch("requests.post", return_value=resp):
            with pytest.raises(requests.HTTPError):
                get_token()

    def test_raises_key_error_if_no_access_token(self):
        resp = MagicMock()
        resp.json.return_value = {"error": "invalid_client"}
        resp.raise_for_status.return_value = None
        with patch("requests.post", return_value=resp):
            with pytest.raises(KeyError):
                get_token()

    def test_raises_on_network_error(self):
        with patch("requests.post", side_effect=requests.ConnectionError("timeout")):
            with pytest.raises(requests.ConnectionError):
                get_token()


# ── hdrs() ────────────────────────────────────────────────────────────────────

class TestHdrs:
    def test_authorization_header_present(self):
        h = hdrs("my_token")
        assert "Authorization" in h

    def test_bearer_format(self):
        h = hdrs("abc123")
        assert h["Authorization"] == "Bearer abc123"

    def test_key_id_present(self):
        from legifrance.config import API_KEY
        h = hdrs("tok")
        assert h["KeyId"] == API_KEY

    def test_content_type_json(self):
        h = hdrs("tok")
        assert h["Content-Type"] == "application/json"

    def test_accept_json(self):
        h = hdrs("tok")
        assert h["Accept"] == "application/json"

    def test_all_four_keys_present(self):
        h = hdrs("tok")
        assert {"Authorization", "KeyId", "Content-Type", "Accept"}.issubset(h.keys())

    def test_different_tokens_produce_different_auth(self):
        assert hdrs("token_A")["Authorization"] != hdrs("token_B")["Authorization"]

    def test_returns_dict(self):
        assert isinstance(hdrs("tok"), dict)
