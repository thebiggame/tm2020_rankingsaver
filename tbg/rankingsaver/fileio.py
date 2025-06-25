import asyncio
import json
from datetime import datetime

# This mutex MUST be held if you wish to work with the matchresults directory.
matchfile_mutex = asyncio.Lock()

async def update_matchresult(round_result: dict):
    """
    update_matchresult updates today's matchresult file with the given round_result.
    """
    today = datetime.today().strftime('%Y-%m-%d')
    # Open today's file.
    async with matchfile_mutex:
        with open(f"matchresults/matchresults_{today}.json", 'r', encoding="utf-8") as match_file:
            data = json.load(match_file)

        if data is None:
            # Create new basic data structure.
            data = {
                "RoundResults": [],
            }

        data['RoundResults'].append(round_result)

        # Overwrite today's matchresults file.
        with open(f"matchresults/match_{today}.json", 'w', encoding="utf-8") as match_file:
            match_file.write(json.dumps(data))
