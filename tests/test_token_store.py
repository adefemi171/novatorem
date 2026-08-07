import os
import unittest
from unittest.mock import patch

from spotify_tokens import SpotifyTokenStore


class SpotifyTokenStoreTest(unittest.TestCase):
    def test_detects_vercel_upstash_prefixed_credentials(self):
        env = {
            "UPSTASH_REDIS_REST_KV_REST_API_URL": "https://example.upstash.io",
            "UPSTASH_REDIS_REST_KV_REST_API_TOKEN": "token",
        }
        with patch.dict(os.environ, env, clear=True):
            store = SpotifyTokenStore()

        self.assertEqual(store.url, env["UPSTASH_REDIS_REST_KV_REST_API_URL"])
        self.assertEqual(
            store.token, env["UPSTASH_REDIS_REST_KV_REST_API_TOKEN"]
        )
        self.assertTrue(store.writable)


if __name__ == "__main__":
    unittest.main()
