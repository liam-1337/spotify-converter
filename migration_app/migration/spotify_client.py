import spotipy

class SpotifyDataClient:
    def __init__(self, sp_client: spotipy.Spotify):
        if not isinstance(sp_client, spotipy.Spotify):
            raise ValueError("A valid spotipy.Spotify client instance is required.")
        self.sp = sp_client

    def get_current_user_playlists(self, limit: int = 50) -> list[dict]:
        """
        Retrieves all playlists for the current authenticated user.
        Handles pagination.
        """
        playlists = []
        offset = 0
        while True:
            results = self.sp.current_user_playlists(limit=limit, offset=offset)
            if not results or not results['items']:
                break
            playlists.extend(results['items'])
            if results['next']:
                offset += limit
            else:
                break
        return playlists

    def get_playlist_tracks(self, playlist_id: str, limit: int = 100) -> list[dict]:
        """
        Retrieves all tracks for a given playlist ID.
        Handles pagination.
        Each track item in the list will be the 'track' object from the playlist item, if available.
        """
        tracks = []
        offset = 0
        while True:
            results = self.sp.playlist_items(playlist_id, limit=limit, offset=offset)
            if not results or not results['items']:
                break

            # Filter out None tracks which can happen for various reasons (e.g., deleted, unavailable)
            # Also, ensure 'track' key exists and is not None
            valid_tracks = [item['track'] for item in results['items'] if item and item.get('track')]
            tracks.extend(valid_tracks)

            if results['next']:
                offset += limit
            else:
                break
        return tracks

    def get_saved_tracks(self, limit: int = 50) -> list[dict]:
        """
        Retrieves all liked/saved tracks for the current authenticated user.
        Handles pagination.
        Each track item in the list will be the 'track' object from the saved track item.
        """
        saved_tracks = []
        offset = 0
        while True:
            results = self.sp.current_user_saved_tracks(limit=limit, offset=offset)
            if not results or not results['items']:
                break

            # Filter out None tracks and ensure 'track' key exists
            valid_tracks = [item['track'] for item in results['items'] if item and item.get('track')]
            saved_tracks.extend(valid_tracks)

            if results['next']:
                offset += limit
            else:
                break
        return saved_tracks

    def get_saved_albums(self, limit: int = 50) -> list[dict]:
        """
        Retrieves all saved albums for the current authenticated user.
        Handles pagination.
        Each album item in the list will be the 'album' object from the saved album item.
        """
        saved_albums_data = []
        offset = 0
        while True:
            results = self.sp.current_user_saved_albums(limit=limit, offset=offset)
            if not results or not results['items']:
                break

            valid_albums = [item['album'] for item in results['items'] if item and item.get('album')]
            saved_albums_data.extend(valid_albums)

            if results['next']:
                offset += limit
            else:
                break
        return saved_albums_data

    def get_album_tracks(self, album_id: str, limit: int = 50) -> list[dict]:
        """
        Retrieves all tracks for a given album ID.
        Handles pagination.
        Note: Album tracks from this endpoint are simplified track objects (don't have 'album' context within them).
        """
        album_tracks = []
        offset = 0
        while True:
            results = self.sp.album_tracks(album_id, limit=limit, offset=offset)
            if not results or not results['items']:
                break

            # Ensure track objects are valid before adding
            valid_tracks = [track for track in results['items'] if track]
            album_tracks.extend(valid_tracks)

            if results['next']:
                offset += limit
            else:
                break
        return album_tracks

    def get_followed_artists(self, limit: int = 50) -> list[dict]:
        """
        Retrieves all artists followed by the current authenticated user.
        Handles pagination using the 'after' cursor.
        """
        followed_artists = []
        after_cursor = None
        while True:
            results = self.sp.current_user_followed_artists(limit=limit, after=after_cursor)
            if not results or not results['artists'] or not results['artists']['items']:
                break

            valid_artists = [artist for artist in results['artists']['items'] if artist]
            followed_artists.extend(valid_artists)

            if results['artists']['next']:
                after_cursor = results['artists']['cursors']['after']
            else:
                break
            # Safety break if after_cursor is somehow not updated
            if not after_cursor and results['artists']['next']:
                break

        return followed_artists

    def get_artist_top_tracks(self, artist_id: str, country: str = 'US') -> list[dict]:
        """
        Retrieves the top tracks for a given artist ID in a specific country.
        """
        results = self.sp.artist_top_tracks(artist_id, country=country)
        return [track for track in results.get('tracks', []) if track] if results else []

    def get_artist_albums(self, artist_id: str, album_type: str = 'album,single', limit: int = 50) -> list[dict]:
        """
        Retrieves albums for a given artist ID.
        Handles pagination.
        album_type can be 'album', 'single', 'appears_on', 'compilation'.
        """
        artist_albums = []
        offset = 0
        while True:
            results = self.sp.artist_albums(artist_id, album_type=album_type, limit=limit, offset=offset)
            if not results or not results['items']:
                break

            valid_albums = [album for album in results['items'] if album]
            artist_albums.extend(valid_albums)

            if results['next']:
                offset += limit
            else:
                break
        return artist_albums

