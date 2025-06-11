import time # For simulating delays
import random # For varied outcomes
from typing import List, Optional

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
                self.album = album # Made optional for simpler dummy data
                self.duration_ms = duration_ms
                self.spotify_id = spotify_id
                self.youtube_id = youtube_id # Important for the context of this client
            def __repr__(self):
                return f"Track(title='{self.title}', artist='{self.artist}')"

class YouTubeMusicClient:
    def __init__(self, api_token: Optional[str] = None): # api_token is optional for stubs
        """
        Initializes the YouTube Music client (Stub).
        api_token is a placeholder and not used in this stub implementation.
        """
        self.api_token = api_token
        if api_token:
            print(f"YouTubeMusicClient initialized (stubbed) with a dummy token.")
        else:
            print(f"YouTubeMusicClient initialized (stubbed) without a token.")

    def find_track_match(self, track_info: Track) -> Optional[str]:
        """
        Placeholder for finding a matching track on YouTube Music.
        Simulates finding a track with varied outcomes and slight delay.
        Returns a dummy YouTube Music track ID or None if not found.
        """
        print(f"  YTMClient: Simulating search for track: '{track_info.title}' by '{track_info.artist}'...")
        time.sleep(random.uniform(0.1, 0.3)) # Simulate network delay

        # Simulate different outcomes
        # For ~70% of tracks, simulate a find.
        # For specific known titles (from Spotify dummy data), make it more predictable.
        if track_info.title in ["Song A", "Track One", "Liked Song 1", "Song B", "Track Two", "Liked Song 2", "Another Track"]:
            if random.random() < 0.9: # 90% chance of finding these known tracks
                dummy_yt_id = f"ytmusic:track:{track_info.title.replace(' ', '_').lower()}_{track_info.artist.replace(' ', '_').lower()}"
                print(f"    YTMClient: Match found for '{track_info.title}'. Assigning dummy ID: {dummy_yt_id}")
                return dummy_yt_id
        elif random.random() < 0.6: # 60% chance of finding other tracks
            dummy_yt_id = f"ytmusic:track:{track_info.title.replace(' ', '_').lower()}_{track_info.artist.replace(' ', '_').lower()}"
            print(f"    YTMClient: Match found for '{track_info.title}'. Assigning dummy ID: {dummy_yt_id}")
            return dummy_yt_id

        print(f"    YTMClient: No match found for '{track_info.title}'.")
        return None

    def create_playlist(self, name: str, description: str = "", public: bool = True) -> str:
        """
        Placeholder for creating a new playlist on YouTube Music.
        Returns a predictable dummy YouTube Music playlist ID.
        """
        playlist_visibility = "public" if public else "private"
        print(f"  YTMClient: Simulating creating playlist: '{name}' (Description: '{description}', Visibility: {playlist_visibility})...")
        time.sleep(random.uniform(0.1, 0.2))
        # Return a predictable dummy ID based on the name for testing
        dummy_playlist_id = f"ytmusic:playlist:{name.replace(' ', '_').lower()}"
        print(f"    YTMClient: Simulated creating playlist '{name}'. Assigned dummy ID: {dummy_playlist_id}")
        return dummy_playlist_id

    def add_tracks_to_playlist(self, youtube_playlist_id: str, youtube_track_ids: List[str]) -> bool:
        """
        Placeholder for adding tracks to a playlist on YouTube Music.
        Simulates the action and returns True if successful (always true if tracks are provided).
        """
        print(f"  YTMClient: Simulating adding {len(youtube_track_ids)} tracks to playlist ID: {youtube_playlist_id}...")
        time.sleep(random.uniform(0.2, 0.5))
        if not youtube_track_ids:
            print("    YTMClient: No track IDs provided to add.")
            return False
        for track_id in youtube_track_ids:
            print(f"    YTMClient: Simulated adding track ID: {track_id} to playlist {youtube_playlist_id}")
        print(f"  YTMClient: Successfully simulated adding {len(youtube_track_ids)} tracks to playlist {youtube_playlist_id}.")
        return True

if __name__ == '__main__':
    print("Running YouTubeMusicClient stub example usage...")

    # Initialize client (no token needed for stub)
    client = YouTubeMusicClient()

    # Example Tracks (ensure Track class is available)
    # These would typically come from the Spotify client in a real scenario
    sample_tracks_to_find = [
        Track(title="Song A", artist="Artist X"),
        Track(title="Unknown Song", artist="Artist U"),
        Track(title="Liked Song 1", artist="Artist L"),
        Track(title="Ephemeral Tune", artist="Artist E"),
    ]

    print("\n--- Testing find_track_match ---")
    matched_ids = []
    for s_track in sample_tracks_to_find:
        found_id = client.find_track_match(s_track)
        if found_id:
            matched_ids.append(found_id)
            print(f"  Result for '{s_track.title}': Found, ID = {found_id}")
        else:
            print(f"  Result for '{s_track.title}': Not Found")

    print("\n--- Testing create_playlist ---")
    new_playlist_name = "My Simulated YouTube Hits"
    new_playlist_id = client.create_playlist(name=new_playlist_name, description="Test playlist from converter stubs")
    print(f"  Result for create_playlist '{new_playlist_name}': Created, ID = {new_playlist_id}")

    print("\n--- Testing add_tracks_to_playlist ---")
    if matched_ids:
        success = client.add_tracks_to_playlist(youtube_playlist_id=new_playlist_id, youtube_track_ids=matched_ids)
        print(f"  Result for add_tracks_to_playlist (with {len(matched_ids)} tracks): {'Successful' if success else 'Failed'}")
    else:
        print("  Skipping add_tracks_to_playlist as no tracks were matched in the example.")

    success_empty = client.add_tracks_to_playlist(youtube_playlist_id=new_playlist_id, youtube_track_ids=[])
    print(f"  Result for add_tracks_to_playlist (empty list): {'Successful' if success_empty else 'Failed (as expected)'}")

    print("\nYouTubeMusicClient stub example usage finished.")
