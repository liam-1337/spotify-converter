from ytmusicapi import YTMusic
import logging

# Configure logging for this module
logger = logging.getLogger(__name__)

class YouTubeMusicDataClient:
    def __init__(self, ytmusic_client: YTMusic):
        if not isinstance(ytmusic_client, YTMusic):
            raise ValueError("A valid ytmusicapi.YTMusic client instance is required.")
        self.ytm = ytmusic_client

    def search_track(self, title: str, artist: str = None, album: str = None, limit: int = 5) -> list[dict]:
        """
        Searches for a track on YouTube Music.
        Constructs a query string from title, artist, and album if provided.

        Args:
            title (str): The title of the track.
            artist (str, optional): The artist of the track. Defaults to None.
            album (str, optional): The album of the track. Defaults to None.
            limit (int, optional): The maximum number of search results to return. Defaults to 5.

        Returns:
            list[dict]: A list of search result dictionaries from ytmusicapi,
                        filtered for songs/videos. Returns empty list on error or no results.
        """
        query_parts = [title]
        if artist:
            query_parts.append(artist)
        if album:
            query_parts.append(album)

        query = " ".join(query_parts)

        try:
            logger.info(f"Searching YouTube Music for: '{query}' with limit {limit}")
            # ytmusicapi search results can include songs, videos, albums, artists, playlists.
            # We are primarily interested in songs or videos that can be added to playlists.
            search_results = self.ytm.search(query=query, filter=None, limit=limit) # Filter later

            # Filter for items that are likely playable tracks (songs or videos)
            # 'category' might indicate 'Songs', 'Videos', 'Albums', etc.
            # 'resultType' can be 'song', 'video', 'album', 'artist', 'playlist'.
            # We want items that have a 'videoId'.

            relevant_results = []
            if search_results:
                for result in search_results:
                    if result.get('videoId') and result.get('resultType') in ['song', 'video']:
                        # Add more details if needed, like duration
                        track_info = {
                            'videoId': result.get('videoId'),
                            'title': result.get('title'),
                            'artists': result.get('artists'), # List of artists [{name, id}]
                            'album': result.get('album'),   # Album {name, id}
                            'duration': result.get('duration'), # Duration string like "3:45"
                            'resultType': result.get('resultType') # 'song' or 'video'
                        }
                        relevant_results.append(track_info)

            logger.info(f"Found {len(relevant_results)} relevant tracks for query '{query}'.")
            return relevant_results
        except Exception as e:
            logger.error(f"Error searching YouTube Music for '{query}': {e}", exc_info=True)
            return []

    def create_playlist(self, title: str, description: str = "", privacy_status: str = "PRIVATE") -> str | None:
        """
        Creates a new playlist on YouTube Music.

        Args:
            title (str): The title of the new playlist.
            description (str, optional): Description for the playlist. Defaults to "".
            privacy_status (str, optional): Privacy status ("PRIVATE", "PUBLIC", "UNLISTED"). Defaults to "PRIVATE".

        Returns:
            str | None: The ID of the newly created playlist if successful, otherwise None.
        """
        try:
            logger.info(f"Creating YouTube Music playlist: Title='{title}', Privacy='{privacy_status}'")
            playlist_id = self.ytm.create_playlist(
                title=title,
                description=description,
                privacy_status=privacy_status
            )
            if playlist_id:
                logger.info(f"Successfully created playlist '{title}' with ID: {playlist_id}")
                return playlist_id
            else:
                # This case might indicate an issue with ytmusicapi's return or a silent failure
                logger.warning(f"Playlist creation for '{title}' returned a falsy ID: {playlist_id}. Assuming failure.")
                return None
        except Exception as e:
            logger.error(f"Error creating YouTube Music playlist '{title}': {e}", exc_info=True)
            return None

    def add_tracks_to_playlist(self, playlist_id: str, video_ids: list[str]) -> bool:
        """
        Adds tracks to an existing YouTube Music playlist.

        Args:
            playlist_id (str): The ID of the playlist to add tracks to.
            video_ids (list[str]): A list of video IDs for the tracks to be added.

        Returns:
            bool: True if tracks were added successfully (or at least no errors reported), False otherwise.
        """
        if not video_ids:
            logger.info(f"No video IDs provided to add to playlist {playlist_id}.")
            return True # No action needed, considered success

        try:
            logger.info(f"Adding {len(video_ids)} tracks to YouTube Music playlist ID: {playlist_id}")
            response = self.ytm.add_playlist_items(playlistId=playlist_id, videoIds=video_ids)

            # Response structure for add_playlist_items:
            # {'status': 'SUCCEEDED', 'actions': [...], 'playlistEditResults': [...]}
            # If 'status' is 'SUCCEEDED' and 'actions' list is not empty, it's generally a success.
            # Individual actions can also have statuses, but ytmusicapi usually raises on failure.
            if response and response.get('status') == 'SUCCEEDED' and response.get('actions'):
                logger.info(f"Successfully added {len(video_ids)} tracks to playlist {playlist_id}. Response status: {response.get('status')}")
                # Could further inspect response['actions'][0]['addToToastAction']['item']['notificationActionRenderer']['responseText'] for "Song added"
                return True
            elif response: # Response received but not clearly success
                logger.warning(f"Adding tracks to playlist {playlist_id} resulted in an ambiguous response: {response}")
                return False # Or True depending on how strict we want to be. Let's be strict.
            else: # No response or falsy response
                logger.error(f"Failed to add tracks to playlist {playlist_id}. No valid response from API.")
                return False
        except Exception as e:
            logger.error(f"Error adding tracks to YouTube Music playlist {playlist_id}: {e}", exc_info=True)
            return False

