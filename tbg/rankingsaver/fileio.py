import asyncio
import json
import os
from datetime import datetime

# This mutex MUST be held if you wish to work with the matchresults directory.
matchfile_mutex = asyncio.Lock()

async def update_matchresult(round_result: dict):
    """
    update_matchresult updates today's matchresult file with the given round_result.
    """
    today = datetime.today().strftime('%Y-%m-%d')
    filepath = f"matchresults/{today}.json"
    # Open today's file.
    async with matchfile_mutex:
        data = None
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding="utf-8") as match_file:
                data = json.load(match_file)

        if data is None:
            # Create new basic data structure.
            data = {
                "RoundResults": [],
            }

        data['RoundResults'].append(round_result)

        # Overwrite today's matchresults file.
        with open(filepath, 'w+', encoding="utf-8") as match_file:
            match_file.write(json.dumps(data, indent=4))

async def dump_mapend_raw(players: dict, teams: dict):
    """
    dump_mapend_raw writes the raw map end information to a JSON file.
    """
    timestr = datetime.utcnow().isoformat()
    filepath = f"matchresults/raw_{timestr}.json"
    # Open the appropriate raw data file.
    async with matchfile_mutex:
        data = {
            "Players": [],
        }
        for player in players:
            player_data = {
                'best_race_time': player.get('best_race_time', 'UNKNOWN'),
                'best_lap_time': player.get('best_lap_time', 'UNKNOWN'),
            }
            if player.get('player', None) is not None:
                player_data['nickname'] = player['player'].nickname
                player_data['login'] = player['player'].login
            data.get('Players').append(player_data)


        # Write the appropriate raw data to disk.
        with open(filepath, 'w+', encoding="utf-8") as match_file:
            match_file.write(json.dumps(data, indent=4))