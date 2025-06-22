# migration_app/migration/playlist_migrator.py
import logging
from migration_app.migration.spotify_client import SpotifyDataClient
from migration_app.migration.ytmusic_client import YouTubeMusicDataClient
from migration_app.matching.track_matcher import TrackMatcher

logger = logging.getLogger(__name__)

def migrate_single_playlist(
    spotify_playlist_id: str,
    spotify_data_client: SpotifyDataClient,
    ytmusic_data_client: YouTubeMusicDataClient,
    track_matcher: TrackMatcher,
    playlist_name_prefix: str = "[Spotify Import] "
) -> dict:
    """
    Migrates a single Spotify playlist to YouTube Music.

    Args:
        spotify_playlist_id (str): The ID of the Spotify playlist to migrate.
        spotify_data_client (SpotifyDataClient): Authenticated client for Spotify data.
        ytmusic_data_client (YouTubeMusicDataClient): Authenticated client for YouTube Music.
        track_matcher (TrackMatcher): Instance of TrackMatcher for finding track equivalents.
        playlist_name_prefix (str): Prefix to add to the YouTube Music playlist name.

    Returns:
        dict: A summary of the migration attempt for this playlist, including
              status, tracks processed, tracks matched, and tracks added.
    """
    migration_summary = {
        "spotify_playlist_id": spotify_playlist_id,
        "status": "FAILED",
        "message": "",
        "yt_playlist_id": None,
        "tracks_processed": 0,
        "tracks_matched": 0,
        "tracks_added_to_yt": 0,
        "unmatched_spotify_tracks": [] # List of {name, artists_str} for unmatched tracks
    }

    try:
        # 1. Fetch Spotify playlist details and tracks
        # First, get playlist details (like name) - SpotifyDataClient might need a method for this
        # For now, assume we can get tracks and infer name from first track or a dedicated call.
        # Let's assume spotify_data_client needs a get_playlist_details method.
        # As a placeholder, we'll just use the ID for now if details are not easily fetched by current client.
        # Ideally:
        # spotify_playlist_details = spotify_data_client.get_playlist_details(spotify_playlist_id)
        # if not spotify_playlist_details:
        #     migration_summary["message"] = f"Failed to fetch Spotify playlist details for ID: {spotify_playlist_id}"
        #     logger.error(migration_summary["message"])
        #     return migration_summary
        # spotify_playlist_name = spotify_playlist_details.get('name', f"Spotify Playlist {spotify_playlist_id}")
        # spotify_playlist_description = spotify_playlist_details.get('description', "")

        logger.info(f"Starting migration for Spotify playlist ID: {spotify_playlist_id}")
        spotify_tracks = spotify_data_client.get_playlist_tracks(spotify_playlist_id)

        if not spotify_tracks:
            migration_summary["message"] = f"No tracks found in Spotify playlist ID: {spotify_playlist_id} or playlist is empty."
            logger.info(migration_summary["message"])
            migration_summary["status"] = "COMPLETED_EMPTY" # Or some other status
            return migration_summary

        migration_summary["tracks_processed"] = len(spotify_tracks)

        # For now, we don't have playlist name easily. Let's construct a generic one.
        # This needs to be improved by fetching actual Spotify playlist name.
        # For this iteration, we'll use a generic name or skip if no tracks.
        # Let's assume first track's album's playlist name if possible - this is a big assumption.
        # A proper get_playlist(playlist_id) method in SpotifyDataClient is needed.
        # Using a generic name for now:
        temp_spotify_playlist_name = f"Playlist {spotify_playlist_id}"
        # A better approach would be to add get_playlist() to SpotifyDataClient
        # For now, we will try to get it from the first track's context if available, or use ID.
        # This part is a known simplification for this step.
        # For the sake of current structure, we will assume a generic name based on ID.
        # Actual Spotify playlist name should be fetched.
        # Let's assume spotify_data_client.get_playlist(playlist_id) exists and returns {'name': '...', 'description': '...'}
        # We will mock this behavior or accept this limitation for now.
        # For the subtask, let's use a fixed name as a placeholder for the real name.

        # Attempt to get actual playlist name - this requires sp_sdk to be available on spotify_data_client or a new method
        # This is a conceptual improvement; the current SpotifyDataClient doesn't expose raw sp client.
        # We'll use a placeholder. A real app would ensure SpotifyDataClient can fetch this.
        try:
            # This is an ideal scenario if spotify_data_client.sp is the raw spotipy client
            # and is accessible. This is not guaranteed by SpotifyDataClient's current interface.
            # So this is more of a design note for improvement.
            playlist_details_raw = spotify_data_client.sp.playlist(spotify_playlist_id, fields="name,description")
            spotify_playlist_name_for_yt = playlist_details_raw.get('name', f"Spotify Playlist ({spotify_playlist_id})")
            spotify_playlist_description_for_yt = playlist_details_raw.get('description', f"Migrated from Spotify playlist {spotify_playlist_id}.")
        except Exception: # Catch if .sp is not available or other issues
            logger.warning(f"Could not fetch real Spotify playlist name for {spotify_playlist_id}. Using placeholder.")
            spotify_playlist_name_for_yt = f"Spotify Playlist ({spotify_playlist_id})" # Placeholder
            spotify_playlist_description_for_yt = f"Migrated from Spotify playlist {spotify_playlist_id}." # Placeholder


        # 2. Create a new playlist on YouTube Music
        yt_playlist_title = f"{playlist_name_prefix}{spotify_playlist_name_for_yt}"
        logger.info(f"Creating YouTube Music playlist: '{yt_playlist_title}'")

        yt_playlist_id = ytmusic_data_client.create_playlist(
            title=yt_playlist_title,
            description=spotify_playlist_description_for_yt
            # privacy_status can be passed if needed, default is PRIVATE
        )

        if not yt_playlist_id:
            migration_summary["message"] = f"Failed to create YouTube Music playlist for Spotify playlist: {spotify_playlist_id}"
            logger.error(migration_summary["message"])
            return migration_summary

        migration_summary["yt_playlist_id"] = yt_playlist_id
        logger.info(f"YouTube Music playlist created with ID: {yt_playlist_id} for Spotify playlist {spotify_playlist_id}")

        # 3. Match tracks and collect video IDs
        matched_yt_video_ids = []
        for i, sp_track in enumerate(spotify_tracks):
            track_name = sp_track.get('name', 'Unknown Track')
            track_artists_list = sp_track.get('artists', [])
            track_artists_str = ", ".join([a.get('name', 'N/A') for a in track_artists_list])

            logger.info(f"  Processing Spotify track ({i+1}/{len(spotify_tracks)}): '{track_name}' by {track_artists_str}")

            yt_matched_track = track_matcher.match_track(sp_track)

            if yt_matched_track and yt_matched_track.get('videoId'):
                logger.info(f"    -> MATCHED: '{yt_matched_track.get('title')}' (YT ID: {yt_matched_track.get('videoId')}, Score: {yt_matched_track.get('match_score', 'N/A')})")
                matched_yt_video_ids.append(yt_matched_track['videoId'])
                migration_summary["tracks_matched"] += 1
            else:
                logger.info(f"    -> NOT MATCHED: '{track_name}' by {track_artists_str}")
                migration_summary["unmatched_spotify_tracks"].append({
                    "name": track_name,
                    "artists": track_artists_str,
                    "spotify_id": sp_track.get("id") # If available
                })

        # 4. Add matched tracks to the new YouTube Music playlist
        if matched_yt_video_ids:
            logger.info(f"Adding {len(matched_yt_video_ids)} matched tracks to YouTube Music playlist: {yt_playlist_id}")
            add_success = ytmusic_data_client.add_tracks_to_playlist(yt_playlist_id, matched_yt_video_ids)
            if add_success:
                logger.info("Successfully added tracks to YouTube Music playlist.")
                migration_summary["tracks_added_to_yt"] = len(matched_yt_video_ids) # Assuming all were added if API call succeeded
                migration_summary["status"] = "COMPLETED_SUCCESS"
                migration_summary["message"] = f"Playlist migrated. {migration_summary['tracks_matched']}/{migration_summary['tracks_processed']} tracks matched. {migration_summary['tracks_added_to_yt']} tracks added to YT."
            else:
                migration_summary["message"] = f"Failed to add some/all matched tracks to YouTube Music playlist {yt_playlist_id}."
                migration_summary["status"] = "COMPLETED_PARTIAL_FAILURE" # Partial because creation and matching might have occurred
                logger.error(migration_summary["message"])
        elif migration_summary["tracks_matched"] == 0 and migration_summary["tracks_processed"] > 0 :
             migration_summary["status"] = "COMPLETED_NO_MATCHES"
             migration_summary["message"] = "Playlist processed, but no tracks were matched."
             logger.info(migration_summary["message"])
        else: # No tracks processed or no tracks matched (already covered)
            migration_summary["status"] = "COMPLETED_SUCCESS" # Or some other status if no tracks to add
            migration_summary["message"] = "Playlist processed. No tracks to add to YouTube Music."
            logger.info(migration_summary["message"])

    except Exception as e:
        migration_summary["message"] = f"An unexpected error occurred during migration of playlist {spotify_playlist_id}: {e}"
        logger.error(migration_summary["message"], exc_info=True)
        # Status remains "FAILED"

    logger.info(f"Migration summary for Spotify playlist {spotify_playlist_id}: {migration_summary}")
    return migration_summary


