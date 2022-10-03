#!/usr/bin/env python

import argparse
import os
import json
from collections.abc import Sequence

import requests

# Objective:
#   - ✅ Tell user if they should make changes to their lineup based on fantasy pros
#   - ✅ Tell user if there are higher ranked available players based on fantasy pros
#   - Support defenses
#   - Support running this for all teams a user owns in sleeper
#   - Support Yahoo


def check_sleeper_roster_against_available_players(sleeper_roster, available_players):
    for player in sleeper_roster["players"]:
        if not player.get("full_name"):
            # TODO: Support defenses
            continue

        if not player.get("ff_pro_data"):
            print(f'{player["full_name"]} has no matching data in FantasyPros!')
            continue

        for available_player in available_players:
            if available_player["position"] != player["position"]:
                continue

            if not available_player.get("ff_pro_data", None):
                # TODO: Monitor this? Retry? Eh?
                #       Seems to happen a lot with lesser known players
                # print(f'{available_player["full_name"]} has no matching data in FantasyPros!')
                continue

            if (
                available_player["ff_pro_data"]["rank_ecr"]
                < player["ff_pro_data"]["rank_ecr"]
            ):
                print(
                    f'Available player {available_player["full_name"]} is higher ranked than rostered player: {player["full_name"]}'
                )


def check_sleeper_roster_for_position(sleeper_roster, position):
    starters_for_position = [
        player
        for player in sleeper_roster["starters"]
        if player["position"] == position
    ]
    players_for_position = [
        player for player in sleeper_roster["players"] if player["position"] == position
    ]
    bench_players_for_position = [
        player for player in players_for_position if player not in starters_for_position
    ]

    print(f"{len(starters_for_position)} starters at {position}")
    print(f"{len(bench_players_for_position)} bench players at {position}")

    for starter in starters_for_position:
        if not starter.get("ff_pro_data", None):
            print(f'{starter["full_name"]} has no matching data in FantasyPros!')
            continue

        for bench_player in bench_players_for_position:
            if not bench_player.get("ff_pro_data", None):
                print(
                    f'{bench_player["full_name"]} has no matching data in FantasyPros!'
                )
                continue

            if (
                bench_player["ff_pro_data"]["rank_ecr"]
                < starter["ff_pro_data"]["rank_ecr"]
            ):
                print(
                    f'Bench player {bench_player["full_name"]} is higher ranked than starter: {starter["full_name"]}'
                )


def create_sleeper_player_data():
    print("Creating player data!")

    player_data = requests.get("https://api.sleeper.app/v1/players/nfl")
    with open("players.json", "w") as json_file:
        json.dump(player_data.json(), json_file)


def get_available_players_in_sleeper(
    league_id: str,
    qb_ff_pro_rankings,
    rb_ff_pro_rankings,
    wr_ff_pro_rankings,
    te_ff_pro_rankings,
    k_ff_pro_rankings,
):
    rosters_response = requests.get(
        f"https://api.sleeper.app/v1/league/{league_id}/rosters"
    )
    rosters_response.raise_for_status()
    rosters = rosters_response.json()

    available_players = []
    taken_players = []

    for roster in rosters:
        for player in roster["players"]:
            taken_players.append(player)

    with open("players.json", "r") as player_file:
        all_sleeper_players = json.load(player_file)

    for player_id, player_data in all_sleeper_players.items():
        if player_id not in taken_players:
            try:
                available_players.append(
                    get_data_for_player(
                        player_id,
                        all_sleeper_players,
                        qb_ff_pro_rankings,
                        rb_ff_pro_rankings,
                        wr_ff_pro_rankings,
                        te_ff_pro_rankings,
                        k_ff_pro_rankings,
                    )
                )
            except KeyError:
                # Likely an supported position like OL
                continue

    return available_players


def get_nfl_state():
    response = requests.get("https://api.sleeper.app/v1/state/nfl")
    response.raise_for_status()
    return response.json()


def get_ff_pro_rankings(position: str, week: int):
    ff_response = requests.get(
        "https://api.fantasypros.com/v2/json/nfl/2022/consensus-rankings",
        params={
            "experts": "available",  # Is this needed?
            "position": position,
            "scoring": "HALF",
            "type": "weekly",
            "week": week,
        },
        headers={"x-api-key": os.environ["FF_PROS_API_KEY"]},
    )
    ff_response.raise_for_status()
    ranking_data = ff_response.json()
    return ranking_data["players"]


def get_data_for_player(
    player_id: int,
    player_json,
    qb_ff_pro_rankings,
    rb_ff_pro_rankings,
    wr_ff_pro_rankings,
    te_ff_pro_rankings,
    k_ff_pro_rankings,
):
    ff_pro_data_ranking_map = {
        "QB": qb_ff_pro_rankings,
        "RB": rb_ff_pro_rankings,
        "WR": wr_ff_pro_rankings,
        "TE": te_ff_pro_rankings,
        "K": k_ff_pro_rankings,
    }

    player_data = player_json[player_id]

    if player_data.get("full_name", None):
        player_data["ff_pro_data"] = next(
            (
                x
                for x in ff_pro_data_ranking_map[player_data["position"]]
                if x["player_name"] in player_data["full_name"]
                or player_data["full_name"] in x["player_name"]
            ),
            None,
        )
    else:
        # TODO: Add support for defense
        pass

    return player_data


def get_roster_from_sleeper(
    league_id: str,
    user_id: str,
    player_json,
    qb_ff_pro_rankings,
    rb_ff_pro_rankings,
    wr_ff_pro_rankings,
    te_ff_pro_rankings,
    k_ff_pro_rankings,
):
    rosters_response = requests.get(
        f"https://api.sleeper.app/v1/league/{league_id}/rosters"
    )
    rosters_response.raise_for_status()
    rosters = rosters_response.json()

    user_roster = next(x for x in rosters if x["owner_id"] == user_id)
    user_roster["players"] = [
        get_data_for_player(
            player_id,
            player_json,
            qb_ff_pro_rankings,
            rb_ff_pro_rankings,
            wr_ff_pro_rankings,
            te_ff_pro_rankings,
            k_ff_pro_rankings,
        )
        for player_id in user_roster["players"]
    ]
    user_roster["starters"] = [
        get_data_for_player(
            player_id,
            player_json,
            qb_ff_pro_rankings,
            rb_ff_pro_rankings,
            wr_ff_pro_rankings,
            te_ff_pro_rankings,
            k_ff_pro_rankings,
        )
        for player_id in user_roster["starters"]
    ]
    return user_roster


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
        create_sleeper_player_data()

    league_id = os.environ["LEAGUE_ID"]
    user_id = os.environ["USER_ID"]

    nfl_state = get_nfl_state()
    week = args.week or nfl_state['week']

    print('------------')
    print(f'Halping out with week {week}')
    print('------')
    print('Do any lineup adjustments need to made?')
    print('------')

    # TODO: Evaluate if this could be made in 1 request via a superflex filter
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

    print('------')
    print('Any better available players out there?')
    print('------')
    check_sleeper_roster_against_available_players(sleeper_roster, available_players)
    print('------------')


if __name__ == "__main__":
    raise SystemExit(main())
