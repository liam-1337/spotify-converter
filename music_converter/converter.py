import os
import sys

# Attempt to set up relative imports if running as a script
# This helps locate modules when the script is run directly from its directory
if __name__ == '__main__' and "." not in __package__:
    # Assuming the script is in 'music_converter' and 'common_models', 'spotify', 'youtube_music' are siblings
    # Or if it's one level down, adjust path accordingly.
    # This is a common pattern but might need adjustment based on exact execution context.
    # If 'music_converter' is the root package:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir) # Go up one level if converter.py is inside a 'scripts' or 'app' dir
                                          # If converter.py is at the root of the package, this line is not needed
                                          # For our current structure, converter.py is at the root of the package 'music_converter'
                                          # so common_models etc are submodules.
    # If music_converter itself is the top-level package:
    # sys.path.insert(0, os.path.dirname(script_dir)) # Add parent of 'music_converter' if needed
    # No, for current structure, if running 'python music_converter/converter.py', then 'music_converter' is not a package in path
    # We need to add the directory *containing* 'music_converter' to the path.
    # Or, better, run as 'python -m music_converter.converter' from outside.

    # For 'python music_converter/converter.py' from one level up:
    # sys.path.insert(0, os.getcwd()) # Add current working directory (parent of music_converter)

    # If running 'python converter.py' from *inside* 'music_converter' directory:
    if script_dir not in sys.path: # Current script's directory
         sys.path.insert(0, script_dir)
    # Add parent directory to sys.path to allow imports like 'from spotify.client import SpotifyClient'
    # if 'music_converter' is meant to be the package.
    # This is tricky. Standard way is to run 'python -m music_converter.converter' from the directory *above* music_converter.
    # The below imports assume that 'music_converter' package is in sys.path.

try:
    from spotify.client import SpotifyClient
    from youtube_music.client import YouTubeMusicClient
    from common_models.models import Playlist, Track
except ImportError as e:
    print(f"Error importing modules in converter.py: {e}")
    print("Please ensure you are running this script as part of the 'music_converter' package,")
    print("e.g., using 'python -m music_converter.converter' from the directory containing 'music_converter'.")
    # Define dummy classes if imports fail, to allow the script to be parsed at least
    class SpotifyClient:
        def __init__(self, *args, **kwargs): print("Dummy SpotifyClient used in converter")
        def get_user_playlists(self, limit=5): return []
        def get_playlist_tracks(self, playlist_id, limit=5): return []
        def get_liked_songs(self, limit=5): return []
    class YouTubeMusicClient:
        def __init__(self, *args, **kwargs): print("Dummy YouTubeMusicClient used in converter")
        def find_track_match(self, track): return None
        def create_playlist(self, name, description): return "dummy_yt_playlist_id"
        def add_tracks_to_playlist(self, pl_id, tr_ids): return False
    class Playlist: pass
    class Track: pass
    # sys.exit(1) # Optionally exit if imports fail critically

