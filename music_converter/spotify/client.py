import requests # For making HTTP requests
from typing import List, Dict, Any, Optional

# Use relative import for models within the same package
try:
    from ..common_models.models import Playlist, Track
except ImportError:
    # Fallback for direct execution or if package structure is not recognized
    # This helps in testing/running this file standalone, though ideally it's part of the package
    print("Warning: Could not import models using relative import. Attempting direct import for common_models.")
    try:
        from common_models.models import Playlist, Track # If music_converter is in PYTHONPATH
    except ImportError:
        print("Critical Warning: Could not import Playlist and Track. Using placeholder classes.")
        # Define placeholder classes if all imports fail, to allow basic script execution
        class Track:
            def __init__(self, title: str, artist: str, album: str, duration_ms: int, spotify_id: Optional[str] = None, youtube_id: Optional[str] = None):
                self.title = title
                self.artist = artist
                self.album = album
                self.duration_ms = duration_ms
                self.spotify_id = spotify_id
                self.youtube_id = youtube_id
            def __repr__(self): return f"Track({self.title})"

        class Playlist:
            def __init__(self, name: str, tracks: List[Track], description: Optional[str] = "", spotify_id: Optional[str] = None, youtube_id: Optional[str] = None, total_tracks_from_api: Optional[int] = None):
                self.name = name
                self.tracks = tracks
                self.description = description
                self.spotify_id = spotify_id
                self.youtube_id = youtube_id
                self.total_tracks_from_api = total_tracks_from_api
            def __repr__(self): return f"Playlist({self.name})"


