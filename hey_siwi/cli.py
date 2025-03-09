import click

from hey_siwi.spotify import (
    PlayPlaylistAction,
    PlayRandomSongAction,
    PlaySongsAction,
    SpotifyActionConfig,
)


@click.group()
def main():
    pass


@main.command()
def eat_glass() -> None:
    cfg = SpotifyActionConfig.create(
        scopes="user-read-playback-state,user-modify-playback-state"
    )
    action = PlayPlaylistAction("3jq3BeAoiHakyy9KgII5bl")
    action.execute(cfg)


@main.command()
def play_despacito() -> None:
    cfg = SpotifyActionConfig.create(
        scopes="user-read-playback-state,user-modify-playback-state"
    )
    action = PlaySongsAction(["6habFhsOp2NvshLv26DqMb"])
    action.execute(cfg)


@main.command()
def surprise_me() -> None:
    cfg = SpotifyActionConfig.create(
        scopes="user-read-playback-state,user-modify-playback-state"
    )
    action = PlayRandomSongAction()
    action.execute(cfg)
