from ytmusicapi import YTMusic
import os
import json

# Define a path for the YouTube Music authentication headers
YT_AUTH_HEADERS_PATH = 'headers_auth.json'

# Custom exception for YouTube Music authentication errors
class YouTubeMusicAuthError(Exception):
    pass

class YouTubeMusicAuthenticator:
    def __init__(self, headers_auth_path: str = YT_AUTH_HEADERS_PATH):
        self.headers_auth_path = headers_auth_path
        self.ytmusic = None

    def is_authenticated(self) -> bool:
        """Checks if authentication headers file exists."""
        return os.path.exists(self.headers_auth_path)

    def setup_authentication(self):
        """
        Guides the user to perform the initial authentication setup
        if the headers file is not found.
        """
        print(f"YouTube Music authentication file ('{self.headers_auth_path}') not found.")
        print("To authenticate with YouTube Music, you need to generate this file.")
        print("Please follow these steps:")
        print("1. Open a web browser and go to YouTube Music (music.youtube.com).")
        print("2. Log in to your YouTube Music account.")
        print("3. Open the developer tools (usually by pressing F12).")
        print("4. Go to the 'Network' tab.")
        print("5. Filter for 'browse' requests (or any request to music.youtube.com).")
        print("6. Find a 'browse' request, click on it.")
        print("7. In the 'Headers' section (or 'Request Headers'), find the 'Cookie' header.")
        print("8. Copy the entire value of the 'Cookie' header.")
        print("9. Also, copy the 'User-Agent' header value from the same request.")
        print("10. You will be prompted to paste these into a command line setup for ytmusicapi.")
        print("
Alternatively, you can run the following in your terminal in this project's environment:")
        print(f"  `python -m ytmusicapi setup`")
        print(f"And follow its instructions. It will create the '{self.headers_auth_path}' file for you.")
        print("
After the file is created, re-run the application.")
        # In a real application, you might directly call YTMusic.setup() if it can be done non-interactively
        # or if you can capture its output/input.
        # For now, we rely on the user running it manually.
        # YTMusic.setup(filepath=self.headers_auth_path) # This is interactive
        raise YouTubeMusicAuthError(
            f"Authentication file '{self.headers_auth_path}' not found. "
            "Please run `python -m ytmusicapi setup` in your terminal or "
            "manually create it as per documentation, then try again."
        )


    def get_ytmusic_client(self) -> YTMusic:
        """
        Returns an authenticated YTMusic client.
        Prompts for setup if authentication file is not found.
        """
        if self.ytmusic:
            return self.ytmusic

        if not self.is_authenticated():
            self.setup_authentication() # This will raise an error and instruct the user

        try:
            self.ytmusic = YTMusic(self.headers_auth_path)
            # Test authentication by fetching some basic info
            # This might vary depending on ytmusicapi version, adjust if needed
            try:
                self.ytmusic.get_library_playlists(limit=1)
            except Exception as e:
                # If the initial call fails, the auth might be stale or invalid
                # Clean up potentially bad file and re-prompt setup
                if os.path.exists(self.headers_auth_path):
                    print(f"Warning: Authentication with '{self.headers_auth_path}' failed. The file might be corrupted or credentials stale.")
                    # os.remove(self.headers_auth_path) # Optionally remove the bad file
                raise YouTubeMusicAuthError(
                    f"Failed to connect to YouTube Music with existing '{self.headers_auth_path}'. "
                    f"It might be corrupted or your session expired. Please try running "
                    f"`python -m ytmusicapi setup` again. Details: {e}"
                )
            return self.ytmusic
        except json.JSONDecodeError:
            # This can happen if headers_auth.json is malformed
            os.remove(self.headers_auth_path) # Remove corrupted file
            raise YouTubeMusicAuthError(
                f"Authentication file '{self.headers_auth_path}' is corrupted. "
                "It has been removed. Please run `python -m ytmusicapi setup` again."
            )
        except Exception as e:
            raise YouTubeMusicAuthError(f"YouTube Music authentication failed: {e}")

# Example usage (for testing purposes, will be moved to CLI)
if __name__ == '__main__':
    authenticator = YouTubeMusicAuthenticator()
    try:
        print("Attempting to get YouTube Music client...")
        ytm = authenticator.get_ytmusic_client()
        print("Successfully authenticated with YouTube Music.")

        # Example: Get library playlists (first 5)
        playlists = ytm.get_library_playlists(limit=5)
        if playlists:
            print(f"Found {len(playlists)} playlists in your YouTube Music library (showing up to 5):")
            for pl in playlists:
                print(f"- {pl['title']} ({pl['playlistId']})")
        else:
            print("No playlists found in your YouTube Music library or couldn't fetch them.")

    except YouTubeMusicAuthError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
