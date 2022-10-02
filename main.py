#!/usr/bin/env python

import argparse
import os
import json
from collections.abc import Sequence

import requests

# Objective:
#   - ✅ Tell user if they should make changes to their lineup based on fantasy pros 
#   - Tell user if there are higher ranked available players based on fantasy pros
#   - Do these things for different dynamic accounts, mayby even all in sleeper?

def check_sleeper_roster_for_position(sleeper_roster, position):
    starters_for_position = [player for player in sleeper_roster['starters'] if player['position'] == position]
    players_for_position = [player for player in sleeper_roster['players'] if player['position'] == position]
    bench_players_for_position = [player for player in players_for_position if player not in starters_for_position]

    print(f'{len(starters_for_position)} starters at {position}')
    print(f'{len(bench_players_for_position)} bench players at {position}')

    for starter in starters_for_position:
        if not starter.get('ff_pro_data', None):
            print(f'{starter["full_name"]} has no matching data in FantasyPros!')
            continue

        for bench_player in bench_players_for_position:
            if not bench_player.get('ff_pro_data', None):
                print(f'{bench_player["full_name"]} has no matching data in FantasyPros!')
                continue

            if bench_player['ff_pro_data']['rank_ecr'] < starter['ff_pro_data']['rank_ecr']:
                print(f'Bench player {bench_player["full_name"]} is higher ranked than starter: {starter["full_name"]}')
    
    

def create_sleeper_player_data():
    print('Creating player data!')

    player_data = requests.get('https://api.sleeper.app/v1/players/nfl')
    with open('players.json', 'w') as json_file:
        json.dump(player_data.json(), json_file)

def get_ff_pro_rankings(position):
    ff_response = requests.get(
        'https://api.fantasypros.com/v2/json/nfl/2022/consensus-rankings',
        params={
            'experts': 'available', # Is this needed?
            'position': position,
            'scoring': 'HALF',
            'type': 'weekly',
            # TODO: Week should be dynamic, use sleeper state endpoint?
            'week': 4,
        },
        headers={
            'x-api-key': os.environ['FF_PROS_API_KEY']
        }
    )
    ff_response.raise_for_status()
    ranking_data = ff_response.json()
    return ranking_data['players']


def get_data_for_player(player_id: int, qb_ff_pro_rankings, rb_ff_pro_rankings, wr_ff_pro_rankings, te_ff_pro_rankings, k_ff_pro_rankings):
    ff_pro_data_ranking_map = {
        'QB' : qb_ff_pro_rankings,
        'RB': rb_ff_pro_rankings,
        'WR': wr_ff_pro_rankings,
        'TE': te_ff_pro_rankings,
        'K': k_ff_pro_rankings,
    }

    with open('players.json', 'r') as player_file:
        player_json = json.load(player_file)
        player_data = player_json[player_id]
        if player_data.get('full_name', None):
            player_data['ff_pro_data'] = next((x for x in ff_pro_data_ranking_map[player_data['position']] if x['player_name'] in player_data['full_name'] or player_data['full_name'] in x['player_name']), None)
        else:
            # TODO: Add support for defense
            print('The player data had no full name! Was it a defense?')
        return player_data

def get_roster_from_sleeper(league_id: str, user_id: str, qb_ff_pro_rankings, rb_ff_pro_rankings, wr_ff_pro_rankings, te_ff_pro_rankings, k_ff_pro_rankings):
    rosters_response = requests.get(f'https://api.sleeper.app/v1/league/{league_id}/rosters')
    rosters_response.raise_for_status()

    rosters = rosters_response.json()
    user_roster = next(x for x in rosters if x['owner_id'] == user_id)
    user_roster['players'] = [
        get_data_for_player(player_id, qb_ff_pro_rankings, rb_ff_pro_rankings, wr_ff_pro_rankings, te_ff_pro_rankings, k_ff_pro_rankings) for player_id in user_roster['players']
    ]
    user_roster['starters'] = [
        get_data_for_player(player_id, qb_ff_pro_rankings, rb_ff_pro_rankings, wr_ff_pro_rankings, te_ff_pro_rankings, k_ff_pro_rankings) for player_id in user_roster['starters']
    ]
    return user_roster
    

def main(argv: Sequence[str] | None = None):
    parser = argparse.ArgumentParser()
    # Add arguments here
    parser.add_argument(
        "--create-players",
        action="store_true",
        help="Create JSON file filled with Sleeper player data"
    )
    args = parser.parse_args(argv)

    if args.create_players:
        create_sleeper_player_data()

    # league_id = 784479542935990272
    # user_id = 590283383364423680
    league_id = os.environ['LEAGUE_ID']
    user_id = os.environ['USER_ID']

    # TODO: Evaluate if this could be made in 1 request via a superflex filter
    qb_ff_pro_rankings = get_ff_pro_rankings("QB")
    rb_ff_pro_rankings = get_ff_pro_rankings("RB")
    wr_ff_pro_rankings = get_ff_pro_rankings("WR")
    te_ff_pro_rankings = get_ff_pro_rankings("TE")
    k_ff_pro_rankings = get_ff_pro_rankings("K")

    sleeper_roster = get_roster_from_sleeper(
        str(league_id),
        str(user_id),
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


if __name__ == "__main__":
    raise SystemExit(main())
