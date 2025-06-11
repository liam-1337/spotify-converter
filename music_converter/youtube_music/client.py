import time
import random
from typing import List, Optional
import os # For checking file path
import sys # For sys.exit

try:
    from ytmusicapi import YTMusic
except ImportError:
    print("Critical Error: YTMusicAPI library not found. Please install it: pip install ytmusicapi")
    # Define a dummy YTMusic class if import fails, so the script can be parsed.
    class YTMusic:
        def __init__(self, auth_headers_file_path: Optional[str] = None):
            if auth_headers_file_path:
                 print(f"Dummy YTMusic initialized with auth: {auth_headers_file_path}")
            else:
                 print("Dummy YTMusic initialized without auth.")
            print("Warning: Real YTMusicAPI not found, using dummy class. No real API calls will be made.")
        def search(self, query, filter=None, limit=None, ignore_spelling=False):
            print(f"Dummy YTMusic.search called with query: {query}")
            return [] # Return empty list to mimic no results

# Use relative import for models within the same package
try:
    from ..common_models.models import Track
except ImportError:
    # Fallback for direct execution
    print("Warning: YTMClient: Could not import Track using relative import. Attempting direct common_models.")
    try:
        from common_models.models import Track
    except ImportError:
        print("Critical Warning: YTMClient: Could not import Track. Using placeholder class.")
        class Track:
            def __init__(self, title: str, artist: str, album: Optional[str] = None, duration_ms: Optional[int] = 0, spotify_id: Optional[str] = None, youtube_id: Optional[str] = None):
                self.title = title
                self.artist = artist
                self.album = album
                self.duration_ms = duration_ms
                self.spotify_id = spotify_id
                self.youtube_id = youtube_id
            def __repr__(self):
                return f"Track(title='{self.title}', artist='{self.artist}')"

