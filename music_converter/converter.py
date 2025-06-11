import os
import sys
from typing import Optional, List # Ensure List is imported

# Attempt to set up relative imports if running as a script
# This helps locate modules when the script is run directly from its directory
if __name__ == '__main__' and "." not in __package__:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
         sys.path.insert(0, script_dir)

try:
    from spotify.client import SpotifyClient
    from youtube_music.client import YouTubeMusicClient
    from common_models.models import Playlist, Track
except ImportError as e:
    print(f"Error importing modules in converter.py: {e}")
    print("Please ensure you are running this script as part of the 'music_converter' package,")
    print("e.g., using 'python -m music_converter.converter' from the directory containing 'music_converter'.")
    class SpotifyClient:
        def __init__(self, *args, **kwargs): print("Dummy SpotifyClient used in converter")
        def get_user_playlists(self, limit=5): return []
        def get_playlist_tracks(self, playlist_id, limit=5): return []
        def get_liked_songs(self, limit=5): return []
    class YouTubeMusicClient:
        def __init__(self, *args, **kwargs): print("Dummy YouTubeMusicClient used in converter")
        def find_track_match(self, track): return None
        def create_playlist(self, name, description, public=True): return "dummy_yt_playlist_id" # Match signature
        def add_tracks_to_playlist(self, pl_id, tr_ids): return False
    # Ensure dummy models match field expectations if real ones aren't loaded
    class Track:
        def __init__(self, title: str, artist: str, album: Optional[str]=None, duration_ms: Optional[int]=0, spotify_id: Optional[str]=None, youtube_id: Optional[str]=None):
            self.title = title
            self.artist = artist
            self.album = album
            self.duration_ms = duration_ms
            self.spotify_id = spotify_id
            self.youtube_id = youtube_id
    class Playlist:
        def __init__(self, name: str, tracks: List[Track], description: Optional[str]="", spotify_id: Optional[str]=None, youtube_id: Optional[str]=None, total_tracks_from_api: Optional[int]=None):
            self.name = name
            self.tracks = tracks
            self.description = description
            self.spotify_id = spotify_id
            self.youtube_id = youtube_id
            self.total_tracks_from_api = total_tracks_from_api


