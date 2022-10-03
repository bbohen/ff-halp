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
#   - Support defenses
#   - Support running this for all teams a user owns in sleeper
#   - Support Yahoo

# TODO:
#   - Fix players missing due to names being inconsistent between platforms
#   - Fancy colors or a more useful output of data
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

    league_id = os.environ["LEAGUE_ID"]
    user_id = os.environ["USER_ID"]

    nfl_state = get_nfl_state()
    week = args.week or nfl_state["week"]

    print("------------")
    print(f"Halping out with week {week}")
    print("------")
    print("Do any lineup adjustments need to made?")
    print("------")

    qb_ff_pro_rankings = get_ff_pro_rankings("QB", week)
    rb_ff_pro_rankings = get_ff_pro_rankings("RB", week)
    wr_ff_pro_rankings = get_ff_pro_rankings("WR", week)
    te_ff_pro_rankings = get_ff_pro_rankings("TE", week)
    k_ff_pro_rankings = get_ff_pro_rankings("K", week)

    with open("players.json", "r") as player_file:
        player_json = json.load(player_file)

    sleeper_roster = get_roster_from_sleeper(
        str(league_id),
        str(user_id),
        player_json,
        qb_ff_pro_rankings,
        rb_ff_pro_rankings,
        wr_ff_pro_rankings,
        te_ff_pro_rankings,
        k_ff_pro_rankings,
    )

    check_sleeper_roster_for_position(sleeper_roster, "QB")
    check_sleeper_roster_for_position(sleeper_roster, "RB")
    check_sleeper_roster_for_position(sleeper_roster, "WR")
    check_sleeper_roster_for_position(sleeper_roster, "TE")
    check_sleeper_roster_for_position(sleeper_roster, "K")

    available_players = get_available_players_in_sleeper(
        league_id,
        qb_ff_pro_rankings,
        rb_ff_pro_rankings,
        wr_ff_pro_rankings,
        te_ff_pro_rankings,
        k_ff_pro_rankings,
    )

    print("------")
    print("Any better available players out there?")
    print("------")
    check_sleeper_roster_against_available_players(sleeper_roster, available_players)
    print("------------")


if __name__ == "__main__":
    raise SystemExit(main())
