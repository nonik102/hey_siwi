from __future__ import annotations

import getpass
import random
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

import emoji
import halo
import requests
from spotipy.client import Spotify
from spotipy.oauth2 import SpotifyOAuth

from hey_siwi import static
from hey_siwi.actions import Action, ActionConfig

DEFAULT_CREDS_PATH = "/home/{USER}/.tokens/spotify_api.tok"
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8000"


class SpotifyActionError(Exception):
    pass


@dataclass
class SpotifyActionConfig(ActionConfig):
    # auth
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: str | None = None

    device_id: str | None = None

    # how many times to retry for retry-able actions
    retry_count: int = 10

    @staticmethod
    def _load_creds(path: str | None = None) -> tuple[str, str]:
        path = str(path or DEFAULT_CREDS_PATH).format(USER=getpass.getuser())
        if not Path(path).exists():
            raise SpotifyActionError("Cannot find spotify creds file")
        try:
            with open(path, "r") as fp:
                client_id = fp.readline().strip("\n ")
                client_secret = fp.readline().strip("\n ")
        except IOError as e:
            raise SpotifyActionError from e
        return (client_id, client_secret)

    @classmethod
    def create(cls, **kwargs: Any) -> SpotifyActionConfig:
        client_id, client_secret = cls._load_creds()
        return cls(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=DEFAULT_REDIRECT_URI,
            **kwargs,
        )


class SpotifyAction(Action):
    def __init__(self) -> None:
        self._sp: Spotify | None = None

    @property
    def spotify_client(self) -> Spotify:
        if not self._sp:
            raise RuntimeError
        return self._sp

    def execute(self, config: ActionConfig | None = None) -> None:
        if not isinstance(config, SpotifyActionConfig):
            raise SpotifyActionError("Incorrect config provided")
        self._sp = self._get_spotify_client(config)

    def _get_spotify_client(self, config: SpotifyActionConfig) -> Spotify:
        creds = SpotifyOAuth(
            client_id=config.client_id,
            client_secret=config.client_secret,
            redirect_uri=config.redirect_uri,
            scope=config.scopes,
        )
        sp = Spotify(auth_manager=creds)
        return sp


class PlayPlaylistAction(SpotifyAction):
    def __init__(self, playlist_id: str) -> None:
        self._playlist_id = playlist_id

    def _print_blurb(self) -> None:
        resp = self.spotify_client.playlist(self._playlist_id)
        if not resp:
            raise SpotifyActionError("Unable to get playlist details!")
        playlist_name = resp["name"]
        creator_name = resp["owner"]["display_name"]
        music_note = emoji.emojize(":musical_note:")
        print(
            f"Playing {creator_name}'s playlist: "
            f"{playlist_name} {music_note*3}"
        )

    def execute(self, config: ActionConfig | None = None) -> None:
        super().execute(config)

        context_uri = f"spotify:playlist:{self._playlist_id}"
        self._print_blurb()
        self.spotify_client.start_playback(context_uri=context_uri)


class PlaySongAction(SpotifyAction):
    def __init__(self, song_id: str) -> None:
        self._song_id = song_id

    def _print_blurb(self) -> None:
        resp = self.spotify_client.track(self._song_id)
        if not resp:
            raise SpotifyActionError("Unable to get track details!")
        track_name = resp["name"]
        artists = ", ".join([artist["name"] for artist in resp["artists"]])
        music_note = emoji.emojize(":musical_note:")
        track_emoji = emoji.emojize(":optical_disk:")
        artists_emoji = emoji.emojize(":man_singer::woman_singer:")
        print(
            f"Playing {track_emoji} {track_name} "
            f"by {artists_emoji} {artists} {music_note*3}"
        )

    def execute(self, config: ActionConfig | None = None) -> None:
        super().execute(config)

        uris = [f"spotify:track:{self._song_id}"]
        self._print_blurb()
        self.spotify_client.start_playback(uris=uris)


@dataclass
class ItemRecord:
    id: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ItemRecord:
        return cls(id=d["id"])


class PlayRandomSongAction(SpotifyAction):
    def __init__(self, retry_count: int = 5) -> None:
        self._retry_count = retry_count

    def _get_genre(self) -> str:
        # spotify doesn't provide info on genres, so use this static list
        genre_file = str(resources.files(static) / "genres.txt")
        genre_list = list(open(genre_file, "r"))
        genre = random.choice(genre_list).strip("\n")
        return genre

    def _get_random(self) -> str | None:
        query = f"genre:{self._get_genre()}"
        data = self.spotify_client.search(
            q=query, limit=50, type="track", market="US"
        )
        if not data:
            raise SpotifyActionError
        samples: list[str] = []
        while True:
            # pick a sample from this batch
            num_items = len(data["tracks"]["items"])
            if num_items == 0:
                return None
            to_pick = random.randint(0, num_items - 1)
            samples.append(data["tracks"]["items"][to_pick]["id"])
            # check if there's another batch to look at
            if not data["tracks"]["next"]:
                break
            # get the next batch
            resp = requests.get(
                url=data["tracks"]["next"],
                headers=self.spotify_client._auth_headers(),
            )
            data = resp.json()
        return random.choice(samples)

    def execute(self, config: ActionConfig | None = None) -> None:
        super().execute(config)

        mag_glass = emoji.emojize(":magnifying_glass_tilted_right:")
        spinner = halo.Halo(spinner="dots")
        spinner.start(text=f"Searching for a song... {mag_glass}")

        # we should use retries in case we get a bad genre with no items!
        song_id = self._get_random()
        for _ in range(self._retry_count):
            song_id = self._get_random()
            if song_id:
                break
        if not song_id:
            spinner.fail("Unable to find a song!")
            raise SpotifyActionError("Unable to find a song!")

        spinner.succeed(text="Found a song!")

        subtask = PlaySongAction(song_id)
        subtask.execute(config)