def transfer_spotify_to_youtube_music(spotify_api_token: str, ytm_auth_json_path: Optional[str] = None):
    """
    Main function to transfer playlists and liked songs
    from Spotify to YouTube Music using live clients.
    """
    print("🚀🚀🚀 Starting Spotify to YouTube Music LIVE transfer process... 🚀🚀🚀")
    print(f"Spotify Token: {'Provided' if spotify_api_token and spotify_api_token != 'INVALID_SPOTIFY_TOKEN' else 'MISSING/Invalid'}")
    print(f"YTM Auth JSON: {ytm_auth_json_path if ytm_auth_json_path else 'Not Provided'}")


    # Initialize clients
    print("\n🎧 Initializing Spotify Client...")
    spotify_client = SpotifyClient(api_token=spotify_api_token)

    print("🎧 Initializing YouTube Music Client...")
    youtube_music_client = YouTubeMusicClient(auth_headers_file_path=ytm_auth_json_path)

    # --- 1. Process Spotify Playlists ---
    print("\n🎵 --- Fetching Spotify Playlists (max 5) ---")
    try:
        spotify_playlists = spotify_client.get_user_playlists(limit=5)
        if not spotify_playlists: # Handles None or empty list
            print("  ⚠️ No Spotify playlists found or an error occurred during fetch. Skipping playlist transfer.")
        else:
            print(f"  ✅ Successfully fetched {len(spotify_playlists)} Spotify playlists.")
    except Exception as e: # Catch any exception from client call itself
        print(f"  ❌ CRITICAL ERROR fetching Spotify playlists: {e}")
        spotify_playlists = [] # Ensure it's an empty list to prevent further errors

    if spotify_playlists: # Check if list is not empty
        for sp_playlist in spotify_playlists:
            if not sp_playlist or not hasattr(sp_playlist, 'spotify_id') or not sp_playlist.spotify_id : # Basic check on playlist object
                print(f"  Skipping invalid Spotify playlist object: {sp_playlist}")
                continue

            print(f"\n  🔄 Processing Spotify playlist: '{sp_playlist.name}' (ID: {sp_playlist.spotify_id}, API Tracks: {getattr(sp_playlist, 'total_tracks_from_api', 'N/A')})")

            actual_tracks_in_playlist: List[Track] = []
            # Use getattr for total_tracks_from_api for safety with dummy objects
            total_tracks = getattr(sp_playlist, 'total_tracks_from_api', 0)
            if total_tracks is None or total_tracks > 0: # if None, we attempt fetch
                print(f"    Fetching tracks for '{sp_playlist.name}' (max 10)...")
                try:
                    # Assuming get_playlist_tracks returns List[Track] or raises error
                    actual_tracks_in_playlist = spotify_client.get_playlist_tracks(sp_playlist.spotify_id, limit=10)
                    # sp_playlist.tracks = actual_tracks_in_playlist # Update our playlist object - careful if dummy
                    if hasattr(sp_playlist, 'tracks'):
                         sp_playlist.tracks = actual_tracks_in_playlist

                    if actual_tracks_in_playlist: # Check if list is not empty
                        print(f"    ✅ Successfully fetched {len(actual_tracks_in_playlist)} tracks for '{sp_playlist.name}'.")
                    else:
                        print(f"    ⚠️ No tracks returned by API for '{sp_playlist.name}' (or fetch limit was 0).")
                except Exception as e:
                    print(f"    ❌ ERROR fetching tracks for '{sp_playlist.name}': {e}")
                    actual_tracks_in_playlist = [] # Ensure it's empty on error
            elif total_tracks == 0:
                print(f"    ⏩ Playlist '{sp_playlist.name}' has 0 tracks according to API. Skipping track processing.")
            else:
                 print(f"    ⏩ Playlist '{sp_playlist.name}' has issue with track count. Skipping track processing.")

            if not actual_tracks_in_playlist: # Check if list is empty
                print(f"    No tracks to process for Spotify playlist '{sp_playlist.name}'. Skipping YouTube Music playlist creation for this one.")
                continue

            yt_playlist_name = f"{sp_playlist.name} (From Spotify)"
            yt_playlist_description = getattr(sp_playlist, 'description', "") if getattr(sp_playlist, 'description', "") else f"Converted from Spotify playlist '{sp_playlist.name}'"

            print(f"    Attempting to create YouTube Music playlist: '{yt_playlist_name}'...")
            yt_playlist_id = youtube_music_client.create_playlist(
                name=yt_playlist_name,
                description=yt_playlist_description,
                public=False
            )

            if not yt_playlist_id:
                print(f"    ❌ Failed to create YouTube Music playlist for '{sp_playlist.name}'. Skipping track additions for this playlist.")
                continue

            print(f"    ✅ Successfully created YouTube Music playlist '{yt_playlist_name}' with ID: {yt_playlist_id}")

            yt_track_ids_to_add = []
            print(f"    Looking for YouTube Music matches for {len(actual_tracks_in_playlist)} tracks...")
            for track_num, sp_track_item in enumerate(actual_tracks_in_playlist):
                if not sp_track_item or not hasattr(sp_track_item, 'title') or not hasattr(sp_track_item, 'artist'):
                    print(f"      Skipping invalid Spotify track object at index {track_num}.")
                    continue
                print(f"      Track {track_num + 1}/{len(actual_tracks_in_playlist)}: '{sp_track_item.title}' by {sp_track_item.artist} (Spotify ID: {getattr(sp_track_item, 'spotify_id', 'N/A')})")
                yt_track_id = youtube_music_client.find_track_match(sp_track_item)
                if yt_track_id:
                    print(f"        ➡️ Found YouTube Music match: ID {yt_track_id}")
                    yt_track_ids_to_add.append(yt_track_id)
                else:
                    print(f"        ❌ No YouTube Music match found for '{sp_track_item.title}'.")

            if yt_track_ids_to_add:
                print(f"    Attempting to add {len(yt_track_ids_to_add)} matched tracks to YTM playlist '{yt_playlist_name}' (ID: {yt_playlist_id})...")
                add_success = youtube_music_client.add_tracks_to_playlist(
                    youtube_playlist_id=yt_playlist_id,
                    youtube_track_ids=yt_track_ids_to_add
                )
                if add_success:
                    print(f"    ✅ Successfully called add_tracks_to_playlist for YTM playlist '{yt_playlist_name}'.")
                else:
                    print(f"    ❌ Failed to add tracks to YTM playlist '{yt_playlist_name}'.")
            else:
                print(f"    No tracks to add to YouTube Music playlist '{yt_playlist_name}'.")

    # --- 2. Process Spotify Liked Songs ---
    print("\n🎵 --- Fetching Spotify Liked Songs (max 10) ---")
    try:
        spotify_liked_songs = spotify_client.get_liked_songs(limit=10)
        if not spotify_liked_songs:
            print("  ⚠️ No Spotify liked songs found or an error occurred during fetch.")
        else:
            print(f"  ✅ Successfully fetched {len(spotify_liked_songs)} Spotify liked songs.")
    except Exception as e:
        print(f"  ❌ CRITICAL ERROR fetching Spotify liked songs: {e}")
        spotify_liked_songs = []

    if spotify_liked_songs:
        yt_liked_playlist_name = "Spotify Liked Songs (Imported)"
        print(f"  Attempting to create YTM playlist for Liked Songs: '{yt_liked_playlist_name}'...")
        yt_liked_playlist_id = youtube_music_client.create_playlist(
            name=yt_liked_playlist_name,
            description="Songs I liked on Spotify", # Corrected description
            public=False
        )

        if not yt_liked_playlist_id:
            print(f"  ❌ Failed to create YTM playlist for Liked Songs. Skipping adding liked songs.")
        else:
            print(f"  ✅ Successfully created YTM playlist for Liked Songs with ID: {yt_liked_playlist_id}")

            yt_liked_track_ids_to_add = []
            print(f"  Looking for YTM matches for {len(spotify_liked_songs)} liked songs...")
            for track_num, sp_track_item in enumerate(spotify_liked_songs):
                if not sp_track_item or not hasattr(sp_track_item, 'title') or not hasattr(sp_track_item, 'artist'):
                    print(f"    Skipping invalid Spotify liked song object at index {track_num}.")
                    continue
                print(f"    Liked Song {track_num + 1}/{len(spotify_liked_songs)}: '{sp_track_item.title}' by {sp_track_item.artist} (Spotify ID: {getattr(sp_track_item, 'spotify_id', 'N/A')})")
                yt_track_id = youtube_music_client.find_track_match(sp_track_item)
                if yt_track_id:
                    print(f"      ➡️ Found YTM match: ID {yt_track_id}")
                    yt_liked_track_ids_to_add.append(yt_track_id)
                else:
                    print(f"      ❌ No YTM match found for liked song '{sp_track_item.title}'.")

            if yt_liked_track_ids_to_add:
                print(f"  Attempting to add {len(yt_liked_track_ids_to_add)} matched liked songs to YTM playlist '{yt_liked_playlist_name}'...")
                add_success_liked = youtube_music_client.add_tracks_to_playlist(
                    youtube_playlist_id=yt_liked_playlist_id,
                    youtube_track_ids=yt_liked_track_ids_to_add
                )
                if add_success_liked:
                    print(f"  ✅ Successfully called add_tracks_to_playlist for Liked Songs YTM playlist.")
                else:
                    print(f"  ❌ Failed to add tracks to Liked Songs YTM playlist.")
            else:
                print(f"  No liked songs to add to YTM playlist '{yt_liked_playlist_name}'.")

    print("\n🏁🏁🏁 Transfer process finished. 🏁🏁🏁")
    print("Please check your YouTube Music account if operations were expected to succeed.")

