import unittest
from unittest import mock
import os
import json
import spotipy # For exceptions

# Modules to test
from migration_app.auth.spotify_auth import SpotifyAuthenticator, SpotifyAuthError, TOKEN_CACHE_PATH
from migration_app.ui.cli import get_spotify_credentials # Assuming cli.py is structured to allow this import
import click # For click.Abort in error cases from cli helpers

# Dummy Spotify credentials for testing
DUMMY_CLIENT_ID = "test_client_id"
DUMMY_CLIENT_SECRET = "test_client_secret"
DUMMY_REDIRECT_URI = "http://localhost/callback"
DUMMY_SCOPE = "user-library-read"

DUMMY_TOKEN_INFO = {
    'access_token': 'dummy_access_token',
    'refresh_token': 'dummy_refresh_token',
    'expires_at': 1678886400  # Some future time
}
DUMMY_REFRESHED_TOKEN_INFO = {
    'access_token': 'refreshed_access_token',
    'refresh_token': 'new_dummy_refresh_token',
    'expires_at': 1678890000
}


class TestSpotifyAuthenticator(unittest.TestCase):

    @mock.patch('migration_app.auth.spotify_auth.SpotifyOAuth')
    @mock.patch('migration_app.auth.spotify_auth.os.path.exists')
    @mock.patch('migration_app.auth.spotify_auth.open', new_callable=mock.mock_open)
    def test_get_spotify_client_new_auth_success(self, mock_file_open, mock_os_exists, MockSpotifyOAuth):
        # Simulate no cache exists initially
        mock_os_exists.return_value = False

        # Configure SpotifyOAuth mock instance
        mock_oauth_instance = MockSpotifyOAuth.return_value
        mock_oauth_instance.get_access_token.return_value = DUMMY_TOKEN_INFO
        mock_oauth_instance.validate_token.return_value = DUMMY_TOKEN_INFO # if spotipy uses this
        mock_oauth_instance.parse_response_code.return_value = "dummy_code"
        mock_oauth_instance.get_authorize_url.return_value = "http://dummyauthurl.com"


        authenticator = SpotifyAuthenticator(DUMMY_CLIENT_ID, DUMMY_CLIENT_SECRET, DUMMY_REDIRECT_URI, DUMMY_SCOPE)

        with mock.patch('spotipy.Spotify') as MockSpotifyClient:
            client = authenticator.get_spotify_client()
            MockSpotifyOAuth.assert_called_with(
                client_id=DUMMY_CLIENT_ID,
                client_secret=DUMMY_CLIENT_SECRET,
                redirect_uri=DUMMY_REDIRECT_URI,
                scope=DUMMY_SCOPE,
                cache_path=TOKEN_CACHE_PATH,
                show_dialog=True
            )
            # Spotipy's get_access_token is called to handle cache or new token
            mock_oauth_instance.get_access_token.assert_called_with(check_cache=True)
            MockSpotifyClient.assert_called_with(auth=DUMMY_TOKEN_INFO['access_token'])
            self.assertIsNotNone(client)

    @mock.patch('migration_app.auth.spotify_auth.SpotifyOAuth')
    @mock.patch('migration_app.auth.spotify_auth.os.path.exists')
    @mock.patch('migration_app.auth.spotify_auth.open', new_callable=mock.mock_open)
    def test_get_spotify_client_cached_token_success(self, mock_file_open, mock_os_exists, MockSpotifyOAuth):
        mock_os_exists.return_value = True
        mock_file_open.return_value.read.return_value = json.dumps(DUMMY_TOKEN_INFO)

        mock_oauth_instance = MockSpotifyOAuth.return_value
        # Simulate spotipy finding the token via cache_path mechanism or internal check
        mock_oauth_instance.get_access_token.return_value = DUMMY_TOKEN_INFO

        authenticator = SpotifyAuthenticator(DUMMY_CLIENT_ID, DUMMY_CLIENT_SECRET, DUMMY_REDIRECT_URI, DUMMY_SCOPE)

        with mock.patch('spotipy.Spotify') as MockSpotifyClient:
            client = authenticator.get_spotify_client()
            # Assert that get_access_token was called, which would utilize the cache
            mock_oauth_instance.get_access_token.assert_called_with(check_cache=True)
            MockSpotifyClient.assert_called_with(auth=DUMMY_TOKEN_INFO['access_token'])
            self.assertIsNotNone(client)
            # Check that file was opened for reading cache
            mock_file_open.assert_called_with(TOKEN_CACHE_PATH, 'r')


    @mock.patch('migration_app.auth.spotify_auth.SpotifyOAuth')
    @mock.patch('migration_app.auth.spotify_auth.os.path.exists')
    @mock.patch('migration_app.auth.spotify_auth.open', new_callable=mock.mock_open)
    def test_get_spotify_client_token_refresh_scenario(self, mock_file_open, mock_os_exists, MockSpotifyOAuth):
        # Simulate cache exists with an "expired" token that spotipy will refresh
        mock_os_exists.return_value = True
        # Let's say the cache file initially has old token info, but spotipy handles refresh via get_access_token
        mock_file_open.return_value.read.return_value = json.dumps(DUMMY_TOKEN_INFO)


        mock_oauth_instance = MockSpotifyOAuth.return_value
        # get_access_token is expected to handle the refresh if needed and return the new token
        mock_oauth_instance.get_access_token.return_value = DUMMY_REFRESHED_TOKEN_INFO
        # mock_oauth_instance.refresh_access_token.return_value = DUMMY_REFRESHED_TOKEN_INFO # If we were testing refresh_access_token directly

        authenticator = SpotifyAuthenticator(DUMMY_CLIENT_ID, DUMMY_CLIENT_SECRET, DUMMY_REDIRECT_URI, DUMMY_SCOPE)

        with mock.patch('spotipy.Spotify') as MockSpotifyClient:
            client = authenticator.get_spotify_client()
            mock_oauth_instance.get_access_token.assert_called_with(check_cache=True)
            MockSpotifyClient.assert_called_with(auth=DUMMY_REFRESHED_TOKEN_INFO['access_token'])
            self.assertIsNotNone(client)

    @mock.patch('migration_app.auth.spotify_auth.SpotifyOAuth')
    @mock.patch('migration_app.auth.spotify_auth.os.path.exists')
    def test_get_spotify_client_auth_failure(self, mock_os_exists, MockSpotifyOAuth):
        mock_os_exists.return_value = False # No cache
        mock_oauth_instance = MockSpotifyOAuth.return_value
        mock_oauth_instance.get_access_token.side_effect = spotipy.SpotifyException("auth_code", "400", "Auth failed")

        authenticator = SpotifyAuthenticator(DUMMY_CLIENT_ID, DUMMY_CLIENT_SECRET, DUMMY_REDIRECT_URI, DUMMY_SCOPE)
        with self.assertRaises(SpotifyAuthError):
            authenticator.get_spotify_client()

    @mock.patch('migration_app.auth.spotify_auth.SpotifyOAuth')
    @mock.patch('migration_app.auth.spotify_auth.os.path.exists')
    @mock.patch('builtins.input') # For mocking the input() call
    def test_get_spotify_client_manual_redirect_flow(self, mock_input, mock_os_exists, MockSpotifyOAuth):
        mock_os_exists.return_value = False # No cache
        mock_oauth_instance = MockSpotifyOAuth.return_value

        # First call to get_access_token (check_cache=True) returns None, triggering manual flow
        # Second call to get_access_token (with code) returns token
        mock_oauth_instance.get_access_token.side_effect = [None, DUMMY_TOKEN_INFO]

        mock_oauth_instance.get_authorize_url.return_value = "http://dummyauthurl.com"
        mock_input.return_value = "http://localhost/callback?code=dummy_code_from_redirect" # User pastes this
        mock_oauth_instance.parse_response_code.return_value = "dummy_code_from_redirect"

        authenticator = SpotifyAuthenticator(DUMMY_CLIENT_ID, DUMMY_CLIENT_SECRET, DUMMY_REDIRECT_URI, DUMMY_SCOPE)

        with mock.patch('spotipy.Spotify') as MockSpotifyClient:
            client = authenticator.get_spotify_client()

            self.assertEqual(mock_oauth_instance.get_access_token.call_count, 2)
            mock_oauth_instance.get_access_token.assert_any_call(check_cache=True)
            mock_oauth_instance.get_access_token.assert_any_call("dummy_code_from_redirect", check_cache=False)

            mock_input.assert_called_once_with("Enter the URL you were redirected to: ")
            mock_oauth_instance.parse_response_code.assert_called_with("http://localhost/callback?code=dummy_code_from_redirect")
            MockSpotifyClient.assert_called_with(auth=DUMMY_TOKEN_INFO['access_token'])
            self.assertIsNotNone(client)