def transfer_spotify_to_youtube_music(spotify_api_token: str):
    """
    Main function to transfer playlists and liked songs
    from Spotify to YouTube Music.
    Uses a live SpotifyClient and a stubbed YouTubeMusicClient.
    """
    print("🚀 Starting Spotify to YouTube Music transfer process...")

    # Initialize clients
    spotify_client = SpotifyClient(api_token=spotify_api_token)
    # YouTubeMusicClient is a stub and doesn't need a real token for now
    youtube_music_client = YouTubeMusicClient()

    # 1. Get Spotify Playlists
    print("\n🎵 --- Fetching Spotify Playlists (max 5) ---")
    try:
        spotify_playlists = spotify_client.get_user_playlists(limit=5)
    except Exception as e:
        print(f"  ❌ ERROR fetching Spotify playlists: {e}")
        spotify_playlists = []

    if not spotify_playlists:
        print("  No Spotify playlists found or an error occurred. Skipping playlist transfer.")
    else:
        print(f"  ✅ Found {len(spotify_playlists)} Spotify playlists.")

        for sp_playlist in spotify_playlists:
            print(f"\n  🔄 Processing Spotify playlist: '{sp_playlist.name}' (ID: {sp_playlist.spotify_id}, API Tracks: {sp_playlist.total_tracks_from_api})")

            # 2. Get tracks for each Spotify playlist
            actual_tracks_in_playlist: List[Track] = []
            if sp_playlist.spotify_id and (sp_playlist.total_tracks_from_api is None or sp_playlist.total_tracks_from_api > 0) :
                print(f"    Fetching tracks for '{sp_playlist.name}' (max 10)...") # Limit tracks per playlist for demo
                try:
                    actual_tracks_in_playlist = spotify_client.get_playlist_tracks(sp_playlist.spotify_id, limit=10)
                    sp_playlist.tracks = actual_tracks_in_playlist # Update our playlist object
                    if actual_tracks_in_playlist:
                        print(f"    ✅ Fetched {len(actual_tracks_in_playlist)} tracks for '{sp_playlist.name}'.")
                    else:
                        print(f"    ⚠️ No tracks returned by API for '{sp_playlist.name}' (or fetch limit was 0).")
                except Exception as e:
                    print(f"    ❌ ERROR fetching tracks for '{sp_playlist.name}': {e}")
            elif sp_playlist.total_tracks_from_api == 0:
                print(f"    ⏩ Playlist '{sp_playlist.name}' has 0 tracks according to API, skipping track processing.")
            else:
                 print(f"    ⏩ Playlist '{sp_playlist.name}' has no ID or issue with track count, skipping track processing.")


            if not actual_tracks_in_playlist:
                print(f"    No tracks to process for Spotify playlist '{sp_playlist.name}'. Skipping YouTube Music playlist creation for this one.")
                continue

            # 3. Create a corresponding playlist on YouTube Music (simulated)
            yt_playlist_name = f"{sp_playlist.name} (From Spotify)"
            yt_playlist_description = sp_playlist.description if sp_playlist.description else f"Converted from Spotify playlist '{sp_playlist.name}'"

            print(f"    Attempting to create YouTube Music playlist: '{yt_playlist_name}' (simulated)...")
            yt_playlist_id = youtube_music_client.create_playlist(
                name=yt_playlist_name,
                description=yt_playlist_description
            )
            print(f"    ✅ Simulated YouTube Music playlist created with ID: {yt_playlist_id}")

            # 4. Find matches for each track and add to the new YouTube Music playlist (simulated)
            yt_track_ids_to_add = []
            print(f"    Looking for YouTube Music matches for {len(actual_tracks_in_playlist)} tracks (simulated)...")
            for track_num, sp_track in enumerate(actual_tracks_in_playlist):
                print(f"      Track {track_num + 1}/{len(actual_tracks_in_playlist)}: '{sp_track.title}' by {sp_track.artist} (Spotify ID: {sp_track.spotify_id})")
                yt_track_id = youtube_music_client.find_track_match(sp_track) # Stubbed call
                if yt_track_id:
                    print(f"        ➡️ Found simulated YouTube Music match: ID {yt_track_id}")
                    yt_track_ids_to_add.append(yt_track_id)
                else:
                    print(f"        ❌ No simulated YouTube Music match found for '{sp_track.title}'.")

            if yt_track_ids_to_add:
                print(f"    Attempting to add {len(yt_track_ids_to_add)} matched tracks to YouTube Music playlist '{yt_playlist_name}' (ID: {yt_playlist_id}) (simulated)...")
                youtube_music_client.add_tracks_to_playlist( # Stubbed call
                    youtube_playlist_id=yt_playlist_id,
                    youtube_track_ids=yt_track_ids_to_add
                )
            else:
                print(f"    No tracks to add to simulated YouTube Music playlist '{yt_playlist_name}'.")

    # 5. Get Spotify Liked Songs & simulate adding to a "Liked Songs" playlist on YouTube Music
    print("\n🎵 --- Fetching Spotify Liked Songs (max 10) ---")
    try:
        spotify_liked_songs = spotify_client.get_liked_songs(limit=10)
    except Exception as e:
        print(f"  ❌ ERROR fetching Spotify liked songs: {e}")
        spotify_liked_songs = []

    if not spotify_liked_songs:
        print("  No Spotify liked songs found or an error occurred.")
    else:
        print(f"  ✅ Found {len(spotify_liked_songs)} Spotify liked songs.")

        yt_liked_playlist_name = "Spotify Liked Songs (Imported)"
        print(f"  Attempting to create YouTube Music playlist for Liked Songs: '{yt_liked_playlist_name}' (simulated)...")
        yt_liked_playlist_id = youtube_music_client.create_playlist(
            name=yt_liked_playlist_name,
            description="Songs you liked on Spotify"
        )
        print(f"  ✅ Simulated YouTube Music playlist for Liked Songs created with ID: {yt_liked_playlist_id}")

        yt_liked_track_ids_to_add = []
        print(f"  Looking for YouTube Music matches for {len(spotify_liked_songs)} liked songs (simulated)...")
        for track_num, sp_track in enumerate(spotify_liked_songs):
            print(f"    Liked Song {track_num + 1}/{len(spotify_liked_songs)}: '{sp_track.title}' by {sp_track.artist} (Spotify ID: {sp_track.spotify_id})")
            yt_track_id = youtube_music_client.find_track_match(sp_track) # Stubbed call
            if yt_track_id:
                print(f"      ➡️ Found simulated YouTube Music match: ID {yt_track_id}")
                yt_liked_track_ids_to_add.append(yt_track_id)
            else:
                print(f"      ❌ No simulated YouTube Music match found for liked song '{sp_track.title}'.")

        if yt_liked_track_ids_to_add:
            print(f"  Attempting to add {len(yt_liked_track_ids_to_add)} matched liked songs to playlist '{yt_liked_playlist_name}' (ID: {yt_liked_playlist_id}) (simulated)...")
            youtube_music_client.add_tracks_to_playlist( # Stubbed call
                youtube_playlist_id=yt_liked_playlist_id,
                youtube_track_ids=yt_liked_track_ids_to_add
            )
        else:
            print(f"  No liked songs to add to simulated YouTube Music playlist '{yt_liked_playlist_name}'.")

    print("\n🏁 Transfer simulation completed.")

