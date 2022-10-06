import json
import os.path

import requests


def create_sleeper_player_data_file():
    print("Creating player data!")

    player_data = requests.get("https://api.sleeper.app/v1/players/nfl")
    player_data.raise_for_status()
    with open(os.path.dirname(__file__) + "/../players.json", "w") as json_file:
        json.dump(player_data.json(), json_file)


def get_nfl_state():
    response = requests.get("https://api.sleeper.app/v1/state/nfl")
    response.raise_for_status()
    return response.json()


def get_rosters_for_league(league_id: str):
    rosters_response = requests.get(
        f"https://api.sleeper.app/v1/league/{league_id}/rosters"
    )
    rosters_response.raise_for_status()
    return rosters_response.json()