class SpotifyClient:
    BASE_API_URL = "https://api.spotify.com/v1"

    def __init__(self, api_token: str):
        """
        Initializes the Spotify client.
        api_token: A valid Spotify API access token.
        """
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        # print(f"SpotifyClient initialized with token.") # Avoid printing token info

    def _parse_track_from_spotify_item(self, item: Dict[str, Any]) -> Optional[Track]:
        """Helper to parse a track item from Spotify API response."""
        if not item or 'track' not in item or not item['track']: # Handles cases like local files or missing track data
            return None

        track_data = item['track']
        if not track_data.get('id') or not track_data.get('name'): # Essential data missing
             return None

        # Artists can be a list, concatenate their names
        artist_names = ", ".join([artist['name'] for artist in track_data.get('artists', [])])
        album_name = track_data.get('album', {}).get('name', "Unknown Album")

        return Track(
            title=track_data['name'],
            artist=artist_names,
            album=album_name,
            duration_ms=track_data.get('duration_ms', 0),
            spotify_id=track_data['id']
        )

    def get_user_playlists(self, limit: int = 20) -> List[Playlist]:
        """
        Fetches the current user's playlists from Spotify.
        limit: The maximum number of playlists to retrieve.
        Returns a list of Playlist objects or an empty list if an error occurs.
        """
        print(f"SpotifyClient: get_user_playlists called (limit: {limit})")
        playlists_url = f"{self.BASE_API_URL}/me/playlists"
        params = {"limit": limit}

        try:
            response = requests.get(playlists_url, headers=self.headers, params=params)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)

            data = response.json()
            user_playlists = []
            for item in data.get("items", []):
                # The /me/playlists endpoint provides playlist metadata.
                # Tracks within the playlist are usually just a link (href) and total count.
                # For now, we'll create Playlist objects without full track details.
                # A separate call to get_playlist_tracks would be needed for full track lists.
                playlist_tracks_data = item.get('tracks', {})
                # Let's create placeholder tracks if we want to represent them, or an empty list
                # For simplicity, we'll use an empty list of tracks for now from this endpoint

                playlist_tracks_data = item.get('tracks', {}) # Ensure this line is present or adjust if it was removed
                playlist = Playlist(
                    name=item.get("name", "Unnamed Playlist"),
                    tracks=[],
                    description=item.get("description", ""),
                    spotify_id=item.get("id"),
                    total_tracks_from_api=playlist_tracks_data.get('total') # Populate the new field
                )
                # We can store the href to fetch tracks later if needed
                # playlist.tracks_href = playlist_tracks_data.get('href')
                # playlist.total_tracks = playlist_tracks_data.get('total')
                user_playlists.append(playlist)

            print(f"Successfully fetched {len(user_playlists)} playlists.")
            return user_playlists

        except requests.exceptions.RequestException as e:
            print(f"Error fetching user playlists: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    print(f"API Error Response: {e.response.json()}")
                except ValueError: # If response is not JSON
                    print(f"API Error Response (Non-JSON): {e.response.text}")
            return []
        except ValueError: # JSONDecodeError
            print("Error decoding JSON response from Spotify API.")
            return []


    def get_playlist_tracks(self, playlist_id: str, limit: int = 50) -> List[Track]:
        """
        Fetches tracks for a specific playlist from Spotify.
        playlist_id: The ID of the Spotify playlist.
        limit: The maximum number of tracks to retrieve.
        Returns a list of Track objects.
        """
        print(f"SpotifyClient: get_playlist_tracks called for playlist_id: {playlist_id} (limit: {limit})")
        tracks_url = f"{self.BASE_API_URL}/playlists/{playlist_id}/tracks"
        params = {"limit": limit, "fields": "items(track(id,name,artists(name),album(name),duration_ms))"} # Specify fields to get

        try:
            response = requests.get(tracks_url, headers=self.headers, params=params)
            response.raise_for_status()

            data = response.json()
            tracks_list = []
            for item in data.get("items", []):
                track = self._parse_track_from_spotify_item(item)
                if track:
                    tracks_list.append(track)

            print(f"Successfully fetched {len(tracks_list)} tracks for playlist {playlist_id}.")
            return tracks_list

        except requests.exceptions.RequestException as e:
            print(f"Error fetching tracks for playlist {playlist_id}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    print(f"API Error Response: {e.response.json()}")
                except ValueError:
                    print(f"API Error Response (Non-JSON): {e.response.text}")
            return []
        except ValueError:
            print(f"Error decoding JSON response for playlist {playlist_id} tracks.")
            return []

    def get_liked_songs(self, limit: int = 50) -> List[Track]:
        """
        Placeholder for fetching user's liked songs from Spotify.
        This now makes a real API call.
        limit: Max number of liked songs to retrieve.
        """
        print(f"SpotifyClient: get_liked_songs called (limit: {limit})")
        liked_songs_url = f"{self.BASE_API_URL}/me/tracks"
        params = {"limit": limit}

        try:
            response = requests.get(liked_songs_url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()

            liked_tracks = []
            for item in data.get("items", []): # Liked songs are wrapped in 'item' objects containing 'track'
                track = self._parse_track_from_spotify_item(item)
                if track:
                    liked_tracks.append(track)

            print(f"Successfully fetched {len(liked_tracks)} liked songs.")
            return liked_tracks

        except requests.exceptions.RequestException as e:
            print(f"Error fetching liked songs: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    print(f"API Error Response: {e.response.json()}")
                except ValueError:
                    print(f"API Error Response (Non-JSON): {e.response.text}")
            return []
        except ValueError:
            print("Error decoding JSON response for liked songs.")
            return []


if __name__ == '__main__':
    print("Running SpotifyClient example usage...")
    print("IMPORTANT: To test with real API calls, set a valid SPOTIFY_API_TOKEN environment variable.")
    print("Without it, this will likely fail with an authentication error from Spotify.")

    import os
    # IMPORTANT: Replace with your actual Spotify API Token for testing
    # It's best to get this from an environment variable or a secure config
    api_token = os.environ.get("SPOTIFY_API_TOKEN")

    if not api_token:
        print("\nSPOTIFY_API_TOKEN environment variable not set.")
        print("Cannot perform real API calls. Please set it to a valid Spotify OAuth Access Token.")
        print("Falling back to printing what WOULD be done.")

        # Simulate what would happen
        print("\n--- SIMULATED API CALLS (NO TOKEN) ---")
        # client = SpotifyClient(api_token="DUMMY_TOKEN_FOR_INITIALIZATION_ONLY") # Init with dummy
        print("\nSimulating: client.get_user_playlists()")
        print("--> Would fetch user playlists. Expect a list of Playlist objects.")
        print("    Each Playlist object would have 'name', 'spotify_id', 'description', and 'total_tracks_from_api'.")

        print("\nSimulating: client.get_playlist_tracks(playlist_id='some_playlist_id')")
        print("--> Would fetch tracks for a specific playlist. Expect a list of Track objects.")

        print("\nSimulating: client.get_liked_songs()")
        print("--> Would fetch liked songs. Expect a list of Track objects.")

    else:
        print(f"\n--- PERFORMING REAL API CALLS (Token: ...{api_token[-4:] if len(api_token) > 4 else 'Token too short'}) ---")
        client = SpotifyClient(api_token=api_token)

        print("\nFetching user playlists (limit 5)...")
        playlists = client.get_user_playlists(limit=5)
        if playlists:
            print(f"Fetched {len(playlists)} playlists:")
            for i, p in enumerate(playlists):
                print(f"  {i+1}. Name: {p.name} (ID: {p.spotify_id})")
                print(f"     Description: '{p.description}'")
                print(f"     Total tracks (from API): {p.total_tracks_from_api}")
                print(f"     Tracks in object (initially): {len(p.tracks)}") # Will be 0 initially

                # Example: Fetch tracks for the first playlist that has a reported total > 0
                if p.total_tracks_from_api is not None and p.total_tracks_from_api > 0: # Check if total_tracks_from_api is not None
                    print(f"    Fetching first 3 tracks for '{p.name}' (ID: {p.spotify_id})...")
                    tracks_in_playlist = client.get_playlist_tracks(p.spotify_id, limit=3)
                    if tracks_in_playlist:
                        p.tracks = tracks_in_playlist # Populate the tracks list in our object
                        print(f"    Found {len(p.tracks)} tracks in '{p.name}':")
                        for t_idx, t in enumerate(p.tracks):
                            print(f"      {t_idx + 1}. {t.title} by {t.artist} (Album: {t.album}, ID: {t.spotify_id})")
                    else:
                        print(f"    No tracks found (or error) for '{p.name}'.")
                    # Break after fetching for one playlist to keep example concise
                    print("    (Stopping track fetch example after first eligible playlist)")
                    break

            # If no playlist had tracks to fetch, indicate this
            if not any(p.tracks for p in playlists if p.total_tracks_from_api is not None and p.total_tracks_from_api > 0):
                 print("\n    No playlist tracks fetched in this example run (either no playlists with tracks or limit reached).")


        else:
            print("No playlists fetched or an error occurred.")

        print("\nFetching liked songs (limit 5)...")
        liked_songs = client.get_liked_songs(limit=5)
        if liked_songs:
            print(f"Fetched {len(liked_songs)} liked songs:")
            for t_idx, t in enumerate(liked_songs):
                print(f"  {t_idx + 1}. {t.title} by {t.artist} (Album: {t.album}, ID: {t.spotify_id})")
        else:
            print("No liked songs fetched or an error occurred.")

    print("\nExample usage finished.")
