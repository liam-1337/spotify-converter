import unittest
from unittest import mock
from click.testing import CliRunner
import click # For click.Abort

# CLI module to test
from migration_app.ui import cli as main_cli # renamed to avoid conflict with cli object in main_cli
from migration_app.auth.spotify_auth import SpotifyAuthError
from migration_app.auth.ytmusic_auth import YouTubeMusicAuthError

# Dummy data structures for mocking
def mock_spotify_user():
    user_mock = mock.Mock()
    user_mock.current_user.return_value = {'display_name': 'Test User', 'id': 'testid'}
    return user_mock

def mock_ytmusic_client_basic():
    yt_mock = mock.Mock()
    yt_mock.get_library_playlists.return_value = [{'title': 'YT Test PL1'}]
    return yt_mock

MOCK_SPOTIFY_PLAYLISTS = [
    {'name': 'Playlist A', 'id': 'plA', 'tracks': {'total': 10}},
    {'name': 'Awesome Mix Vol. 1', 'id': 'plB', 'tracks': {'total': 5}},
    {'name': 'Chill Vibes', 'id': 'plC', 'tracks': {'total': 20}},
]
MOCK_PLAYLIST_TRACKS = [
    {'name': 'Track 1', 'id': 't1', 'artists': [{'name': 'Artist X'}]},
    {'name': 'Song B', 'id': 't2', 'artists': [{'name': 'Artist Y'}]},
]
MOCK_LIKED_SONGS = [
    {'name': 'Liked Song Alpha', 'id': 'lsA', 'artists': [{'name': 'Artist Liked'}]},
    {'name': 'Favorite Tune Beta', 'id': 'lsB', 'artists': [{'name': 'Another Artist'}]},
]


