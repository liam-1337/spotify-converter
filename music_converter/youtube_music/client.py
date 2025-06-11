import time
import random
from typing import List, Optional
import os # For checking file path

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

    # ... (find_track_match, create_playlist, add_tracks_to_playlist methods will be updated later)
    # Make sure to keep the existing stub methods for now, they will be replaced in the next steps.

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

            # For now, assume the first result is the best match.
            # More sophisticated matching could involve checking duration, album, etc.
            # but ytmusicapi search results for songs are quite good.

            # Example song item from ytmusic.search(filter='songs'):
            # {
            #   'category': 'Songs', 'resultType': 'song', 'title': '...', 'artists': [{'name': '...', 'id': '...'}],
            #   'album': {'name': '...', 'id': '...'}, 'duration': '3:10', 'duration_seconds': 190,
            #   'isExplicit': False, 'videoId': 'VIDEO_ID_HERE', 'feedbackTokens': {...}, 'likeStatus': 'INDIFFERENT'
            # }

            best_match = None
            for item in search_results:
                # Ensure it's a song and has a videoId
                if item.get('resultType') == 'song' and item.get('videoId'):
                    # Basic check: do artists roughly match? (Case-insensitive)
                    # Artist names in YTM results are in a list of dicts: item['artists'][0]['name']
                    yt_artists = [a.get('name', '').lower() for a in item.get('artists', [])]
                    query_artist_lower = track_info.artist.lower()

                    # Simple artist check: if any of the YT artists are in our query artist string, or vice-versa
                    # This is a very basic heuristic.
                    artist_match_found = False
                    for yt_artist_name_lower in yt_artists:
                        if yt_artist_name_lower in query_artist_lower or query_artist_lower in yt_artist_name_lower:
                            artist_match_found = True
                            break

                    if artist_match_found:
                        best_match = item
                        break # Take the first "artist-matched" song
                # Fallback: if no artist match from top results, take first song if available
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
                for i, item in enumerate(search_results[:3]): # Log first 3 results for diagnostics
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
            # If the exception is from ytmusicapi due to auth, it might be caught here.
            # e.g. if self.ytmusic is None or methods fail due to lack of authentication.
            return None


    def create_playlist(self, name: str, description: str = "", public: bool = True) -> str:
        """ Placeholder - will be replaced """
        playlist_visibility = "public" if public else "private"
        print(f"  YTMClient (STUB): Simulating creating playlist: '{name}' (Description: '{description}', Visibility: {playlist_visibility})...")
        dummy_playlist_id = f"ytmusic:playlist:{name.replace(' ', '_').lower()}"
        return dummy_playlist_id

    def add_tracks_to_playlist(self, youtube_playlist_id: str, youtube_track_ids: List[str]) -> bool:
        """ Placeholder - will be replaced """
        print(f"  YTMClient (STUB): Simulating adding {len(youtube_track_ids)} tracks to playlist ID: {youtube_playlist_id}...")
        if not youtube_track_ids: return False
        return True

# The if __name__ == '__main__': block will be updated later.
# For now, retain the existing __main__ block.
if __name__ == '__main__':
    print("------------------------------------------------------------------")
    print("YouTubeMusicClient with YTMusicAPI - Example Usage")
    print("------------------------------------------------------------------")
    print("This example demonstrates initializing the client and using 'find_track_match'.")
    print("For many YTMusicAPI features (like creating private playlists or accessing user library),")
    print("you need to provide an authentication file (e.g., 'headers_auth.json').")
    print("You can set up 'ytmusicapi' by running: `ytmusicapi setup` in your terminal.")
    print("------------------------------------------------------------------")

    # Path to your authentication headers JSON file (if you have one)
    # Replace with the actual path to your 'headers_auth.json' or similar.
    # If you don't have one, search might be limited to public results or fail for some queries.
    auth_file = "headers_auth.json" # Default name ytmusicapi setup suggests

    # Check if a local auth file exists in the current directory for testing
    local_auth_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), auth_file)
    # Or, you might want to specify an absolute path or allow user input:
    # auth_file_to_use = input(f"Enter path to YTMusicAPI auth headers file (e.g., {auth_file}) or press Enter to skip: ")

    auth_file_to_use = None
    if os.path.exists(auth_file): # Check in current working directory first
        auth_file_to_use = auth_file
        print(f"Found potential auth file in current directory: '{auth_file}'")
    elif os.path.exists(local_auth_file_path): # Check in script's directory
        auth_file_to_use = local_auth_file_path
        print(f"Found potential auth file in script directory: '{local_auth_file_path}'")
    else:
        print(f"No auth file ('{auth_file}') found in current or script directory.")
        print("Proceeding without authentication. Search results may be limited.")

    print("\nInitializing YouTubeMusicClient...")
    if auth_file_to_use:
        print(f"Attempting to use auth file: {auth_file_to_use}")
    client = YouTubeMusicClient(auth_headers_file_path=auth_file_to_use)

    # Example Tracks for testing find_track_match
    # Using common, well-known tracks for better chance of public search success
    sample_tracks_to_find = [
        Track(title="Bohemian Rhapsody", artist="Queen"),
        Track(title="Stairway to Heaven", artist="Led Zeppelin"),
        Track(title="Hotel California", artist="Eagles"),
        Track(title="Eine Kleine Nachtmusik", artist="Wolfgang Amadeus Mozart"), # Classical
        Track(title="NonExistentSong123", artist="NoArtistXYZ"), # Likely to fail
    ]

    print("\n--- Testing find_track_match (with YTMusicAPI) ---")
    if not hasattr(client, 'ytmusic') or isinstance(client.ytmusic, type(None)) or not callable(getattr(client.ytmusic, 'search', None)):
        print("  YTMusicAPI instance not properly initialized in client. Skipping find_track_match test.")
    else:
        for s_track in sample_tracks_to_find:
            print(f"Searching for: '{s_track.title}' by {s_track.artist}")
            found_yt_id = client.find_track_match(s_track) # This now calls the real implementation
            if found_yt_id:
                print(f"  --> Found YouTube Music ID: {found_yt_id}")
            else:
                print(f"  --> No match found or error for '{s_track.title}'.")
            print("-" * 30)

    print("\n--- Testing STUBBED methods (create_playlist, add_tracks_to_playlist) ---")
    # These methods are still stubs from the previous version
    # Calling them to ensure they don't crash and to show they are next to be implemented

    print("Calling stubbed create_playlist...")
    stub_playlist_id = client.create_playlist(name="Test YTMusicAPI Playlist", description="A test playlist (stubbed)")
    print(f"Stubbed create_playlist returned ID: {stub_playlist_id}")

    if stub_playlist_id:
        print("\nCalling stubbed add_tracks_to_playlist...")
        # Let's use some dummy IDs for this stub call
        dummy_track_ids_for_stub = ["dummy_yt_video_id_1", "dummy_yt_video_id_2"]
        stub_add_success = client.add_tracks_to_playlist(
            youtube_playlist_id=stub_playlist_id,
            youtube_track_ids=dummy_track_ids_for_stub
        )
        print(f"Stubbed add_tracks_to_playlist returned: {stub_add_success}")

    print("\nYouTubeMusicClient example usage finished.")
