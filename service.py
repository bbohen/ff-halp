import json

from interfaces.sleeper import get_rosters_for_league


def check_sleeper_roster_against_available_players(sleeper_roster, available_players):
    for player in sleeper_roster["players"]:

        player["higher_rated_players"] = []

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
                if (
                    available_player.get("status") == "Inactive"
                    or available_player["active"] == False
                ):
                    continue

                player["higher_rated_players"].append(available_player)

        if len(player["higher_rated_players"]):
            players_sorted_by_rank = sorted(
                player["higher_rated_players"],
                key=lambda d: d["ff_pro_data"]["rank_ecr"],
            )

            if player.get("position") == "DEF":
                print(
                    f"--- There are {len(player['higher_rated_players'])} available defenses ranked higher than {player['team']}({player['ff_pro_data']['rank_ecr']})"
                )
                for higher_rated_player in players_sorted_by_rank:
                    print(
                        f'- {higher_rated_player["team"]}({higher_rated_player["ff_pro_data"]["rank_ecr"]})'
                    )
            else:
                print(
                    f"--- There are {len(player['higher_rated_players'])} available players ranked higher than {player['full_name']}({player['ff_pro_data']['rank_ecr']})"
                )
                for higher_rated_player in players_sorted_by_rank:
                    print(
                        f'- {higher_rated_player["full_name"]}({higher_rated_player["ff_pro_data"]["rank_ecr"]})'
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

    print(f"--- {position}")

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
                    f'Bench player {bench_player["full_name"]}({bench_player["ff_pro_data"]["rank_ecr"]}) is higher ranked than starter: {starter["full_name"]}({starter["ff_pro_data"]["rank_ecr"]})'
                )


def get_available_players_in_sleeper(league_id: str, ff_pro_rankings_map):
    available_players = []
    taken_players = []

    rosters = get_rosters_for_league(league_id)

    for roster in rosters:
        if roster.get("players") is not None:
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
                        ff_pro_rankings_map,
                    )
                )
            except KeyError:
                # Likely an supported position like OL
                continue

    return available_players


def get_data_for_player(
    player_id: int,
    player_json,
    ff_pro_rankings_map,
):
    player_data = player_json[player_id]

    if player_data.get("full_name", None):
        player_data["ff_pro_data"] = next(
            (
                x
                for x in ff_pro_rankings_map[player_data["position"]]
                if x["player_name"] in player_data["full_name"]
                or player_data["full_name"] in x["player_name"]
            ),
            None,
        )
    elif player_data.get("position") == "DEF":
        player_data["ff_pro_data"] = next(
            (
                x
                for x in ff_pro_rankings_map[player_data["position"]]
                if x["player_team_id"] in player_data["team"]
            ),
            None,
        )
        pass
    else:
        print("Not a defense or a player?")
        pass
    return player_data


def get_roster_from_sleeper(
    league_id: str,
    user_id: str,
    player_json,
    ff_pro_rankings_map,
):
    rosters = get_rosters_for_league(league_id)

    user_roster = next(x for x in rosters if x["owner_id"] == user_id)
    user_roster["players"] = [
        get_data_for_player(
            player_id,
            player_json,
            ff_pro_rankings_map,
        )
        for player_id in user_roster["players"]
    ]
    user_roster["starters"] = [
        get_data_for_player(
            player_id,
            player_json,
            ff_pro_rankings_map,
        )
        for player_id in user_roster["starters"]
    ]
    return user_roster