# Example Usage (for testing - requires significant setup)
if __name__ == '__main__':
    from migration_app.auth.spotify_auth import SpotifyAuthenticator
    from migration_app.auth.ytmusic_auth import YouTubeMusicAuthenticator
    import os

    logging.basicConfig(level=logging.INFO)
    # For more detailed logs from matcher etc:
    # logging.getLogger("migration_app.matching.track_matcher").setLevel(logging.DEBUG)
    # logging.getLogger("migration_app.migration.spotify_client").setLevel(logging.DEBUG)
    # logging.getLogger("migration_app.migration.ytmusic_client").setLevel(logging.DEBUG)


    # --- Configuration - NEEDS ACTUAL CREDENTIALS AND A REAL PLAYLIST ID ---
    # Spotify Credentials (ensure these are set as environment variables)
    SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
    SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
    SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')

    # Target Spotify Playlist ID to migrate (replace with a real one you own/can access)
    # Example: A small playlist for testing is recommended.
    TARGET_SPOTIFY_PLAYLIST_ID = os.getenv('TEST_SPOTIFY_PLAYLIST_ID', "YOUR_TEST_PLAYLIST_ID_HERE") # e.g., "37i9dQZF1DXcBWIGoYBM5M" (Spotify's "Today's Top Hits")

    if not all([SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI]) or TARGET_SPOTIFY_PLAYLIST_ID == "YOUR_TEST_PLAYLIST_ID_HERE":
        logger.error("Please set SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, and TEST_SPOTIFY_PLAYLIST_ID environment variables to run the example.")
    else:
        try:
            logger.info("--- Authenticating Spotify ---")
            sp_auth = SpotifyAuthenticator(SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI)
            sp_sdk = sp_auth.get_spotify_client()
            spotify_client = SpotifyDataClient(sp_sdk)
            logger.info("Spotify authenticated.")

            logger.info("--- Authenticating YouTube Music (requires headers_auth.json) ---")
            yt_auth = YouTubeMusicAuthenticator()
            ytm_sdk = yt_auth.get_ytmusic_client()
            ytmusic_client = YouTubeMusicDataClient(ytm_sdk)
            logger.info("YouTube Music authenticated.")

            logger.info("--- Initializing TrackMatcher ---")
            matcher = TrackMatcher(ytmusic_data_client=ytmusic_client)

            logger.info(f"--- Starting Migration for Spotify Playlist ID: {TARGET_SPOTIFY_PLAYLIST_ID} ---")

            # Before running, ensure SpotifyDataClient has a method like get_playlist_details(playlist_id)
            # or modify the placeholder for spotify_playlist_name_for_yt and description.
            # For this example, we'll proceed with the placeholder names.
            # A real implementation should fetch these details from Spotify.

            # It's highly recommended to add a get_playlist method to SpotifyDataClient
            # that returns {'name': 'playlist_name', 'description': 'playlist_description'}
            # For now, the migrator uses a placeholder name.

            # Example: Add a dummy get_playlist_details to the client for the test to run
            # The attempt to fetch real playlist name is now inside migrate_single_playlist,
            # assuming spotify_data_client.sp is accessible.

            summary = migrate_single_playlist(
                spotify_playlist_id=TARGET_SPOTIFY_PLAYLIST_ID,
                spotify_data_client=spotify_client,
                ytmusic_data_client=ytmusic_client,
                track_matcher=matcher
            )

            logger.info(f"--- Migration Attempt Finished for {TARGET_SPOTIFY_PLAYLIST_ID} ---")
            logger.info(f"Status: {summary.get('status')}")
            logger.info(f"Message: {summary.get('message')}")
            logger.info(f"YouTube Playlist ID: {summary.get('yt_playlist_id')}")
            logger.info(f"Tracks Processed: {summary.get('tracks_processed')}")
            logger.info(f"Tracks Matched: {summary.get('tracks_matched')}")
            logger.info(f"Tracks Added to YT: {summary.get('tracks_added_to_yt')}")
            if summary.get("unmatched_spotify_tracks"):
                logger.info("Unmatched Spotify Tracks:")
                for i, track_info in enumerate(summary["unmatched_spotify_tracks"][:5]): # Log first 5
                    logger.info(f"  {i+1}. {track_info['name']} by {track_info['artists']} (ID: {track_info.get('spotify_id', 'N/A')})")
                if len(summary["unmatched_spotify_tracks"]) > 5:
                    logger.info(f"  ...and {len(summary['unmatched_spotify_tracks']) - 5} more unmatched tracks.")


        except Exception as e:
            logger.error(f"An error occurred in the playlist migration example: {e}", exc_info=True)