if __name__ == '__main__':
    # --------------------------------------------------------------------------
    # Spotify to YouTube Music Converter - End-to-End Testing Instructions
    # --------------------------------------------------------------------------
    #
    #
    # This script attempts a full transfer of music data from Spotify to YouTube Music.
    # It uses LIVE clients for both services, meaning REAL CHANGES can occur
    # in your YouTube Music account if authentication is provided and operations succeed.
    #
    # --- How to Run for End-to-End Testing ---
    #
    # 1. Spotify Authentication (SPOTIFY_API_TOKEN):
    #    - Set the `SPOTIFY_API_TOKEN` environment variable to your Spotify API token.
    #      Example (Linux/macOS): export SPOTIFY_API_TOKEN="your_spotify_token"
    #      Example (Windows CMD): set SPOTIFY_API_TOKEN="your_spotify_token"
    #    - If not set, the script will prompt you to paste the token.
    #    - Get a token via Spotify's OAuth 2.0 flow or from their Web API console
    #      (https://developer.spotify.com/console/) with scopes like
    #      `playlist-read-private`, `user-library-read`.
    #
    # 2. YouTube Music Authentication (YTM_AUTH_JSON_PATH):
    #    - Set the `YTM_AUTH_JSON_PATH` environment variable to the *absolute path*
    #      of your YouTube Music authentication headers file (e.g., `headers_auth.json`).
    #      Example (Linux/macOS): export YTM_AUTH_JSON_PATH="/path/to/your/headers_auth.json"
    #      Example (Windows CMD): set YTM_AUTH_JSON_PATH="C:\path\to\your\headers_auth.json"
    #    - If not set, the script will prompt for the path.
    #    - Generate `headers_auth.json` by running `ytmusicapi setup` in your terminal
    #      and following the instructions. This file allows `ytmusicapi` to act on your behalf.
    #    - CRITICAL: Without this auth file, YouTube Music operations that require login
    #                (creating playlists, adding tracks) WILL FAIL or work in a limited way.
    #
    # 3. Navigate to the directory ABOVE 'music_converter'.
    #    (e.g., if structure is /project/music_converter, cd to /project)
    #
    # 4. Run the script as a module:
    #    python -m music_converter.converter
    #
    # --- What to Observe During an End-to-End Test ---
    #
    #   - Initialization: Messages indicating whether Spotify token and YTM auth path
    #     were found/provided.
    #   - Spotify Data Fetching:
    #     - Logs showing successful fetching of your Spotify playlists and liked songs.
    #     - Errors if the Spotify token is invalid or network issues occur.
    #   - YouTube Music Operations (requires YTM_AUTH_JSON_PATH for success):
    #     - Track Matching: Logs for each Spotify track showing attempts to find a match
    #       on YouTube Music and the outcome (found ID or no match).
    #     - Playlist Creation: Messages indicating attempts to create new playlists on
    #       YouTube Music (e.g., "My Playlist (From Spotify)"). Success or failure
    #       (especially failure if not authenticated for YTM).
    #     - Adding Tracks: Messages about attempts to add matched tracks to the newly
    #       created YouTube Music playlists. Success or failure.
    #
    #   - Final Output:
    #     - The script will print a "Transfer process finished" message.
    #     - CHECK YOUR YOUTUBE MUSIC ACCOUNT: If YTM authentication was valid and
    #       operations were logged as successful, you should see new playlists and tracks.
    #     - CHECK CONSOLE FOR ERRORS: Pay close attention to any error messages,
    #       especially regarding authentication or API limits.
    #
    # --- IMPORTANT NOTES ---
    #   - API Rate Limits: Both Spotify and YouTube Music have API rate limits.
    #     Excessive use in a short period might lead to temporary blocks.
    #   - Data Accuracy: Track matching is heuristic. Not all tracks may be found,
    #     or incorrect versions might sometimes be matched.
    #   - Use with Caution: Since this interacts with live accounts, be mindful,
    #     especially when testing with your primary music accounts.
    # --------------------------------------------------------------------------

    print("-------------------------------------------------------------")
    print("Spotify to YouTube Music Converter - Live Clients")
    print("-------------------------------------------------------------")
    print("This script uses REAL Spotify and REAL YouTube Music clients (if auth provided).")
    print("Ensure you have valid authentication for both services for full functionality.")
    print("-------------------------------------------------------------")

    # --- Spotify Authentication ---
    spotify_token = os.environ.get("SPOTIFY_API_TOKEN")
    if not spotify_token:
        print("\n⚠️ SPOTIFY_API_TOKEN environment variable not set.")
        try:
            print("You can manually paste a Spotify API Token below.")
            spotify_token_input = input("Enter Spotify API Token (or press Enter to skip): ")
            if spotify_token_input:
                spotify_token = spotify_token_input
        except KeyboardInterrupt:
            print("\nCancelled by user. Exiting.")
            sys.exit(0)
        except EOFError:
            print("\nNo input received for Spotify token.")

    if not spotify_token:
        print("\n🛑 No Spotify API Token. Spotify calls will likely fail.")
        spotify_token = "INVALID_SPOTIFY_TOKEN" # Ensure it's not None for client init

    # --- YouTube Music Authentication ---
    ytm_auth_path = os.environ.get("YTM_AUTH_JSON_PATH")
    if not ytm_auth_path:
        print("\n⚠️ YTM_AUTH_JSON_PATH environment variable not set for YouTube Music.")
        try:
            print("This should be the path to your 'headers_auth.json' file for ytmusicapi.")
            print("You can generate this by running `ytmusicapi setup` in your terminal.")
            ytm_auth_path_input = input("Enter path to YouTube Music auth JSON (e.g., headers_auth.json) or press Enter to skip: ")
            if ytm_auth_path_input:
                ytm_auth_path = ytm_auth_path_input
        except KeyboardInterrupt:
            print("\nCancelled by user. Exiting.")
            sys.exit(0)
        except EOFError:
            print("\nNo input received for YouTube Music auth path.")

    if not ytm_auth_path:
        print("\nℹ️ No YouTube Music auth JSON path. YouTube Music operations requiring login (like creating private playlists or adding tracks) will likely fail.")
    elif not os.path.exists(ytm_auth_path):
        print(f"\n⚠️ YouTube Music auth JSON file not found at: {ytm_auth_path}")
        print("   Operations requiring login will likely fail.")
        ytm_auth_path = None # Set to None if path is invalid

    # --- Call the main transfer function ---
    print("\n🚀 Starting transfer process...")
    transfer_spotify_to_youtube_music(
        spotify_api_token=spotify_token,
        ytm_auth_json_path=ytm_auth_path
    )