# Example Usage (for testing - would be integrated into CLI later)
if __name__ == '__main__':
    from migration_app.auth.ytmusic_auth import YouTubeMusicAuthenticator, YouTubeMusicAuthError
    import time # For unique playlist names

    logging.basicConfig(level=logging.INFO)

    try:
        logger.info("Authenticating with YouTube Music for client examples...")
        yt_auth = YouTubeMusicAuthenticator()
        ytm_sdk_instance = yt_auth.get_ytmusic_client()
        logger.info("Authenticated successfully.")

        yt_data_client = YouTubeMusicDataClient(ytm_sdk_instance)

        # --- Test search_track (existing) ---
        logger.info("\nSearching for 'Bohemian Rhapsody by Queen'...")
        search_results = yt_data_client.search_track(title="Bohemian Rhapsody", artist="Queen", limit=2)
        if search_results:
            logger.info(f"Found {len(search_results)} results for 'Bohemian Rhapsody':")
            for i, track in enumerate(search_results):
                logger.info(f"  {i+1}. Title: {track['title']}, Video ID: {track['videoId']}")
        else:
            logger.info("No results found for 'Bohemian Rhapsody'.")

        video_ids_to_add = [res['videoId'] for res in search_results if res.get('videoId')]

        # --- Test create_playlist ---
        # Use a timestamp to make playlist names unique for testing to avoid conflicts
        timestamp = int(time.time())
        test_playlist_title = f"Test Migration Playlist {timestamp}"
        logger.info(f"\nAttempting to create playlist: {test_playlist_title}")

        new_playlist_id = yt_data_client.create_playlist(
            title=test_playlist_title,
            description="A test playlist created by the migration app example.",
            privacy_status="PRIVATE" # Or "PUBLIC" to easily verify on YT Music
        )

        if new_playlist_id:
            logger.info(f"Playlist '{test_playlist_title}' created successfully with ID: {new_playlist_id}")

            # --- Test add_tracks_to_playlist ---
            if video_ids_to_add:
                logger.info(f"\nAttempting to add {len(video_ids_to_add)} tracks to playlist ID {new_playlist_id}...")
                add_success = yt_data_client.add_tracks_to_playlist(new_playlist_id, video_ids_to_add)
                if add_success:
                    logger.info("Tracks added to the playlist successfully (according to API response).")
                else:
                    logger.error("Failed to add tracks to the playlist.")
            else:
                logger.info("\nNo tracks found from search to add to the playlist.")

            # Note: To fully verify, one might want to delete the playlist afterwards.
            # ytmusicapi has delete_playlist(playlist_id). This is not added to client yet.
            # For manual testing, you'd check your YouTube Music account.
            # Example:
            # try:
            #     logger.info(f"Attempting to delete test playlist {new_playlist_id}...")
            #     delete_status = ytm_sdk_instance.delete_playlist(new_playlist_id)
            #     logger.info(f"Deletion status for playlist {new_playlist_id}: {delete_status}")
            # except Exception as del_e:
            #     logger.error(f"Error deleting playlist {new_playlist_id}: {del_e}")

        else:
            logger.error(f"Failed to create playlist '{test_playlist_title}'.")

    except YouTubeMusicAuthError as e:
        logger.error(f"YouTube Music authentication error in example: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred in example: {e}", exc_info=True)
