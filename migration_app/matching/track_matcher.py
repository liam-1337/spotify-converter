from fuzzywuzzy import fuzz # For string matching
# from ytmusicapi import YTMusic # Will be needed by methods that call YTM search
# from migration_app.migration.ytmusic_client import YouTubeMusicDataClient # Might be passed or instantiated

import logging

logger = logging.getLogger(__name__)

# Define a threshold for a 'good enough' fuzzy match score (0-100)
# This will likely need tuning.
DEFAULT_FUZZY_MATCH_THRESHOLD = 85
# Define a threshold for duration difference in seconds
DEFAULT_DURATION_TOLERANCE_SECONDS = 10
# Threshold for ISRC match validation (title and artist similarity)
ISRC_MATCH_VALIDATION_THRESHOLD = 75
# Weightings for fuzzy match scoring
WEIGHT_TITLE = 0.45
WEIGHT_ARTIST = 0.35
WEIGHT_ALBUM = 0.10
WEIGHT_DURATION_MATCH_BONUS = 0.10 # Bonus points if duration matches

class TrackMatcher:
    def __init__(self, ytmusic_data_client,
                 fuzzy_match_threshold: int = DEFAULT_FUZZY_MATCH_THRESHOLD,
                 duration_tolerance_seconds: int = DEFAULT_DURATION_TOLERANCE_SECONDS):
        self.ytmusic_client = ytmusic_data_client
        self.fuzzy_match_threshold = fuzzy_match_threshold
        self.duration_tolerance_seconds = duration_tolerance_seconds
        # ISRC data from Spotify is usually in track['external_ids']['isrc']

    def _parse_duration_to_seconds(self, duration_str: str) -> int | None:
        # ... (existing _parse_duration_to_seconds method - keep as is)
        if not duration_str: return None
        if duration_str.startswith("PT"):
            try:
                duration_str = duration_str.replace("PT", "")
                minutes, seconds = 0, 0
                if "M" in duration_str:
                    parts = duration_str.split("M")
                    minutes = int(parts[0])
                    if len(parts) > 1 and parts[1]:
                        seconds_part = parts[1].replace("S", "")
                        if seconds_part: seconds = int(seconds_part)
                elif "S" in duration_str:
                    seconds = int(duration_str.replace("S", ""))
                return minutes * 60 + seconds
            except ValueError:
                logger.debug(f"Could not parse ISO duration string: {duration_str}")
                return None
        parts = duration_str.split(':')
        try:
            if len(parts) == 2: return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 1: return int(parts[0])
            else: return None
        except ValueError:
            logger.debug(f"Could not parse duration string: {duration_str}")
            return None

    def _validate_isrc_match(self, spotify_track_info: dict, yt_track_info: dict) -> bool:
        # ... (existing _validate_isrc_match method - keep as is)
        spotify_title = spotify_track_info.get('title', '').lower()
        spotify_artists_str = spotify_track_info.get('artists_str', '').lower()
        yt_title = yt_track_info.get('title', '').lower()
        yt_artists = yt_track_info.get('artists', [])
        yt_artists_str = ""
        if yt_artists:
            yt_artists_str = ", ".join([a['name'] for a in yt_artists if a and 'name' in a]).lower()
        title_similarity = fuzz.ratio(spotify_title, yt_title)
        artist_similarity = fuzz.ratio(spotify_artists_str, yt_artists_str)
        logger.debug(f"ISRC Valid: Spot='{spotify_title} - {spotify_artists_str}', YT='{yt_title} - {yt_artists_str}' -> Title: {title_similarity}, Artist: {artist_similarity}")
        if spotify_artists_str and yt_artists_str:
            return (title_similarity >= ISRC_MATCH_VALIDATION_THRESHOLD and
                    artist_similarity >= ISRC_MATCH_VALIDATION_THRESHOLD)
        else:
            return title_similarity >= ISRC_MATCH_VALIDATION_THRESHOLD + 5

    def match_track(self, spotify_track: dict) -> dict | None:
        if not spotify_track:
            logger.warning("Received empty Spotify track data for matching.")
            return None

        spotify_title = spotify_track.get('name', '')
        spotify_artists_list = spotify_track.get('artists', [])
        spotify_artist_names_str = ", ".join([artist['name'] for artist in spotify_artists_list if artist.get('name')])
        spotify_album_obj = spotify_track.get('album')
        spotify_album_name = ""
        if spotify_album_obj and isinstance(spotify_album_obj, dict):
            spotify_album_name = spotify_album_obj.get('name', '')
        spotify_duration_ms = spotify_track.get('duration_ms')
        spotify_isrc = spotify_track.get('external_ids', {}).get('isrc')

        logger.info(f"Attempting to match Spotify track: '{spotify_title}' by {spotify_artist_names_str} (Album: {spotify_album_name or 'N/A'}, ISRC: {spotify_isrc or 'N/A'})")

        # Strategy 1: ISRC Matching
        if spotify_isrc:
            logger.info(f"Attempting ISRC match for '{spotify_isrc}'...")
            isrc_search_results = self.ytmusic_client.search_track(title=spotify_isrc, limit=1)
            if isrc_search_results:
                yt_track_candidate = isrc_search_results[0]
                logger.info(f"Found potential ISRC match: {yt_track_candidate.get('title')} (Video ID: {yt_track_candidate.get('videoId')})")
                spotify_info_for_validation = {'title': spotify_title, 'artists_str': spotify_artist_names_str}
                if self._validate_isrc_match(spotify_info_for_validation, yt_track_candidate):
                    logger.info(f"ISRC match VALIDATED for '{spotify_title}'. Matched to YT track '{yt_track_candidate.get('title')}'.")
                    return yt_track_candidate
                else:
                    logger.warning(f"ISRC match for '{spotify_title}' found but FAILED validation against YT track '{yt_track_candidate.get('title')}'.")
            else:
                logger.info(f"No direct match found using ISRC '{spotify_isrc}'.")

        # Strategy 2: Fuzzy String Matching based on general search
        logger.info(f"Proceeding to fuzzy matching for '{spotify_title}' by {spotify_artist_names_str}...")
        # Use primary artist for a slightly broader initial search if too many artists.
        primary_spotify_artist = spotify_artist_names_str.split(',')[0].strip() if spotify_artist_names_str else ""

        potential_matches = self.ytmusic_client.search_track(
            title=spotify_title,
            artist=primary_spotify_artist,
            album=spotify_album_name, # Include album in search query
            limit=5 # Get a few candidates to score
        )

        if not potential_matches:
            logger.info(f"No potential matches found on YouTube Music for '{spotify_title}' by {spotify_artist_names_str} via general search.")
            return None

        best_match = None
        highest_score = 0.0

        spotify_duration_s = (spotify_duration_ms // 1000) if spotify_duration_ms is not None else None

        for yt_candidate in potential_matches:
            yt_title = yt_candidate.get('title', '')
            yt_artists_list = yt_candidate.get('artists', [])
            yt_artist_names_str = ", ".join([a['name'] for a in yt_artists_list if a and 'name' in a])
            yt_album_name = ""
            if yt_candidate.get('album') and isinstance(yt_candidate['album'], dict):
                 yt_album_name = yt_candidate['album'].get('name', '')
            yt_duration_s = self._parse_duration_to_seconds(yt_candidate.get('duration'))

            title_score = fuzz.WRatio(spotify_title.lower(), yt_title.lower())
            artist_score = fuzz.WRatio(spotify_artist_names_str.lower(), yt_artist_names_str.lower()) if spotify_artist_names_str and yt_artist_names_str else (100 if not spotify_artist_names_str and not yt_artist_names_str else 50) # Penalize if one has artist and other doesn't heavily

            album_score = 75 # Neutral score if album info is missing on one side
            if spotify_album_name and yt_album_name:
                album_score = fuzz.WRatio(spotify_album_name.lower(), yt_album_name.lower())
            elif not spotify_album_name and not yt_album_name: # Both no album is fine
                album_score = 100

            duration_bonus = 0.0
            duration_match_info = "N/A"
            if spotify_duration_s is not None and yt_duration_s is not None:
                if abs(spotify_duration_s - yt_duration_s) <= self.duration_tolerance_seconds:
                    duration_bonus = WEIGHT_DURATION_MATCH_BONUS * 100 # Add bonus score as points
                    duration_match_info = f"MATCH (Diff: {abs(spotify_duration_s - yt_duration_s)}s)"
                else:
                    duration_match_info = f"NO MATCH (Diff: {abs(spotify_duration_s - yt_duration_s)}s)"

            current_score = (title_score * WEIGHT_TITLE +
                             artist_score * WEIGHT_ARTIST +
                             album_score * WEIGHT_ALBUM +
                             duration_bonus) # duration_bonus is added, not weighted into 100

            logger.debug(
                f"Candidate: '{yt_title}' by '{yt_artist_names_str}' (Album: '{yt_album_name}')
"
                f"  Scores: Title={title_score}(w:{WEIGHT_TITLE}), Artist={artist_score}(w:{WEIGHT_ARTIST}), Album={album_score}(w:{WEIGHT_ALBUM})
"
                f"  Duration: Spotify='{spotify_duration_s}s', YT='{yt_duration_s}s' -> Bonus={duration_bonus:.2f} ({duration_match_info})
"
                f"  Calculated Score: {current_score:.2f}"
            )

            if current_score > highest_score:
                highest_score = current_score
                best_match = yt_candidate
                # Attach score for logging or further decision making if needed
                best_match['match_score'] = current_score
                best_match['duration_matched'] = (duration_bonus > 0)

        if best_match and highest_score >= self.fuzzy_match_threshold:
            # Additional check: if scores are high, a duration match makes it more confident
            # If scores are high but duration is way off, maybe be more skeptical?
            # For now, threshold is primary. Duration match is a bonus in score.
            logger.info(
                f"Best fuzzy match for '{spotify_title}': '{best_match.get('title')}' "
                f"with score {highest_score:.2f} (Threshold: {self.fuzzy_match_threshold}). "
                f"Duration matched: {best_match.get('duration_matched')}"
            )
            return best_match

        logger.info(f"No fuzzy match found above threshold for '{spotify_title}'. Highest score: {highest_score:.2f} (Threshold: {self.fuzzy_match_threshold})")
        return None

# ... (keep existing if __name__ == '__main__' block, it will now use the new fuzzy matching)
# Example Usage (for testing)
if __name__ == '__main__':
    from migration_app.migration.ytmusic_client import YouTubeMusicDataClient # For example
    from migration_app.auth.ytmusic_auth import YouTubeMusicAuthenticator # For example

    # Configure basic logging for the example
    # To see detailed scoring, set level to DEBUG for the matcher's logger or globally
    logging.basicConfig(level=logging.INFO)
    # logging.getLogger("migration_app.matching.track_matcher").setLevel(logging.DEBUG)


    # This example requires YouTube Music authentication to be set up
    try:
        logger.info("Setting up YouTubeMusicAuthenticator for TrackMatcher example...")
        yt_auth = YouTubeMusicAuthenticator()
        ytm_sdk_instance = yt_auth.get_ytmusic_client()
        yt_data_client = YouTubeMusicDataClient(ytm_sdk_instance)

        # Test with a higher threshold to see more rejections, or lower for more matches
        matcher = TrackMatcher(ytmusic_data_client=yt_data_client, fuzzy_match_threshold=80, duration_tolerance_seconds=15)

        # Example Spotify track data (simplified)
        sample_spotify_track_isrc = {
            'name': 'Mr. Brightside',
            'artists': [{'name': 'The Killers'}],
            'album': {'name': 'Hot Fuss'},
            'duration_ms': 222000,
            'external_ids': {'isrc': 'USIR20400255'}
        }

        logger.info(f"\nAttempting to match with ISRC: '{sample_spotify_track_isrc['name']}' by {sample_spotify_track_isrc['artists'][0]['name']}")
        matched_track_isrc = matcher.match_track(sample_spotify_track_isrc)
        if matched_track_isrc:
            logger.info(f"ISRC_FLOW_RESULT: Match found for '{sample_spotify_track_isrc['name']}': '{matched_track_isrc.get('title')}' (Score: {matched_track_isrc.get('match_score', 'N/A')})")
        else:
            logger.info(f"ISRC_FLOW_RESULT: No match found for '{sample_spotify_track_isrc['name']}'.")


        sample_spotify_track_fuzzy = {
            'name': 'Wonderwall',
            'artists': [{'name': 'Oasis'}],
            'album': {'name': "(What's the Story) Morning Glory?"},
            'duration_ms': 258000,
            'external_ids': {} # No ISRC
        }

        logger.info(f"\nAttempting to match with fuzzy: '{sample_spotify_track_fuzzy['name']}' by {sample_spotify_track_fuzzy['artists'][0]['name']}")
        matched_track_fuzzy = matcher.match_track(sample_spotify_track_fuzzy)
        if matched_track_fuzzy:
            logger.info(f"FUZZY_FLOW_RESULT: Match found for '{sample_spotify_track_fuzzy['name']}': '{matched_track_fuzzy.get('title')}' (Score: {matched_track_fuzzy.get('match_score', 'N/A')})")
        else:
            logger.info(f"FUZZY_FLOW_RESULT: No match found for '{sample_spotify_track_fuzzy['name']}'.")

        sample_spotify_track_difficult = {
            'name': 'Smells Like Teen Spirit',
            'artists': [{'name': 'Nirvana'}],
            'album': {'name': 'Nevermind'},
            'duration_ms': 301000, # approx 5m 1s
            'external_ids': {}
        }
        logger.info(f"\nAttempting to match (potentially difficult): '{sample_spotify_track_difficult['name']}' by {sample_spotify_track_difficult['artists'][0]['name']}")
        matched_track_difficult = matcher.match_track(sample_spotify_track_difficult)
        if matched_track_difficult:
            logger.info(f"DIFFICULT_FLOW_RESULT: Match for '{sample_spotify_track_difficult['name']}': '{matched_track_difficult.get('title')}' (Score: {matched_track_difficult.get('match_score', 'N/A')})")
        else:
            logger.info(f"DIFFICULT_FLOW_RESULT: No match for '{sample_spotify_track_difficult['name']}'.")


    except Exception as e:
        logger.error(f"Error in TrackMatcher example: {e}", exc_info=True)