class TestCliHelpers(unittest.TestCase):

    @mock.patch('migration_app.ui.cli.os.getenv')
    @mock.patch('migration_app.ui.cli.click.prompt')
    def test_get_spotify_credentials_all_env(self, mock_click_prompt, mock_os_getenv):
        # Side effect for os.getenv to return values based on input
        def getenv_side_effect(key):
            if key == 'SPOTIPY_CLIENT_ID': return 'env_client_id'
            if key == 'SPOTIPY_CLIENT_SECRET': return 'env_client_secret'
            if key == 'SPOTIPY_REDIRECT_URI': return 'env_redirect_uri'
            return None
        mock_os_getenv.side_effect = getenv_side_effect

        client_id, client_secret, redirect_uri = get_spotify_credentials()

        self.assertEqual(client_id, 'env_client_id')
        self.assertEqual(client_secret, 'env_client_secret')
        self.assertEqual(redirect_uri, 'env_redirect_uri')
        mock_click_prompt.assert_not_called()

    @mock.patch('migration_app.ui.cli.os.getenv')
    @mock.patch('migration_app.ui.cli.click.prompt')
    def test_get_spotify_credentials_all_prompt(self, mock_click_prompt, mock_os_getenv):
        mock_os_getenv.return_value = None # No env vars set

        # Side effect for click.prompt
        def prompt_side_effect(text, type, hide_input=None): # Adjusted for hide_input arg
            if "Client ID" in text: return "prompt_client_id"
            if "Client Secret" in text: return "prompt_client_secret"
            if "Redirect URI" in text: return "prompt_redirect_uri"
            return None # Should not happen
        mock_click_prompt.side_effect = prompt_side_effect

        client_id, client_secret, redirect_uri = get_spotify_credentials()

        self.assertEqual(client_id, 'prompt_client_id')
        self.assertEqual(client_secret, 'prompt_client_secret')
        self.assertEqual(redirect_uri, 'prompt_redirect_uri')
        self.assertEqual(mock_click_prompt.call_count, 3)


    @mock.patch('migration_app.ui.cli.os.getenv')
    @mock.patch('migration_app.ui.cli.click.prompt')
    def test_get_spotify_credentials_mixed_env_prompt(self, mock_click_prompt, mock_os_getenv):
        # Client ID from env, others from prompt
        def getenv_side_effect(key):
            if key == 'SPOTIPY_CLIENT_ID': return 'env_client_id'
            return None # Other vars not set
        mock_os_getenv.side_effect = getenv_side_effect

        def prompt_side_effect(text, type, hide_input=None):
            if "Client Secret" in text: return "prompt_client_secret"
            if "Redirect URI" in text: return "prompt_redirect_uri"
            return None
        mock_click_prompt.side_effect = prompt_side_effect

        client_id, client_secret, redirect_uri = get_spotify_credentials()

        self.assertEqual(client_id, 'env_client_id')
        self.assertEqual(client_secret, 'prompt_client_secret')
        self.assertEqual(redirect_uri, 'prompt_redirect_uri')
        self.assertEqual(mock_click_prompt.call_count, 2)
        mock_click_prompt.assert_any_call("Enter your Spotify Client Secret", type=str, hide_input=True)
        mock_click_prompt.assert_any_call("Enter your Spotify Redirect URI", type=str)


