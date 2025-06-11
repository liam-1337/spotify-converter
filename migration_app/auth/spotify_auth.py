import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import json

# Define a cache path for the token info
# Ideally, this should be in a more secure location or use a proper secrets manager
TOKEN_CACHE_PATH = '.spotify_token_cache.json'

# Custom exception for Spotify authentication errors
class SpotifyAuthError(Exception):
    pass

class SpotifyAuthenticator:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, scope: str = 'user-library-read playlist-read-private user-follow-read user-top-read'):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scope = scope
        self.sp_oauth = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope,
            cache_path=TOKEN_CACHE_PATH,
            show_dialog=True # Show dialog to the user every time
        )

    def get_cached_token(self):
        """Gets the cached token info if available."""
        token_info = None
        if os.path.exists(TOKEN_CACHE_PATH):
            with open(TOKEN_CACHE_PATH, 'r') as f:
                try:
                    token_info = json.load(f)
                except json.JSONDecodeError:
                    # Cache file is corrupted, proceed as if no cache
                    pass
        return token_info

    def get_spotify_client(self) -> spotipy.Spotify:
        """
        Authenticates the user and returns a Spotify client.
        Handles token caching and refreshing.
        """
        token_info = self.get_cached_token()

        if not token_info:
            # No token, or cache was invalid - start auth flow
            # The actual auth URL generation and handling the response
            # will require user interaction (copy-pasting URL/code).
            # This part will be expanded in the CLI.
            # For now, we rely on spotipy's built-in caching or prompt.
            print(f"No cached token found. Attempting to get a new token using spotipy's default mechanism.")
            print(f"Please follow the instructions to authenticate with Spotify.")
            print(f"You might need to open a URL in your browser and paste the redirected URL back.")

        # Spotipy will handle refreshing if token_info is passed and expired,
        # or prompt for new auth if no token_info or it's invalid.
        try:
            # Re-initialize SpotifyOAuth with potentially loaded token_info
            # to ensure it tries to use it or refresh it.
            # Spotipy's cache_path mechanism handles most of this automatically
            # if we just call get_access_token without a code.

            # Try to get a token. If cache exists and is valid, it's used.
            # If cache exists but token is expired, it's refreshed.
            # If cache doesn't exist or is invalid, spotipy prompts for auth.
            token_info = self.sp_oauth.get_access_token(check_cache=True)

            if not token_info:
                # This case should ideally be handled by spotipy raising an error
                # or by the user being prompted.
                # If get_access_token returns None without error/prompt, something is wrong.
                auth_url = self.sp_oauth.get_authorize_url()
                print(f"Please authorize here: {auth_url}")
                response_url = input("Enter the URL you were redirected to: ")
                code = self.sp_oauth.parse_response_code(response_url)
                if not code:
                    raise SpotifyAuthError("Could not parse authorization code from the response URL.")

                token_info = self.sp_oauth.get_access_token(code, check_cache=False)
                if not token_info:
                     raise SpotifyAuthError("Failed to get token even after providing authorization code.")


            # Save the token info manually as well, to be sure, though spotipy handles it with cache_path
            # self.sp_oauth.cache_handler.save_token_to_cache(token_info) # spotipy >= 2.22.0
            # For older spotipy, cache_path in constructor is enough for file cache

            return spotipy.Spotify(auth=token_info['access_token'])

        except spotipy.SpotifyException as e:
            raise SpotifyAuthError(f"Spotify authentication failed: {e}")
        except Exception as e:
            # Catch any other unexpected errors during the auth process
            raise SpotifyAuthError(f"An unexpected error occurred during Spotify authentication: {e}")

# Example usage (for testing purposes, will be moved to CLI)
if __name__ == '__main__':
    # These would come from environment variables or a config file in a real app
    SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
    SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
    SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')

    if not all([SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI]):
        print("Please set SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, and SPOTIPY_REDIRECT_URI environment variables.")
    else:
        authenticator = SpotifyAuthenticator(
            client_id=SPOTIPY_CLIENT_ID,
            client_secret=SPOTIPY_CLIENT_SECRET,
            redirect_uri=SPOTIPY_REDIRECT_URI
        )
        try:
            print("Attempting to get Spotify client...")
            sp = authenticator.get_spotify_client()
            user = sp.current_user()
            print(f"Successfully authenticated as {user['display_name']} ({user['id']})")

            # Test token refresh (spotipy handles this automatically on next call if token expires)
            # To manually test refresh if you have a token and know it will expire soon:
            # new_token_info = authenticator.sp_oauth.refresh_access_token(token_info['refresh_token'])
            # print("Token refreshed (if applicable).")

        except SpotifyAuthError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
