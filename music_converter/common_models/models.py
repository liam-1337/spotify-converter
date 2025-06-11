from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Track:
    title: str
    artist: str
    album: str
    duration_ms: int
    spotify_id: Optional[str] = None
    youtube_id: Optional[str] = None

@dataclass
class Playlist:
    name: str
    tracks: List[Track]
    description: Optional[str] = ""
    spotify_id: Optional[str] = None
    youtube_id: Optional[str] = None