class YouTubeMusicClient:
    def __init__(self, auth_headers_file_path: Optional[str] = None):
        """
        Initializes the YouTube Music client using YTMusicAPI.

        Args:
            auth_headers_file_path (Optional[str]):
                Path to the JSON file containing authentication headers.
                If not provided, YTMusicAPI will be initialized without authentication,
                limiting access to public data and some functionalities.
                To generate this file (usually 'headers_auth.json'):
                1. Install ytmusicapi: `pip install ytmusicapi`
                2. Run `ytmusicapi setup` in your terminal and follow the instructions.
                   This typically involves copying network request headers from an
                   authenticated YouTube Music session in your browser.
                See https://ytmusicapi.readthedocs.io/en/latest/setup/index.html for details.
        """
        self.ytmusic_api_auth_path = auth_headers_file_path
        try:
            if auth_headers_file_path and os.path.exists(auth_headers_file_path):
                print(f"YTMClient: Initializing YTMusicAPI with authentication file: {auth_headers_file_path}")
                self.ytmusic = YTMusic(auth_headers_file_path)
            elif auth_headers_file_path and not os.path.exists(auth_headers_file_path):
                print(f"YTMClient Warning: Authentication file not found at {auth_headers_file_path}. Initializing YTMusicAPI without authentication.")
                self.ytmusic = YTMusic() # Initialize without auth if file path provided but not found
            else:
                print("YTMClient: Initializing YTMusicAPI without authentication (public access only).")
                self.ytmusic = YTMusic() # Initialize without authentication
            print("YTMClient: YTMusicAPI initialized successfully.")

        except Exception as e:
            print(f"YTMClient Critical Error: Failed to initialize YTMusicAPI: {e}")
            print("Ensure 'ytmusicapi' is installed correctly. If using auth, ensure headers file is valid.")
            # Fallback to a dummy YTMusic object to prevent crashes, though functionality will be lost.
            class DummyYTMusic:
                def __init__(self, *args, **kwargs): pass
                def search(self, *args, **kwargs): return []
                def get_playlist(self, *args, **kwargs): return {} # Add other methods as needed for stubs
                def create_playlist(self, *args, **kwargs): return None
                def add_playlist_items(self, *args, **kwargs): return {}
            self.ytmusic = DummyYTMusic()
            print("YTMClient: Using a dummy YTMusic object due to initialization failure.")

    def find_track_match(self, track_info: Track) -> Optional[str]:
        """
        Finds a matching track on YouTube Music using YTMusicAPI's search.

        Args:
            track_info (Track): A Track object containing title and artist information.

        Returns:
            Optional[str]: The YouTube Music videoId if a match is found, otherwise None.
        """
        if not hasattr(self, 'ytmusic') or not self.ytmusic:
            print("YTMClient Error: YTMusicAPI not initialized. Cannot search for tracks.")
            return None

        query = f"{track_info.title} {track_info.artist}"
        print(f"  YTMClient: Searching YouTube Music for: '{query}'")

        try:
            # YTMusic.search returns a list of dictionaries.
            # We're interested in songs, so filter='songs' is appropriate.
            # Limit to a few results to find the best match.
            search_results = self.ytmusic.search(query=query, filter='songs', limit=5)

            if not search_results:
                print(f"    YTMClient: No results found on YouTube Music for '{query}'.")
                return None

            best_match = None
            for item in search_results:
                if item.get('resultType') == 'song' and item.get('videoId'):
                    yt_artists = [a.get('name', '').lower() for a in item.get('artists', [])]
                    query_artist_lower = track_info.artist.lower()
                    artist_match_found = False
                    for yt_artist_name_lower in yt_artists:
                        if yt_artist_name_lower in query_artist_lower or query_artist_lower in yt_artist_name_lower:
                            artist_match_found = True
                            break
                    if artist_match_found:
                        best_match = item
                        break
                if not best_match and item.get('resultType') == 'song' and item.get('videoId'):
                    best_match = item

            if best_match and best_match.get('videoId'):
                video_id = best_match['videoId']
                match_title = best_match.get('title', 'Unknown Title')
                match_artist_names = ", ".join([a.get('name', '') for a in best_match.get('artists', [])])
                print(f"    YTMClient: Match found: '{match_title}' by {match_artist_names} (ID: {video_id})")
                return video_id
            else:
                detailed_results_summary = []
                for i, item in enumerate(search_results[:3]):
                    res_title = item.get('title', 'N/A')
                    res_artists_list = [a.get('name', '') for a in item.get('artists', [])]
                    res_artists = ", ".join(res_artists_list) if res_artists_list else "N/A"
                    res_id = item.get('videoId', 'N/A')
                    detailed_results_summary.append(f"  Res {i+1}: {res_title} by {res_artists} (ID: {res_id})")
                if detailed_results_summary:
                    print(f"    YTMClient: No suitable match confirmed in top results for '{query}'. Top results were:")
                    for summary_line in detailed_results_summary:
                        print(summary_line)
                else:
                    print(f"    YTMClient: No suitable items with videoId found in search results for '{query}'.")
                return None
        except Exception as e:
            print(f"  YTMClient Error: Exception during YouTube Music search for '{query}': {e}")
            return None

    def create_playlist(self, name: str, description: str = "", public: bool = True) -> Optional[str]:
        """
        Creates a new playlist on YouTube Music using YTMusicAPI.
        Requires authentication.
        """
        if not hasattr(self, 'ytmusic') or not self.ytmusic:
            print("YTMClient Error: YTMusicAPI not initialized. Cannot create playlist.")
            return None
        privacy_status = "PUBLIC" if public else "PRIVATE"
        print(f"  YTMClient: Attempting to create playlist on YouTube Music: '{name}' (Privacy: {privacy_status})")
        try:
            playlist_id = self.ytmusic.create_playlist(
                title=name,
                description=description,
                privacy_status=privacy_status
            )
            if playlist_id:
                print(f"    YTMClient: Successfully created playlist '{name}' with ID: {playlist_id}")
                return playlist_id
            else:
                print(f"    YTMClient: Playlist creation for '{name}' did not return a valid ID, though no exception was raised.")
                return None
        except Exception as e:
            print(f"  YTMClient Error: Failed to create playlist '{name}' on YouTube Music: {e}")
            print("    This operation usually requires authentication with YTMusicAPI.")
            print("    Please ensure you have run `ytmusicapi setup` and provided the correct auth_headers_file_path.")
            return None

    def add_tracks_to_playlist(self, youtube_playlist_id: str, youtube_track_ids: List[str]) -> bool:
        """
        Adds tracks to a specified playlist on YouTube Music using YTMusicAPI.
        Requires authentication.
        """
        if not hasattr(self, 'ytmusic') or not self.ytmusic:
            print("YTMClient Error: YTMusicAPI not initialized. Cannot add tracks to playlist.")
            return False
        if not youtube_track_ids:
            print("  YTMClient: No track IDs provided to add to playlist. Skipping.")
            return False
        print(f"  YTMClient: Attempting to add {len(youtube_track_ids)} tracks to YouTube Music playlist ID: {youtube_playlist_id}")
        try:
            response = self.ytmusic.add_playlist_items(
                playlistId=youtube_playlist_id,
                videoIds=youtube_track_ids,
                duplicates=False
            )
            if response and ('status' in response and ('SUCCESS' in response['status'].upper())):
                print(f"    YTMClient: Successfully added/processed tracks for playlist {youtube_playlist_id}.")
                if 'actions' in response and response['actions']:
                    added_count = 0
                    for action in response['actions']:
                        if action.get('action') == 'ACTION_ADDED_VIDEO':
                            added_count +=1
                    if added_count > 0:
                         print(f"      Successfully added {added_count} new tracks.")
                    else:
                         print(f"      No new tracks were added (they might have already been in the playlist).")
                return True
            elif response and 'status' in response:
                 print(f"    YTMClient: Call to add_playlist_items for {youtube_playlist_id} returned status: {response['status']}. Tracks may not have been added.")
                 return False
            else:
                print(f"    YTMClient: Adding tracks to playlist {youtube_playlist_id} resulted in an unexpected response from API.")
                return False
        except Exception as e:
            print(f"  YTMClient Error: Failed to add tracks to playlist {youtube_playlist_id} on YouTube Music: {e}")
            print("    This operation usually requires authentication with YTMusicAPI and a valid playlist ID.")
            return False

