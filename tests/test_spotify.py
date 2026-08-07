import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("SPOTIFY_CLIENT_ID", "client-id")
os.environ.setdefault("SPOTIFY_SECRET_ID", "client-secret")

from api import spotify


class SpotifyRoutesTest(unittest.TestCase):
    def setUp(self):
        spotify.app.config.update(TESTING=True)
        self.client = spotify.app.test_client()
        self.original_reconnect_secret = spotify.RECONNECT_SECRET
        self.original_reminder_secret = spotify.REMINDER_SECRET
        self.original_token_store = spotify.TOKEN_STORE
        spotify.RECONNECT_SECRET = "reconnect-test-secret"
        spotify.REMINDER_SECRET = "reminder-test-secret"
        spotify.TOKEN_STORE = Mock(
            writable=True,
            status=Mock(
                return_value={
                    "connected": True,
                    "expires_at": "2027-02-03T00:00:00+00:00",
                    "storage_configured": True,
                }
            ),
        )

    def tearDown(self):
        spotify.RECONNECT_SECRET = self.original_reconnect_secret
        spotify.REMINDER_SECRET = self.original_reminder_secret
        spotify.TOKEN_STORE = self.original_token_store

    def unlock_admin(self):
        return self.client.post(
            "/api/spotify-admin/manage",
            data={"secret": "reconnect-test-secret"},
        )

    def test_card_returns_svg_fallback_when_spotify_fails(self):
        with patch.object(spotify, "get", side_effect=spotify.SpotifyAuthError()):
            response = self.client.get(
                "/?background_color=not-a-color&border_color=ffffff"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/svg+xml")
        self.assertEqual(response.headers["X-Spotify-Status"], "reconnect-required")
        self.assertIn(b"Spotify connection needs renewal", response.data)
        self.assertIn(b'fill="#181414"', response.data)

    def test_management_page_requires_secret(self):
        response = self.client.get("/api/spotify-admin/manage")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Management secret", response.data)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_unlock_then_login_redirects_to_spotify(self):
        unlock = self.unlock_admin()
        self.assertEqual(unlock.status_code, 302)

        response = self.client.get("/api/spotify-admin/login")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.startswith("https://accounts.spotify.com/authorize?"))
        self.assertIn("state=", response.location)
        self.assertIn("user-read-currently-playing", response.location)

    def test_callback_persists_refresh_token(self):
        state = spotify._signed_value("spotify_oauth")
        token_response = Mock(
            status_code=200,
            json=Mock(
                return_value={
                    "access_token": "access-token",
                    "refresh_token": "new-refresh-token",
                }
            ),
        )

        with patch.object(spotify.requests, "post", return_value=token_response):
            response = self.client.get(
                "/api/spotify-admin/callback",
                query_string={"code": "code", "state": state},
            )

        self.assertEqual(response.status_code, 302)
        spotify.TOKEN_STORE.save_authorization.assert_called_once_with(
            "new-refresh-token"
        )
        self.assertTrue(response.location.endswith("/api/spotify-admin/manage?connected=1"))

    def test_status_requires_reminder_secret(self):
        unauthorized = self.client.get("/api/spotify-admin/status")
        authorized = self.client.get(
            "/api/spotify-admin/status",
            headers={"Authorization": "Bearer reminder-test-secret"},
        )

        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(authorized.status_code, 200)
        self.assertTrue(authorized.get_json()["connected"])


if __name__ == "__main__":
    unittest.main()
