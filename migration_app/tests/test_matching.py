import unittest
from unittest import mock

from migration_app.matching.track_matcher import TrackMatcher, DEFAULT_FUZZY_MATCH_THRESHOLD, DEFAULT_DURATION_TOLERANCE_SECONDS, ISRC_MATCH_VALIDATION_THRESHOLD
from migration_app.migration.ytmusic_client import YouTubeMusicDataClient # For mocking its type

# --- Sample Data ---
SPOTIFY_SAMPLE_BASE = {
    'name': 'Test Song Title',
    'artists': [{'name': 'Test Artist Name'}],
    'album': {'name': 'Test Album Name'},
    'duration_ms': 180000, # 3 minutes
    'external_ids': {}
}

# YouTube Music search result structure (simplified from what ytmusic_client.search_track returns)
YT_RESULT_BASE = {
    'videoId': 'yt_video_id_123',
    'title': 'Test Song Title',
    'artists': [{'name': 'Test Artist Name', 'id': 'artist_id_1'}],
    'album': {'name': 'Test Album Name', 'id': 'album_id_1'},
    'duration': '3:00', # Matches SPOTIFY_SAMPLE_BASE
    'resultType': 'song',
    'match_score': 0, # Will be populated by matcher
    'duration_matched': False
}

class TestTrackMatcherHelpers(unittest.TestCase):
    def setUp(self):
        # No ytmusic_client needed for these helpers directly, but matcher instantiation needs it
        self.mock_yt_client = mock.Mock(spec=YouTubeMusicDataClient)
        self.matcher = TrackMatcher(self.mock_yt_client)

    def test_parse_duration_to_seconds(self):
        self.assertEqual(self.matcher._parse_duration_to_seconds("3:00"), 180)
        self.assertEqual(self.matcher._parse_duration_to_seconds("0:30"), 30)
        self.assertEqual(self.matcher._parse_duration_to_seconds("12:05"), 725)
        self.assertEqual(self.matcher._parse_duration_to_seconds("65"), 65) # Single number interpreted as seconds
        self.assertEqual(self.matcher._parse_duration_to_seconds("PT3M0S"), 180)
        self.assertEqual(self.matcher._parse_duration_to_seconds("PT30S"), 30)
        self.assertEqual(self.matcher._parse_duration_to_seconds("PT2M"), 120)
        self.assertIsNone(self.matcher._parse_duration_to_seconds("invalid"))
        self.assertIsNone(self.matcher._parse_duration_to_seconds(None))
        self.assertIsNone(self.matcher._parse_duration_to_seconds(""))
        self.assertIsNone(self.matcher._parse_duration_to_seconds("1:2:3")) # Not handled

    def test_validate_isrc_match(self):
        spotify_info = {'title': 'Match Title', 'artists_str': 'Match Artist'}

        # Strong match
        yt_match = {'title': 'Match Title', 'artists': [{'name': 'Match Artist'}]}
        self.assertTrue(self.matcher._validate_isrc_match(spotify_info, yt_match))

        # Weak title
        yt_weak_title = {'title': 'Different Title', 'artists': [{'name': 'Match Artist'}]}
        self.assertFalse(self.matcher._validate_isrc_match(spotify_info, yt_weak_title))

        # Weak artist
        yt_weak_artist = {'title': 'Match Title', 'artists': [{'name': 'Different Artist'}]}
        self.assertFalse(self.matcher._validate_isrc_match(spotify_info, yt_weak_artist))

        # Missing YT artist - relies on stricter title match
        yt_no_artist = {'title': 'Match Title', 'artists': []}
        self.assertTrue(self.matcher._validate_isrc_match(spotify_info, yt_no_artist)) # Assumes ISRC_MATCH_VALIDATION_THRESHOLD + 5 is met for title

        yt_no_artist_weak_title = {'title': 'Mutch Title', 'artists': []} # Slightly off title
        with mock.patch('migration_app.matching.track_matcher.ISRC_MATCH_VALIDATION_THRESHOLD', 80): # temp change threshold
             self.assertFalse(self.matcher._validate_isrc_match(spotify_info, yt_no_artist_weak_title))