class TestCliCommands(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    @mock.patch('migration_app.ui.cli.get_authenticated_spotify_client')
    def test_auth_spotify_success(self, mock_get_sp_client):
        mock_get_sp_client.return_value = mock_spotify_user()
        result = self.runner.invoke(main_cli.cli, ['auth-spotify'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Successfully authenticated with Spotify as: Test User (testid)", result.output)

    @mock.patch('migration_app.ui.cli.get_authenticated_spotify_client')
    def test_auth_spotify_failure(self, mock_get_sp_client):
        mock_get_sp_client.side_effect = click.Abort() # Simulate auth failure in helper
        result = self.runner.invoke(main_cli.cli, ['auth-spotify'])
        self.assertNotEqual(result.exit_code, 0) # click.Abort causes non-zero exit
        # The error message is printed by get_authenticated_spotify_client,
        # which is already tested in test_auth.py indirectly.
        # Here we just check that the command aborts.

    @mock.patch('migration_app.ui.cli.YouTubeMusicAuthenticator')
    def test_auth_ytmusic_success(self, MockYTAuthenticator):
        mock_auth_instance = MockYTAuthenticator.return_value
        mock_auth_instance.get_ytmusic_client.return_value = mock_ytmusic_client_basic()

        result = self.runner.invoke(main_cli.cli, ['auth-ytmusic'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Successfully authenticated with YouTube Music.", result.output)
        self.assertIn("YT Test PL1", result.output) # From the mock client's get_library_playlists

    @mock.patch('migration_app.ui.cli.YouTubeMusicAuthenticator')
    def test_auth_ytmusic_failure(self, MockYTAuthenticator):
        mock_auth_instance = MockYTAuthenticator.return_value
        mock_auth_instance.get_ytmusic_client.side_effect = YouTubeMusicAuthError("YT Auth Failed")

        result = self.runner.invoke(main_cli.cli, ['auth-ytmusic'])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("YouTube Music authentication failed: YT Auth Failed", result.output)

    # --- Tests for Spotify Data Commands ---

    @mock.patch('migration_app.ui.cli.get_authenticated_spotify_client')
    @mock.patch('migration_app.ui.cli.SpotifyDataClient')
    def test_list_spotify_playlists_success(self, MockSpotifyDataClient, mock_get_sp_client):
        mock_get_sp_client.return_value = mock_spotify_user() # Auth success
        mock_data_client_instance = MockSpotifyDataClient.return_value
        mock_data_client_instance.get_current_user_playlists.return_value = MOCK_SPOTIFY_PLAYLISTS

        result = self.runner.invoke(main_cli.cli, ['list-spotify-playlists'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Playlist A (ID: plA, Tracks: 10)", result.output)
        self.assertIn("Awesome Mix Vol. 1 (ID: plB, Tracks: 5)", result.output)

    @mock.patch('migration_app.ui.cli.get_authenticated_spotify_client')
    @mock.patch('migration_app.ui.cli.SpotifyDataClient')
    def test_list_spotify_playlists_empty(self, MockSpotifyDataClient, mock_get_sp_client):
        mock_get_sp_client.return_value = mock_spotify_user()
        mock_data_client_instance = MockSpotifyDataClient.return_value
        mock_data_client_instance.get_current_user_playlists.return_value = []

        result = self.runner.invoke(main_cli.cli, ['list-spotify-playlists'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No playlists found.", result.output)

    @mock.patch('migration_app.ui.cli.get_authenticated_spotify_client')
    @mock.patch('migration_app.ui.cli.SpotifyDataClient')
    def test_list_spotify_playlists_limit(self, MockSpotifyDataClient, mock_get_sp_client):
        mock_get_sp_client.return_value = mock_spotify_user()
        mock_data_client_instance = MockSpotifyDataClient.return_value
        mock_data_client_instance.get_current_user_playlists.return_value = MOCK_SPOTIFY_PLAYLISTS

        result = self.runner.invoke(main_cli.cli, ['list-spotify-playlists', '--limit', '1'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Playlist A", result.output)
        self.assertNotIn("Awesome Mix Vol. 1", result.output)
        self.assertIn("... and 2 more.", result.output)


    @mock.patch('migration_app.ui.cli.get_authenticated_spotify_client')
    def test_list_spotify_playlists_auth_fail(self, mock_get_sp_client):
        mock_get_sp_client.side_effect = click.Abort()
        result = self.runner.invoke(main_cli.cli, ['list-spotify-playlists'])
        self.assertNotEqual(result.exit_code, 0)


    @mock.patch('migration_app.ui.cli.get_authenticated_spotify_client')
    @mock.patch('migration_app.ui.cli.SpotifyDataClient')
    def test_show_spotify_playlist_tracks_success(self, MockSpotifyDataClient, mock_get_sp_client):
        mock_get_sp_client.return_value = mock_spotify_user()
        mock_data_client_instance = MockSpotifyDataClient.return_value
        mock_data_client_instance.get_playlist_tracks.return_value = MOCK_PLAYLIST_TRACKS

        result = self.runner.invoke(main_cli.cli, ['show-spotify-playlist-tracks', 'plA'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Track 1 by Artist X (ID: t1)", result.output)
        self.assertIn("Song B by Artist Y (ID: t2)", result.output)
        mock_data_client_instance.get_playlist_tracks.assert_called_once_with('plA')

    @mock.patch('migration_app.ui.cli.get_authenticated_spotify_client')
    @mock.patch('migration_app.ui.cli.SpotifyDataClient')
    def test_show_spotify_playlist_tracks_limit(self, MockSpotifyDataClient, mock_get_sp_client):
        mock_get_sp_client.return_value = mock_spotify_user()
        mock_data_client_instance = MockSpotifyDataClient.return_value
        # Simulate more tracks than limit
        many_tracks = MOCK_PLAYLIST_TRACKS + [{'name': 'Track 3', 'id': 't3', 'artists': [{'name': 'Artist Z'}]}]
        mock_data_client_instance.get_playlist_tracks.return_value = many_tracks

        result = self.runner.invoke(main_cli.cli, ['show-spotify-playlist-tracks', 'plA', '--limit', '1'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Track 1", result.output)
        self.assertNotIn("Song B", result.output)
        self.assertIn("... and 2 more tracks.", result.output)


    @mock.patch('migration_app.ui.cli.get_authenticated_spotify_client')
    @mock.patch('migration_app.ui.cli.SpotifyDataClient')
    def test_list_spotify_liked_songs_success(self, MockSpotifyDataClient, mock_get_sp_client):
        mock_get_sp_client.return_value = mock_spotify_user()
        mock_data_client_instance = MockSpotifyDataClient.return_value
        mock_data_client_instance.get_saved_tracks.return_value = MOCK_LIKED_SONGS

        result = self.runner.invoke(main_cli.cli, ['list-spotify-liked-songs'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Liked Song Alpha by Artist Liked (ID: lsA)", result.output)

    @mock.patch('migration_app.ui.cli.get_authenticated_spotify_client')
    @mock.patch('migration_app.ui.cli.SpotifyDataClient')
    def test_list_spotify_liked_songs_limit(self, MockSpotifyDataClient, mock_get_sp_client):
        mock_get_sp_client.return_value = mock_spotify_user()
        mock_data_client_instance = MockSpotifyDataClient.return_value
        many_liked = MOCK_LIKED_SONGS + [{'name': 'Liked 3', 'id': 'lsC', 'artists': [{'name': 'Artist C'}]}]
        mock_data_client_instance.get_saved_tracks.return_value = many_liked

        result = self.runner.invoke(main_cli.cli, ['list-spotify-liked-songs', '--limit', '1'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Liked Song Alpha", result.output)
        self.assertNotIn("Favorite Tune Beta", result.output)
        self.assertIn("... and 2 more liked songs.", result.output)

if __name__ == '__main__':
    unittest.main()