if __name__ == '__main__':
    print("------------------------------------------------------------------")
    print("YouTubeMusicClient with YTMusicAPI - Full Example Usage")
    print("------------------------------------------------------------------")
    print("This example demonstrates: initializing the client, finding tracks,")
    print("creating a playlist, and adding tracks to it.")
    print("IMPORTANT: For creating playlists and adding items, VALID AUTHENTICATION")
    print("           (e.g., via 'headers_auth.json') IS ALMOST ALWAYS REQUIRED.")
    print("           You can set up 'ytmusicapi' by running: `ytmusicapi setup`.")
    print("------------------------------------------------------------------")

    auth_file = "headers_auth.json"
    local_auth_file_path_scriptdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), auth_file)
    local_auth_file_path_cwd = os.path.join(os.getcwd(), auth_file)

    auth_file_to_use = None
    if os.path.exists(local_auth_file_path_scriptdir):
        auth_file_to_use = local_auth_file_path_scriptdir
        print(f"Found auth file in script directory: '{auth_file_to_use}'")
    elif os.path.exists(local_auth_file_path_cwd):
        auth_file_to_use = local_auth_file_path_cwd
        print(f"Found auth file in current working directory: '{auth_file_to_use}'")
    else:
        print(f"No auth file ('{auth_file}') found in script or current directory.")
        print("Proceeding without authentication. Playlist creation/modification will likely fail.")

    print("\nInitializing YouTubeMusicClient...")
    if auth_file_to_use:
        print(f"Attempting to use auth file: {auth_file_to_use}")
    client = YouTubeMusicClient(auth_headers_file_path=auth_file_to_use)

    if not hasattr(client, 'ytmusic') or isinstance(client.ytmusic, type(None)) or not callable(getattr(client.ytmusic, 'search', None)):
        print("  YTMusicAPI instance not properly initialized in client. Aborting further tests.")
        sys.exit(1) # Use sys.exit if you import sys

    # --- Test find_track_match ---
    sample_tracks_to_find = [
        Track(title="Bohemian Rhapsody", artist="Queen"),
        Track(title="Stairway to Heaven", artist="Led Zeppelin"),
        Track(title="NonExistentSongTrackForTesting purposes", artist="NoClueArtist"),
    ]
    print("\n--- Testing find_track_match (with YTMusicAPI) ---")
    found_track_ids_for_playlist = []
    for s_track in sample_tracks_to_find:
        print(f"Searching for: '{s_track.title}' by {s_track.artist}")
        found_yt_id = client.find_track_match(s_track)
        if found_yt_id:
            print(f"  --> Found YouTube Music ID: {found_yt_id}")
            found_track_ids_for_playlist.append(found_yt_id)
        else:
            print(f"  --> No match found or error for '{s_track.title}'.")
        print("-" * 30)

    if not found_track_ids_for_playlist:
        print("\nNo tracks were successfully found via search. Using dummy track IDs for playlist add test.")
        # Provide some known valid (but potentially random) video IDs if you want to test adding *something*
        # These are just illustrative placeholders.
        found_track_ids_for_playlist = ["dQw4w9WgXcQ", "getVideoId"] # Rick Astley, random video ID
        print(f"Using dummy track IDs: {found_track_ids_for_playlist}")


    # --- Test create_playlist ---
    print("\n--- Testing create_playlist (Requires Auth) ---")
    if not auth_file_to_use:
        print("  No auth file provided. `create_playlist` is expected to fail or create public/unusable playlist.")

    new_playlist_title = "Test API Playlist"
    new_playlist_description = "Created by YouTubeMusicClient test script."
    created_playlist_id = client.create_playlist(
        name=new_playlist_title,
        description=new_playlist_description,
        public=False # Try creating a private playlist
    )

    if created_playlist_id:
        print(f"  --> Successfully created playlist: '{new_playlist_title}' with ID: {created_playlist_id}")

        # --- Test add_tracks_to_playlist ---
        print("\n--- Testing add_tracks_to_playlist (Requires Auth & Valid Playlist ID) ---")
        if not found_track_ids_for_playlist:
            print("    No track IDs available (real or dummy) to add. Skipping add_tracks_to_playlist test.")
        else:
            print(f"    Attempting to add {len(found_track_ids_for_playlist)} tracks to playlist ID: {created_playlist_id}")
            add_success = client.add_tracks_to_playlist(
                youtube_playlist_id=created_playlist_id,
                youtube_track_ids=found_track_ids_for_playlist
            )
            if add_success:
                print(f"  --> Successfully called add_tracks_to_playlist for playlist ID: {created_playlist_id}.")
                print(f"      (Note: Check your YouTube Music account to verify if tracks were actually added, especially if using dummy IDs).")
            else:
                print(f"  --> Failed to add tracks to playlist ID: {created_playlist_id}.")
    else:
        print(f"  --> Failed to create playlist '{new_playlist_title}'. Skipping add_tracks_to_playlist test.")
        print(f"      (This is expected if running without valid authentication via '{auth_file}').")

    print("\nYouTubeMusicClient example usage finished.")
    print("Reminder: Some operations (especially playlist creation/modification) require valid authentication.")
