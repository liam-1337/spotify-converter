import unittest
from unittest import mock
from migration_app.migration.spotify_client import SpotifyDataClient
import spotipy # Required for spotipy.Spotify type check and dummy objects

# Helper function to create mock track/album/artist items for responses
def create_mock_item(item_id, item_type="track"):
    if item_type == "track":
        return {"track": {"id": item_id, "name": f"Track {item_id}", "artists": [{"name": "Artist"}]}}
    if item_type == "album_item": # For saved albums
        return {"album": {"id": item_id, "name": f"Album {item_id}", "artists": [{"name": "Artist"}]}}
    if item_type == "album_track": # For tracks directly under album_tracks endpoint
         return {"id": item_id, "name": f"Track {item_id}", "artists": [{"name": "Artist"}]}
    if item_type == "artist":
        return {"id": item_id, "name": f"Artist {item_id}"}
    if item_type == "playlist":
        return {"id": item_id, "name": f"Playlist {item_id}", "tracks": {"total": 1}} # Simplified
    return {"id": item_id}


class TestSpotifyDataClient(unittest.TestCase):

    def setUp(self):
        self.mock_sp_client = mock.Mock(spec=spotipy.Spotify)
        self.data_client = SpotifyDataClient(self.mock_sp_client)

    def test_constructor_invalid_client(self):
        with self.assertRaises(ValueError):
            SpotifyDataClient("not a spotipy client")

    def test_get_current_user_playlists_pagination(self):
        # Simulate two pages of results
        page1_items = [create_mock_item(f"pl{i}", "playlist") for i in range(2)]
        page2_items = [create_mock_item(f"pl{i+2}", "playlist") for i in range(2)]
        self.mock_sp_client.current_user_playlists.side_effect = [
            {"items": page1_items, "next": "page2_url"},
            {"items": page2_items, "next": None}
        ]

        playlists = self.data_client.get_current_user_playlists(limit=2)

        self.assertEqual(len(playlists), 4)
        self.assertEqual(playlists[0]['name'], "Playlist pl0")
        self.assertEqual(playlists[3]['name'], "Playlist pl3")
        self.mock_sp_client.current_user_playlists.assert_any_call(limit=2, offset=0)
        self.mock_sp_client.current_user_playlists.assert_any_call(limit=2, offset=2)
        self.assertEqual(self.mock_sp_client.current_user_playlists.call_count, 2)

    def test_get_current_user_playlists_empty(self):
        self.mock_sp_client.current_user_playlists.return_value = {"items": [], "next": None}
        playlists = self.data_client.get_current_user_playlists()
        self.assertEqual(len(playlists), 0)

    def test_get_playlist_tracks_pagination_and_filter_none(self):
        page1_items = [create_mock_item("t1"), None, create_mock_item("t2")] # None item to be filtered
        page1_valid_tracks = [item['track'] for item in page1_items if item and item.get('track')]

        page2_items = [create_mock_item("t3")]
        page2_valid_tracks = [item['track'] for item in page2_items if item and item.get('track')]

        self.mock_sp_client.playlist_items.side_effect = [
            {"items": page1_items, "next": "page2_url"},
            {"items": page2_items, "next": None}
        ]

        tracks = self.data_client.get_playlist_tracks("playlist_id_1", limit=3) # limit for call

        self.assertEqual(len(tracks), 3) # t1, t2, t3
        self.assertEqual(tracks[0]['name'], "Track t1")
        self.assertEqual(tracks[2]['name'], "Track t3")
        self.mock_sp_client.playlist_items.assert_any_call("playlist_id_1", limit=3, offset=0)
        self.mock_sp_client.playlist_items.assert_any_call("playlist_id_1", limit=3, offset=3)

    def test_get_saved_tracks_pagination(self):
        page1_items = [create_mock_item(f"st{i}") for i in range(2)]
        page2_items = [create_mock_item(f"st{i+2}") for i in range(1)] # Last page
        self.mock_sp_client.current_user_saved_tracks.side_effect = [
            {"items": page1_items, "next": "page2_url"},
            {"items": page2_items, "next": None}
        ]

        tracks = self.data_client.get_saved_tracks(limit=2)
        self.assertEqual(len(tracks), 3)
        self.assertEqual(tracks[0]['name'], "Track st0")
        self.assertEqual(tracks[2]['name'], "Track st2")
        self.mock_sp_client.current_user_saved_tracks.assert_any_call(limit=2, offset=0)
        self.mock_sp_client.current_user_saved_tracks.assert_any_call(limit=2, offset=2)

    def test_get_saved_albums_pagination(self):
        page1_items = [create_mock_item(f"sa{i}", "album_item") for i in range(2)]
        page2_items = [create_mock_item(f"sa{i+2}", "album_item") for i in range(1)]
        self.mock_sp_client.current_user_saved_albums.side_effect = [
            {"items": page1_items, "next": "page2_url"},
            {"items": page2_items, "next": None}
        ]

        albums = self.data_client.get_saved_albums(limit=2)
        self.assertEqual(len(albums), 3)
        self.assertEqual(albums[0]['name'], "Album sa0")
        self.assertEqual(albums[2]['name'], "Album sa2")
        self.mock_sp_client.current_user_saved_albums.assert_any_call(limit=2, offset=0)
        self.mock_sp_client.current_user_saved_albums.assert_any_call(limit=2, offset=2)

    def test_get_album_tracks_pagination(self):
        # Note: sp.album_tracks returns simplified track objects directly in 'items'
        page1_items = [create_mock_item(f"at{i}", "album_track") for i in range(2)]
        page2_items = [create_mock_item(f"at{i+2}", "album_track") for i in range(1)]
        self.mock_sp_client.album_tracks.side_effect = [
            {"items": page1_items, "next": "page2_url"},
            {"items": page2_items, "next": None}
        ]

        tracks = self.data_client.get_album_tracks("album_id_1", limit=2)
        self.assertEqual(len(tracks), 3)
        self.assertEqual(tracks[0]['name'], "Track at0")
        self.assertEqual(tracks[2]['name'], "Track at2")
        self.mock_sp_client.album_tracks.assert_any_call("album_id_1", limit=2, offset=0)
        self.mock_sp_client.album_tracks.assert_any_call("album_id_1", limit=2, offset=2)

    def test_get_followed_artists_pagination(self):
        # Cursor-based pagination
        page1_artists = [create_mock_item(f"fa{i}", "artist") for i in range(2)]
        page2_artists = [create_mock_item(f"fa{i+2}", "artist") for i in range(1)]
        self.mock_sp_client.current_user_followed_artists.side_effect = [
            {"artists": {"items": page1_artists, "next": "page2_url", "cursors": {"after": "cursor1"}}},
            {"artists": {"items": page2_artists, "next": None, "cursors": {"after": None}}} # No next page
        ]

        artists = self.data_client.get_followed_artists(limit=2)
        self.assertEqual(len(artists), 3)
        self.assertEqual(artists[0]['name'], "Artist fa0")
        self.assertEqual(artists[2]['name'], "Artist fa2")
        self.mock_sp_client.current_user_followed_artists.assert_any_call(limit=2, after=None)
        self.mock_sp_client.current_user_followed_artists.assert_any_call(limit=2, after="cursor1")

    def test_get_artist_top_tracks(self):
        top_tracks_data = [create_mock_item(f"top{i}", "album_track") for i in range(3)] # Using album_track for simplicity
        self.mock_sp_client.artist_top_tracks.return_value = {"tracks": top_tracks_data}

        tracks = self.data_client.get_artist_top_tracks("artist_id_1", country="US")
        self.assertEqual(len(tracks), 3)
        self.assertEqual(tracks[0]['name'], "Track top0")
        self.mock_sp_client.artist_top_tracks.assert_called_once_with("artist_id_1", country="US")

    def test_get_artist_top_tracks_empty(self):
        self.mock_sp_client.artist_top_tracks.return_value = {"tracks": []}
        tracks = self.data_client.get_artist_top_tracks("artist_id_1")
        self.assertEqual(len(tracks), 0)

    def test_get_artist_albums_pagination(self):
        page1_albums = [create_mock_item(f"ar_al{i}", "album_item") for i in range(2)] # Using album_item for simplicity
        page2_albums = [create_mock_item(f"ar_al{i+2}", "album_item") for i in range(1)]
        self.mock_sp_client.artist_albums.side_effect = [
            {"items": page1_albums, "next": "page2_url"},
            {"items": page2_albums, "next": None}
        ]

        albums = self.data_client.get_artist_albums("artist_id_1", album_type="album", limit=2)
        self.assertEqual(len(albums), 3)
        self.assertEqual(albums[0]['name'], "Album ar_al0")
        self.assertEqual(albums[2]['name'], "Album ar_al2")
        self.mock_sp_client.artist_albums.assert_any_call("artist_id_1", album_type="album", limit=2, offset=0)
        self.mock_sp_client.artist_albums.assert_any_call("artist_id_1", album_type="album", limit=2, offset=2)

if __name__ == '__main__':
    unittest.main()
