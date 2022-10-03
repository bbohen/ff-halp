import os

import requests


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