if __name__ == '__main__':
    # -------------------------------------------------------------
    # Spotify to YouTube Music Converter Simulation - Manual Testing
    # -------------------------------------------------------------
    #
    # This script simulates the transfer of music data from Spotify
    # to YouTube Music. It uses:
    #   - A REAL Spotify client: Fetches actual data if a Spotify API token is provided.
    #   - A SIMULATED YouTube Music client: Mimics YouTube Music actions without real API calls.
    #
    # --- How to Run for Testing ---
    #
    # 1. Set your Spotify API Token:
    #    - The script will first look for an environment variable named `SPOTIFY_API_TOKEN`.
    #      Example (Linux/macOS): export SPOTIFY_API_TOKEN="your_actual_spotify_token_here"
    #      Example (Windows CMD): set SPOTIFY_API_TOKEN="your_actual_spotify_token_here"
    #      Example (Windows PowerShell): $env:SPOTIFY_API_TOKEN="your_actual_spotify_token_here"
    #    - If the environment variable is not found, the script will prompt you to paste the token.
    #    - IMPORTANT: Your Spotify API token is sensitive. Do not share it or commit it to version control.
    #                 The prompt is for local testing convenience only.
    #    - To get a token: You usually need to go through Spotify's OAuth 2.0 authorization flow.
    #      A quick way to get a temporary one for testing is from the Spotify Web API console:
    #      https://developer.spotify.com/console/ (e.g., choose 'Get Current User's Playlists')
    #      Make sure to request necessary scopes (e.g., `playlist-read-private`, `user-library-read`).
    #
    # 2. Navigate to the directory ABOVE 'music_converter'.
    #    For example, if your structure is /path/to/project/music_converter, cd to /path/to/project.
    #
    # 3. Run the script as a module:
    #    python -m music_converter.converter
    #
    # --- What to Observe ---
    #   - Spotify Data: If a valid token is provided, you should see output indicating that
    #     your Spotify playlists and liked songs are being fetched (names, track counts).
    #   - YouTube Music Simulation: You will see messages about:
    #     - Simulated searches for tracks on YouTube Music.
    #     - Simulated creation of new playlists on YouTube Music.
    #     - Simulated addition of (matched) tracks to these new YouTube Music playlists.
    #   - No actual changes will be made to your YouTube Music account as this part is stubbed.
    #   - Error Messages: If the Spotify token is invalid or network issues occur, you'll see error messages.
    #
    # -------------------------------------------------------------

    print("-------------------------------------------------------------")
    print("Spotify to YouTube Music Converter Simulation")
    print("-------------------------------------------------------------")
    print("This script uses a REAL Spotify client (if token provided)")
    print("and a SIMULATED YouTube Music client.")
    print("-------------------------------------------------------------")

    spotify_token = os.environ.get("SPOTIFY_API_TOKEN")

    if not spotify_token:
        print("\n⚠️ SPOTIFY_API_TOKEN environment variable not set.")
        try:
            # This input prompt is for CONVENIENCE during local interactive testing ONLY.
            # In a real application, tokens should be handled securely (e.g., OAuth flow).
            print("You can manually paste a Spotify API Token below to proceed with live Spotify calls.")
            print("If you press Enter without pasting a token, Spotify calls will likely fail or use dummy data if client is robust.")
            spotify_token_input = input("Enter Spotify API Token (or press Enter to skip): ")
            if spotify_token_input:
                spotify_token = spotify_token_input
            else:
                print("No Spotify token provided. Spotify calls may fail.")
        except KeyboardInterrupt:
            print("\nCancelled by user. Exiting.")
            sys.exit(0)
        except EOFError: # Happens if input is piped from a non-interactive source
            print("\nNo input received (EOF). Spotify calls may fail if token not in env.")


    if not spotify_token:
        print("\n🛑 No Spotify API Token available. Cannot make live calls to Spotify.")
        print("The script will run with the Spotify client attempting to use a None token, which will likely result in errors for API calls.")
        # Initialize with a clearly invalid token to ensure failure or dummy behavior from client
        spotify_token = "INVALID_TOKEN_DO_NOT_USE"

    transfer_spotify_to_youtube_music(spotify_api_token=spotify_token)
