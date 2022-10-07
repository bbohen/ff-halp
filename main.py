#!/usr/bin/env python

import argparse
import os
import json
from collections.abc import Sequence

from service import (
    check_sleeper_roster_against_available_players,
    check_sleeper_roster_for_position,
    get_available_players_in_sleeper,
    get_roster_from_sleeper,
)
from interfaces.ffpros import get_ff_pro_rankings
from interfaces.sleeper import (
    create_sleeper_player_data_file,
    get_nfl_state,
)

# Objective:
#   - ✅ Tell user if they should make changes to their lineup based on fantasy pros
#   - ✅ Tell user if there are higher ranked available players based on fantasy pros
#   - ✅ Support multiple sleeper leagues
#   - ✅ Support defenses
#   - Support Yahoo

# TODO:
#   - Better handling of duplicate players in Sleeper's system
#       - Any way to tell from the record if it shouldn't be used?
#   - Fancy colors or a more useful output of data
#   - Better typing
#   - Maybe use dataclasses?


def main(argv: Sequence[str] | None = None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--create-players",
        action="store_true",
        help="Create JSON file filled with Sleeper player data",
    )
    parser.add_argument(
        "--week",
        help="Week of the NFL season to analyze",
    )
    args = parser.parse_args(argv)

    if args.create_players:
        create_sleeper_player_data_file()

    league_ids = json.loads(os.environ["LEAGUE_IDS"])
    user_id = os.environ["USER_ID"]

    nfl_state = get_nfl_state()
    week = args.week or nfl_state["week"]

    print("------------")
    print(f"Halping out with week {week}")

    ff_pro_rankings_map = {
        "QB": get_ff_pro_rankings("QB", week),
        "RB": get_ff_pro_rankings("RB", week),
        "WR": get_ff_pro_rankings("WR", week),
        "TE": get_ff_pro_rankings("TE", week),
        "K": get_ff_pro_rankings("K", week),
        "DEF": get_ff_pro_rankings("DST", week),
    }

    with open("players.json", "r") as player_file:
        player_json = json.load(player_file)

    for league_id in league_ids:

        sleeper_roster = get_roster_from_sleeper(
            str(league_id),
            str(user_id),
            player_json,
            ff_pro_rankings_map,
        )

        print("------")
        print(f"Do any lineup adjustments need to made for {league_id}?")
        print("------")

        check_sleeper_roster_for_position(sleeper_roster, "QB")
        check_sleeper_roster_for_position(sleeper_roster, "RB")
        check_sleeper_roster_for_position(sleeper_roster, "WR")
        check_sleeper_roster_for_position(sleeper_roster, "TE")
        check_sleeper_roster_for_position(sleeper_roster, "K")
        check_sleeper_roster_for_position(sleeper_roster, "DEF")

        available_players = get_available_players_in_sleeper(
            league_id,
            ff_pro_rankings_map,
        )

        print("------")
        print(f"Any better available players out there for {league_id}?")
        print("------")
        check_sleeper_roster_against_available_players(
            sleeper_roster, available_players
        )

    print("------------")


if __name__ == "__main__":
    raise SystemExit(main())