# (Existing imports and TestSpotifyAuthenticator, TestCliHelpers should remain)
# ...

from migration_app.auth.ytmusic_auth import YouTubeMusicAuthenticator, YouTubeMusicAuthError, YT_AUTH_HEADERS_PATH
from ytmusicapi import YTMusic # For YTMusic class itself
import json # For JSONDecodeError

# ... (Keep DUMMY_TOKEN_INFO etc. if they are not already there, though not directly used by YT tests)

class TestYouTubeMusicAuthenticator(unittest.TestCase):

    @mock.patch('migration_app.auth.ytmusic_auth.YTMusic')
    @mock.patch('migration_app.auth.ytmusic_auth.os.path.exists')
    def test_get_ytmusic_client_success(self, mock_os_exists, MockYTMusic):
        mock_os_exists.return_value = True  # Simulate headers_auth.json exists

        mock_ytmusic_instance = MockYTMusic.return_value
        # Simulate the internal test call (e.g., get_library_playlists) succeeding
        mock_ytmusic_instance.get_library_playlists.return_value = [{"title": "Test PL"}]

        authenticator = YouTubeMusicAuthenticator()
        client = authenticator.get_ytmusic_client()

        MockYTMusic.assert_called_once_with(YT_AUTH_HEADERS_PATH)
        mock_ytmusic_instance.get_library_playlists.assert_called_once_with(limit=1)
        self.assertIsNotNone(client)
        self.assertEqual(client, mock_ytmusic_instance)

    @mock.patch('migration_app.auth.ytmusic_auth.os.path.exists')
    def test_get_ytmusic_client_file_missing_triggers_setup_error(self, mock_os_exists):
        mock_os_exists.return_value = False  # Simulate headers_auth.json does NOT exist

        authenticator = YouTubeMusicAuthenticator()
        with self.assertRaisesRegex(YouTubeMusicAuthError, "Authentication file 'headers_auth.json' not found"):
            authenticator.get_ytmusic_client()
        # Ensure setup_authentication (which prints instructions and raises) was effectively called.
        # The current implementation of setup_authentication directly raises an error.

    @mock.patch('migration_app.auth.ytmusic_auth.YTMusic')
    @mock.patch('migration_app.auth.ytmusic_auth.os.path.exists')
    def test_get_ytmusic_client_stale_credentials_api_call_fails(self, mock_os_exists, MockYTMusic):
        mock_os_exists.return_value = True # File exists

        mock_ytmusic_instance = MockYTMusic.return_value
        # Simulate the internal test call failing (e.g., due to stale credentials)
        mock_ytmusic_instance.get_library_playlists.side_effect = Exception("API call failed, token stale")

        authenticator = YouTubeMusicAuthenticator()
        with self.assertRaisesRegex(YouTubeMusicAuthError, "Failed to connect to YouTube Music with existing 'headers_auth.json'"):
            authenticator.get_ytmusic_client()

        MockYTMusic.assert_called_once_with(YT_AUTH_HEADERS_PATH)
        mock_ytmusic_instance.get_library_playlists.assert_called_once_with(limit=1)


    @mock.patch('migration_app.auth.ytmusic_auth.YTMusic')
    @mock.patch('migration_app.auth.ytmusic_auth.os.path.exists')
    @mock.patch('migration_app.auth.ytmusic_auth.os.remove') # To check if corrupted file is removed
    def test_get_ytmusic_client_corrupted_auth_file(self, mock_os_remove, mock_os_exists, MockYTMusic):
        mock_os_exists.return_value = True # File exists
        MockYTMusic.side_effect = json.JSONDecodeError("Corrupted JSON", "doc", 0) # Simulate YTMusic init failing

        authenticator = YouTubeMusicAuthenticator()
        with self.assertRaisesRegex(YouTubeMusicAuthError, "Authentication file 'headers_auth.json' is corrupted"):
            authenticator.get_ytmusic_client()

        MockYTMusic.assert_called_once_with(YT_AUTH_HEADERS_PATH)
        mock_os_remove.assert_called_once_with(YT_AUTH_HEADERS_PATH) # Verify removal of bad file

    @mock.patch('migration_app.auth.ytmusic_auth.os.path.exists')
    def test_is_authenticated(self, mock_os_exists):
        authenticator = YouTubeMusicAuthenticator()

        mock_os_exists.return_value = True
        self.assertTrue(authenticator.is_authenticated())

        mock_os_exists.return_value = False
        self.assertFalse(authenticator.is_authenticated())

# Ensure the if __name__ == '__main__': unittest.main() is at the end of the file
# If it's not already there from the previous subtask, it should be added.
# Example:
# if __name__ == '__main__':
#     unittest.main()

if __name__ == '__main__':
    unittest.main()