# Example Usage (for testing - would be integrated into CLI later)
if __name__ == '__main__':
    # This part requires you to have authenticated via spotify_auth.py or have a cached token
    # and set up your SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI env vars.
    from migration_app.auth.spotify_auth import SpotifyAuthenticator, SpotifyAuthError
    import os

    SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
    SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
    SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')

    if not all([SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI]):
        print("Please set SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, and SPOTIPY_REDIRECT_URI environment variables to test.")
    else:
        try:
            print("Authenticating with Spotify...")
            spotify_auth = SpotifyAuthenticator(
                client_id=SPOTIPY_CLIENT_ID,
                client_secret=SPOTIPY_CLIENT_SECRET,
                redirect_uri=SPOTIPY_REDIRECT_URI
            )
            sp_instance = spotify_auth.get_spotify_client()
            print("Authenticated successfully.")

            data_client = SpotifyDataClient(sp_instance)

            print("\nFetching user playlists...")
            playlists = data_client.get_current_user_playlists(limit=5) # Small limit for testing
            if playlists:
                print(f"Found {len(playlists)} playlists (showing details for the first few):")
                for pl in playlists[:3]: # Show first 3
                    print(f"- Playlist: {pl['name']} (ID: {pl['id']}, Tracks: {pl['tracks']['total']})")
                    if pl['tracks']['total'] > 0:
                        tracks = data_client.get_playlist_tracks(pl['id'], limit=3) # Small limit
                        for i, track in enumerate(tracks[:3]):
                             print(f"  - Track {i+1}: {track['name']} by {', '.join(art['name'] for art in track['artists'])}")
            else:
                print("No playlists found for the user.")

            print("\nFetching user liked songs (first 5)...")
            liked_songs = data_client.get_saved_tracks(limit=5)
            if liked_songs:
                print(f"Found {len(liked_songs)} liked songs (showing first 5):")
                for i, track_item in enumerate(liked_songs):
                    print(f"- Liked Song {i+1}: {track_item['name']} by {', '.join(art['name'] for art in track_item['artists'])}")
            else:
                print("No liked songs found.")

            print("\nFetching user saved albums (first 2)...")
            saved_albums = data_client.get_saved_albums(limit=2)
            if saved_albums:
                print(f"Found {len(saved_albums)} saved albums (showing first 2):")
                for i, album_item in enumerate(saved_albums):
                    print(f"- Saved Album {i+1}: {album_item['name']} by {', '.join(art['name'] for art in album_item['artists'])}")
                    album_tracks = data_client.get_album_tracks(album_item['id'], limit=3)
                    for j, track in enumerate(album_tracks):
                        print(f"  - Album Track {j+1}: {track['name']}")
            else:
                print("No saved albums found.")

            print("\nFetching followed artists (first 2)...")
            followed_artists = data_client.get_followed_artists(limit=2)
            if followed_artists:
                print(f"Found {len(followed_artists)} followed artists (showing first 2):")
                for i, artist in enumerate(followed_artists):
                    print(f"- Followed Artist {i+1}: {artist['name']}")
                    top_tracks = data_client.get_artist_top_tracks(artist['id'], country='US')
                    if top_tracks:
                        print(f"  Top track: {top_tracks[0]['name']}")
                    artist_albums = data_client.get_artist_albums(artist['id'], limit=1, album_type='album')
                    if artist_albums:
                        print(f"  Recent album: {artist_albums[0]['name']}")
            else:
                print("No followed artists found.")

        except SpotifyAuthError as e:
            print(f"Spotify authentication error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
