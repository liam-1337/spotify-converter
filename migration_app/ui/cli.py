import click
import os
from migration_app.auth.spotify_auth import SpotifyAuthenticator, SpotifyAuthError
from migration_app.auth.ytmusic_auth import YouTubeMusicAuthenticator, YouTubeMusicAuthError
from migration_app.migration.spotify_client import SpotifyDataClient
import spotipy # For type hinting if needed

# --- Existing get_spotify_credentials ---
def get_spotify_credentials():
    client_id = os.getenv('SPOTIPY_CLIENT_ID')
    client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
    redirect_uri = os.getenv('SPOTIPY_REDIRECT_URI')

    if not client_id:
        client_id = click.prompt("Enter your Spotify Client ID", type=str)
    if not client_secret:
        client_secret = click.prompt("Enter your Spotify Client Secret", type=str, hide_input=True)
    if not redirect_uri:
        redirect_uri = click.prompt("Enter your Spotify Redirect URI", type=str)

    return client_id, client_secret, redirect_uri

# --- Refactored Spotify Authentication Helper ---
def get_authenticated_spotify_client() -> spotipy.Spotify:
    """Authenticates with Spotify and returns a client, or raises/exits."""
    client_id, client_secret, redirect_uri = get_spotify_credentials()
    if not all([client_id, client_secret, redirect_uri]):
        click.secho("Spotify Client ID, Client Secret, and Redirect URI are required.", fg="red", err=True)
        click.echo("Set them as env vars: SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, or provide when prompted.", err=True)
        raise click.Abort() # Abort if credentials are not fully provided

    try:
        authenticator = SpotifyAuthenticator(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri
        )
        sp = authenticator.get_spotify_client()
        return sp
    except SpotifyAuthError as e:
        click.secho(f"Spotify authentication failed: {e}", fg="red", err=True)
        raise click.Abort()
    except Exception as e:
        click.secho(f"An unexpected error during Spotify auth: {e}", fg="red", err=True)
        raise click.Abort()

@click.group()
def cli():
    """A CLI tool to migrate music data from Spotify to YouTube Music."""
    pass

@cli.command(name='auth-spotify')
def auth_spotify_command(): # Renamed to avoid conflict with module name
    """Authenticate with Spotify and display user information."""
    click.echo("Attempting to authenticate with Spotify...")
    try:
        sp = get_authenticated_spotify_client()
        user = sp.current_user()
        if user and user.get('display_name'):
            click.secho(f"Successfully authenticated with Spotify as: {user['display_name']} ({user['id']})", fg="green")
        else:
            click.secho("Authenticated with Spotify, but could not retrieve user display name.", fg="yellow")
    except click.Abort:
        pass # Error already printed by get_authenticated_spotify_client
    except Exception as e: # Catch any other unexpected error post-authentication
        click.secho(f"Error fetching user data: {e}", fg="red", err=True)


@cli.command(name='auth-ytmusic')
def auth_ytmusic_command(): # Renamed
    """Authenticate with YouTube Music and display library information."""
    click.echo("Attempting to authenticate with YouTube Music...")
    try:
        authenticator = YouTubeMusicAuthenticator()
        ytm = authenticator.get_ytmusic_client()
        click.secho("Successfully authenticated with YouTube Music.", fg="green")
        # ... (rest of YT Music auth, e.g., test call)
        try:
            playlists = ytm.get_library_playlists(limit=3)
            if playlists:
                click.echo(f"Found {len(playlists)} playlists in your YouTube Music library (showing up to 3):")
                for pl in playlists:
                    click.echo(f"- {pl['title']}")
            else:
                click.echo("No playlists found in your YouTube Music library or an issue occurred fetching them.")
        except Exception as e:
            click.secho(f"Could not fetch library playlists: {e}", fg="yellow")

    except YouTubeMusicAuthError as e:
        click.secho(f"YouTube Music authentication failed: {e}", fg="red", err=True)
        click.echo(f"Please ensure you have run 'python -m ytmusicapi setup' and the '{authenticator.headers_auth_path}' file is correctly set up.", err=True)
    except Exception as e:
        click.secho(f"An unexpected error during YouTube Music auth: {e}", fg="red", err=True)

# --- New Spotify Data Commands ---

@cli.command(name='list-spotify-playlists')
@click.option('--limit', default=None, type=int, help='Limit the number of playlists to display.')
def list_spotify_playlists(limit):
    """List current user's Spotify playlists."""
    try:
        sp = get_authenticated_spotify_client()
        click.echo("Fetching Spotify playlists...")
        data_client = SpotifyDataClient(sp)
        playlists = data_client.get_current_user_playlists() # Full fetch

        if not playlists:
            click.echo("No playlists found.")
            return

        click.secho(f"Found {len(playlists)} playlists:", fg="blue")

        display_playlists = playlists[:limit] if limit is not None else playlists

        for i, p in enumerate(display_playlists):
            click.echo(f"{i+1}. {p['name']} (ID: {p['id']}, Tracks: {p['tracks']['total']})")

        if limit is not None and len(playlists) > limit:
            click.echo(f"... and {len(playlists) - limit} more.")

    except click.Abort:
        pass # Error handled by get_authenticated_spotify_client
    except Exception as e:
        click.secho(f"Error fetching playlists: {e}", fg="red", err=True)

