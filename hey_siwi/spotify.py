from __future__ import annotations

import getpass
import random
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Iterable

import emoji
import halo
import pycountry
import requests
import spotipy as sp

from hey_siwi import static
from hey_siwi.actions import Action, ActionConfig
from hey_siwi.common import bcolors

DEFAULT_CREDS_PATH = "/home/{USER}/.tokens/spotify_api.tok"
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8000"


class SpotifyActionError(Exception):
    pass


@dataclass
class SongData:
    song_name: str
    artist_names: list[str]
    album_name: str
    country_name: str
    country_flag: str
    release_year: str

    @staticmethod
    def _plural_str(s: list[str]) -> str:
        artist_string = f"{', '.join(s) + 's' * min(1, max(len(s) - 1, 0))}"
        return artist_string

    @classmethod
    def from_spotify(cls, data: Any) -> SongData:
        return SongData(
            song_name=data["name"],
            artist_names=[artist["name"] for artist in data["artists"]],
            album_name=data["album"]["name"],
            country_name="",
            country_flag="",
            release_year=data["album"]["release_date"],
        )

    def pretty(self) -> str:
        man_artist = emoji.emojize(":man_singer:")
        woman_artist = emoji.emojize(":woman_singer:")
        microphone = emoji.emojize(":microphone:")
        book = emoji.emojize(":closed_book:")
        timer = emoji.emojize(":hourglass_not_done:")
        blue = bcolors.OKGREEN
        red = bcolors.FAIL
        noc = bcolors.ENDC
        return (
            f"{microphone:>3}{red} Song: {blue}{self.song_name}{noc}\n"
            f"{man_artist+woman_artist:>3}{red} Artist(s): {blue}{self._plural_str(self.artist_names)}{noc}\n"
            f"{book:>3} {red}Album: {blue}{self.album_name}{noc}\n"
            f"{timer:>3} {red}Year: {blue}{self.release_year}{noc}"
        )

    def __str__(self) -> str:
        return self.pretty()


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
        self._sp: sp.Spotify | None = None

    @property
    def spotify_client(self) -> sp.Spotify:
        if not self._sp:
            raise RuntimeError
        return self._sp

    def execute(self, config: ActionConfig | None = None) -> None:
        if not isinstance(config, SpotifyActionConfig):
            raise SpotifyActionError("Incorrect config provided")
        self._sp = self._get_spotify_client(config)

    def _get_spotify_client(self, config: SpotifyActionConfig) -> sp.Spotify:
        creds = sp.SpotifyOAuth(
            client_id=config.client_id,
            client_secret=config.client_secret,
            redirect_uri=config.redirect_uri,
            scope=config.scopes,
        )
        sp_client = sp.Spotify(auth_manager=creds)
        return sp_client

    def handle(self, ex: sp.SpotifyException) -> None:
        if ex.http_status == 404:
            j_j = emoji.emojize(":loudly_crying_face:")
            c = bcolors.FAIL
            print(f"{c}No available devices to connect to! {j_j}")


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
        try:
            self.spotify_client.start_playback(context_uri=context_uri)
            self._print_blurb()
        except sp.SpotifyException as ex:
            self.handle(ex)


class PlaySongAction(SpotifyAction):
    def __init__(self, song_id: str) -> None:
        self._song_id = song_id

    def _print_blurb(self) -> None:
        resp = self.spotify_client.track(self._song_id)
        if not resp:
            raise SpotifyActionError("Unable to get track details!")
        data = SongData.from_spotify(resp)
        track_emoji = emoji.emojize(":optical_disk:")
        c = bcolors.OKCYAN
        noc = bcolors.ENDC
        print(f"{c}Playing!!! {track_emoji}{noc}")
        print(data)

    def execute(self, config: ActionConfig | None = None) -> None:
        super().execute(config)

        uris = [f"spotify:track:{self._song_id}"]
        try:
            self.spotify_client.start_playback(uris=uris)
            self._print_blurb()
        except sp.SpotifyException as ex:
            self.handle(ex)


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
            c = bcolors.FAIL
            spinner.fail(f"{c}Unable to find a song!")
            raise SpotifyActionError("Unable to find a song!")

        spinner.succeed(text="Found a song!\n")

        subtask = PlaySongAction(song_id)
        subtask.execute(config)
