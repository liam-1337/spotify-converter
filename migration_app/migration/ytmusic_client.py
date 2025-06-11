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

# Example Usage (for testing - would be integrated into CLI later)
if __name__ == '__main__':
    from migration_app.auth.ytmusic_auth import YouTubeMusicAuthenticator, YouTubeMusicAuthError
    import os

    # This requires headers_auth.json to be set up
    # Run `python -m ytmusicapi setup` first if you haven't.

    logging.basicConfig(level=logging.INFO)

    try:
        print("Authenticating with YouTube Music...")
        yt_auth = YouTubeMusicAuthenticator()
        ytm_instance = yt_auth.get_ytmusic_client()
        print("Authenticated successfully.")

        yt_data_client = YouTubeMusicDataClient(ytm_instance)

        print("\nSearching for a track 'Bohemian Rhapsody by Queen'...")
        results = yt_data_client.search_track(title="Bohemian Rhapsody", artist="Queen", limit=3)
        if results:
            print(f"Found {len(results)} results:")
            for i, track in enumerate(results):
                print(f"  {i+1}. Title: {track['title']}")
                if track.get('artists'):
                    print(f"     Artists: {', '.join([a['name'] for a in track['artists']])}")
                print(f"     Video ID: {track['videoId']}, Type: {track['resultType']}, Duration: {track['duration']}")
        else:
            print("No results found.")

        print("\nSearching for a track 'Watermelon Sugar' (no artist)...")
        results_no_artist = yt_data_client.search_track(title="Watermelon Sugar", limit=2)
        if results_no_artist:
            print(f"Found {len(results_no_artist)} results:")
            for i, track in enumerate(results_no_artist):
                print(f"  {i+1}. Title: {track['title']}")
                if track.get('artists'):
                     print(f"     Artists: {', '.join([a['name'] for a in track['artists']])}")
                print(f"     Video ID: {track['videoId']}, Type: {track['resultType']}, Duration: {track['duration']}")
        else:
            print("No results found.")

    except YouTubeMusicAuthError as e:
        logger.error(f"YouTube Music authentication error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