class TestTrackMatcherMatchingLogic(unittest.TestCase):
    def setUp(self):
        self.mock_yt_client = mock.Mock(spec=YouTubeMusicDataClient)
        # Use default thresholds for most tests, can override by creating new matcher in test
        self.matcher = TrackMatcher(self.mock_yt_client)

    def test_match_track_empty_input(self):
        self.assertIsNone(self.matcher.match_track(None))
        self.assertIsNone(self.matcher.match_track({}))

    def test_isrc_match_success(self):
        spotify_track = {**SPOTIFY_SAMPLE_BASE, 'external_ids': {'isrc': 'TEST_ISRC_123'}}
        yt_result_isrc = {**YT_RESULT_BASE, 'title': 'Test Song Title ISRC VER'} # Slightly different to distinguish

        self.mock_yt_client.search_track.return_value = [yt_result_isrc] # Search by ISRC returns this

        # Mock _validate_isrc_match to control its outcome directly for this test
        with mock.patch.object(self.matcher, '_validate_isrc_match', return_value=True) as mock_validate:
            matched_track = self.matcher.match_track(spotify_track)
            self.mock_yt_client.search_track.assert_called_once_with(title='TEST_ISRC_123', limit=1)
            mock_validate.assert_called_once()
            self.assertEqual(matched_track, yt_result_isrc)

    def test_isrc_match_validation_fails_falls_to_fuzzy(self):
        spotify_track = {**SPOTIFY_SAMPLE_BASE, 'external_ids': {'isrc': 'TEST_ISRC_FAIL_VALID'}}
        yt_isrc_candidate = {**YT_RESULT_BASE, 'title': 'Very Different Title by ISRC'}

        # Fuzzy search should find this one
        yt_fuzzy_candidate = {**YT_RESULT_BASE, 'title': 'Test Song Title Fuzzy', 'match_score': DEFAULT_FUZZY_MATCH_THRESHOLD + 5, 'duration_matched': True}

        # ISRC search returns a candidate, then general search returns another
        self.mock_yt_client.search_track.side_effect = [
            [yt_isrc_candidate],  # Result for ISRC search
            [yt_fuzzy_candidate]  # Result for subsequent fuzzy search
        ]

        with mock.patch.object(self.matcher, '_validate_isrc_match', return_value=False) as mock_validate:
            # For fuzzy part to work as expected, mock its scoring to be high
            with mock.patch('migration_app.matching.track_matcher.fuzz.WRatio', side_effect=lambda s1, s2: 90 if "test song title" in s1.lower() and "test song title fuzzy" in s2.lower() else 70): # Ensure fuzzy wins
                matched_track = self.matcher.match_track(spotify_track)

                self.assertEqual(self.mock_yt_client.search_track.call_count, 2)
                self.mock_yt_client.search_track.assert_any_call(title='TEST_ISRC_FAIL_VALID', limit=1)
                self.mock_yt_client.search_track.assert_any_call(
                    title=spotify_track['name'],
                    artist=spotify_track['artists'][0]['name'],
                    album=spotify_track['album']['name'],
                    limit=5
                )
                mock_validate.assert_called_once() # ISRC validation was attempted
                self.assertEqual(matched_track, yt_fuzzy_candidate) # Should pick the fuzzy match

    def test_isrc_match_no_yt_result_falls_to_fuzzy(self):
        spotify_track = {**SPOTIFY_SAMPLE_BASE, 'external_ids': {'isrc': 'TEST_ISRC_NO_HIT'}}
        yt_fuzzy_candidate = {**YT_RESULT_BASE, 'title': 'Fuzzy Match When ISRC Misses', 'match_score': DEFAULT_FUZZY_MATCH_THRESHOLD + 2, 'duration_matched': True}

        self.mock_yt_client.search_track.side_effect = [
            [], # No result for ISRC search
            [yt_fuzzy_candidate] # Result for fuzzy search
        ]
        with mock.patch('migration_app.matching.track_matcher.fuzz.WRatio', return_value=90): # Make fuzzy high score
            matched_track = self.matcher.match_track(spotify_track)
            self.assertEqual(self.mock_yt_client.search_track.call_count, 2)
            self.assertEqual(matched_track, yt_fuzzy_candidate)

    def test_fuzzy_match_strong_match_selected(self):
        spotify_track = {**SPOTIFY_SAMPLE_BASE, 'name': 'Unique Song For Fuzzy Test'} # No ISRC

        candidate_good = {
            **YT_RESULT_BASE,
            'videoId': 'good_id', 'title': 'Unique Song For Fuzzy Test',
            'artists': [{'name': 'Test Artist Name'}], 'album': {'name': 'Test Album Name'},
            'duration': '3:00' # Perfect duration
        }
        candidate_ok = {
            **YT_RESULT_BASE,
            'videoId': 'ok_id', 'title': 'Unique Song For Fuzzy Test (Remix)', # Title slightly off
            'artists': [{'name': 'Test Artist Name'}], 'album': {'name': 'Test Album Name'},
            'duration': '3:05' # Duration close
        }
        self.mock_yt_client.search_track.return_value = [candidate_ok, candidate_good] # Good one is second

        matched_track = self.matcher.match_track(spotify_track)
        self.assertIsNotNone(matched_track)
        self.assertEqual(matched_track['videoId'], 'good_id')
        self.assertTrue(matched_track['match_score'] >= DEFAULT_FUZZY_MATCH_THRESHOLD)
        self.assertTrue(matched_track['duration_matched'])

    def test_fuzzy_match_score_below_threshold(self):
        spotify_track = {**SPOTIFY_SAMPLE_BASE, 'name': 'Obscure Track Name'}
        # All candidates will have low similarity scores
        candidate_low_score = {**YT_RESULT_BASE, 'title': 'Completely Different Name'}
        self.mock_yt_client.search_track.return_value = [candidate_low_score]

        # Mock fuzz.WRatio to ensure low scores
        with mock.patch('migration_app.matching.track_matcher.fuzz.WRatio', return_value=DEFAULT_FUZZY_MATCH_THRESHOLD - 10):
            matched_track = self.matcher.match_track(spotify_track)
            self.assertIsNone(matched_track)

    def test_fuzzy_match_duration_mismatch_impact(self):
        matcher_strict_duration = TrackMatcher(self.mock_yt_client, duration_tolerance_seconds=5)
        spotify_track = {**SPOTIFY_SAMPLE_BASE, 'name': 'Duration Test Song', 'duration_ms': 180000} # 3:00

        # Perfect text match, but duration significantly off
        candidate_duration_off = {
            **YT_RESULT_BASE, 'title': 'Duration Test Song',
            'duration': '3:30' # 210s, diff is 30s (outside 5s tolerance)
        }
        self.mock_yt_client.search_track.return_value = [candidate_duration_off]

        # With high textual similarity, it might still pass if bonus is small part of overall score
        # or if threshold is met even without bonus. Let's check 'duration_matched' flag.
        matched_track = matcher_strict_duration.match_track(spotify_track)
        self.assertIsNotNone(matched_track) # Assuming title/artist/album are perfect and overcome no bonus
        self.assertFalse(matched_track['duration_matched'])

        # Candidate with good duration
        candidate_duration_good = {
             **YT_RESULT_BASE, 'title': 'Duration Test Song',
             'duration': '3:04' # 184s, diff is 4s (within 5s tolerance)
        }
        self.mock_yt_client.search_track.return_value = [candidate_duration_good]
        matched_track_good_dur = matcher_strict_duration.match_track(spotify_track)
        self.assertIsNotNone(matched_track_good_dur)
        self.assertTrue(matched_track_good_dur['duration_matched'])
        # One could also check if the score of matched_track_good_dur is higher than matched_track if textual scores were same

    def test_fuzzy_match_no_search_results(self):
        spotify_track = SPOTIFY_SAMPLE_BASE
        self.mock_yt_client.search_track.return_value = [] # No fuzzy results
        matched_track = self.matcher.match_track(spotify_track)
        self.assertIsNone(matched_track)

if __name__ == '__main__':
    unittest.main()