@cli.command(name='show-spotify-playlist-tracks')
@click.argument('playlist_id')
@click.option('--limit', default=None, type=int, help='Limit the number of tracks to display.')
def show_spotify_playlist_tracks(playlist_id, limit):
    """Show tracks for a specific Spotify playlist ID."""
    try:
        sp = get_authenticated_spotify_client()
        click.echo(f"Fetching tracks for Spotify playlist ID: {playlist_id}...")
        data_client = SpotifyDataClient(sp)
        tracks = data_client.get_playlist_tracks(playlist_id) # Full fetch

        if not tracks:
            click.echo("No tracks found in this playlist or playlist is empty/invalid.")
            return

        click.secho(f"Found {len(tracks)} tracks in playlist '{playlist_id}':", fg="blue")

        display_tracks = tracks[:limit] if limit is not None else tracks

        for i, t in enumerate(display_tracks):
            artist_names = ", ".join([a['name'] for a in t.get('artists', [])])
            click.echo(f"{i+1}. {t['name']} by {artist_names} (ID: {t['id']})")

        if limit is not None and len(tracks) > limit:
            click.echo(f"... and {len(tracks) - limit} more tracks.")

    except click.Abort:
        pass
    except Exception as e:
        click.secho(f"Error fetching playlist tracks: {e}", fg="red", err=True)


@cli.command(name='list-spotify-liked-songs')
@click.option('--limit', default=None, type=int, help='Limit the number of liked songs to display.')
def list_spotify_liked_songs(limit):
    """List current user's liked songs on Spotify."""
    try:
        sp = get_authenticated_spotify_client()
        click.echo("Fetching liked songs from Spotify...")
        data_client = SpotifyDataClient(sp)
        liked_songs = data_client.get_saved_tracks() # Full fetch

        if not liked_songs:
            click.echo("No liked songs found.")
            return

        click.secho(f"Found {len(liked_songs)} liked songs:", fg="blue")

        display_songs = liked_songs[:limit] if limit is not None else liked_songs

        for i, s_item in enumerate(display_songs):
            artist_names = ", ".join([a['name'] for a in s_item.get('artists', [])])
            click.echo(f"{i+1}. {s_item['name']} by {artist_names} (ID: {s_item['id']})")

        if limit is not None and len(liked_songs) > limit:
            click.echo(f"... and {len(liked_songs) - limit} more liked songs.")

    except click.Abort:
        pass
    except Exception as e:
        click.secho(f"Error fetching liked songs: {e}", fg="red", err=True)

from migration_app.migration.ytmusic_client import YouTubeMusicDataClient # Add this import

@cli.command(name='search-ytmusic-track')
@click.option('--title', required=True, help='The title of the track to search for.')
@click.option('--artist', default=None, help='The artist of the track (optional).')
@click.option('--album', default=None, help='The album of the track (optional).')
@click.option('--limit', default=5, type=int, show_default=True, help='Max number of results to return.')
def search_ytmusic_track_command(title, artist, album, limit):
    """Search for a track on YouTube Music."""
    click.echo(f"Searching YouTube Music for title: '{title}', artist: '{artist}', album: '{album}' with limit {limit}...")

    try:
        # Authenticate with YouTube Music
        yt_auth = YouTubeMusicAuthenticator() # Instantiated from cli.py's import
        ytm_sdk_client = yt_auth.get_ytmusic_client()
        click.echo("YouTube Music authentication successful.")

        # Use YouTubeMusicDataClient for searching
        yt_data_client = YouTubeMusicDataClient(ytm_sdk_client)
        results = yt_data_client.search_track(title=title, artist=artist, album=album, limit=limit)

        if not results:
            click.echo("No tracks found matching your criteria.")
            return

        click.secho(f"Found {len(results)} track(s):", fg="blue")
        for i, track in enumerate(results):
            click.echo(f"  {i+1}. Title: {track.get('title', 'N/A')}")

            artist_names = "N/A"
            if track.get('artists'):
                artist_names = ", ".join([a.get('name', 'Unknown Artist') for a in track['artists']])
            click.echo(f"     Artists: {artist_names}")

            album_name = "N/A"
            if track.get('album') and isinstance(track['album'], dict): # album can be None or dict
                 album_name = track['album'].get('name', 'Unknown Album')
            click.echo(f"     Album: {album_name}")

            click.echo(f"     Video ID: {track.get('videoId', 'N/A')}, Type: {track.get('resultType', 'N/A')}, Duration: {track.get('duration', 'N/A')}")
            click.echo("-" * 20)

    except YouTubeMusicAuthError as e:
        click.secho(f"YouTube Music authentication failed: {e}", fg="red", err=True)
        if hasattr(e, 'headers_auth_path'): # Check if this attribute exists
             click.echo(f"Please ensure you have run 'python -m ytmusicapi setup' and the '{e.headers_auth_path}' file is correctly set up.", err=True)
        # The above check for headers_auth_path might not work as expected if the attribute isn't on the exception instance.
        # A more robust way might be to check the type of error or a specific message pattern if ytmusic_auth sets it.
        # For now, relying on the general error message from YouTubeMusicAuthError.
        # The authenticator itself prints detailed setup instructions when file is not found.
    except Exception as e:
        click.secho(f"An unexpected error occurred: {e}", fg="red", err=True)


if __name__ == '__main__':
    cli()
