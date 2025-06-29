import asyncio
import logging
import os
import random
from datetime import datetime
from typing import Optional

from pyplanet.apps.config import AppConfig
from pyplanet.apps.core.maniaplanet import callbacks as mp_signals
from pyplanet.apps.core.trackmania import callbacks as tm_signals
from pyplanet.contrib.command import Command
from pyplanet.utils.style import STRIP_ALL, style_strip

from .fileio import update_matchresult
from .helpers import format_net_timespan

logger = logging.getLogger(__name__)

# These messages are displayed as a congratulations to the winner of each round
# when tracking is enabled.
winner_congrats_messages = [
    'Maximum BIGGAMER points for you!',
    'Your Sunday morning display of speed impresses us.',
    'Seriously fast stuff.',
    'And you managed it without throwing your keyboard across the room.',
]


class RankingSaverApp(AppConfig):
    """
    Save Rankings to JSON files.
    """

    game_dependencies = ['trackmania_next', 'trackmania']
    mode_dependencies = ['TimeAttack']
    app_dependencies = ['core.maniaplanet', 'core.trackmania']

    namespace = 'tbg'

    def __init__(self, *args, **kwargs):
        """
        Initializes the plugin.
        """
        super().__init__(*args, **kwargs)

        self.enabled = False
        self.running = False

    async def on_start(self):
        """
        Called on starting the application.
        """

        # Init settings.

        await self.instance.permission_manager.register(
            'match', 'Manage Tournament Tracking', app=self, min_level=2)

        # Listen to signals.
        self.context.signals.listen(tm_signals.scores, self.scores)
        self.context.signals.listen(mp_signals.map.map_end, self.map_end)

        # Register commands
        # Start match logging
        await self.instance.command_manager.register(
            Command(command='start', aliases=['mstart'], namespace=self.namespace, target=self.match_start,
                    perms='rankingsaver:match', admin=True, description='Start Match Recording')
            .add_param('',
                       nargs='*',
                       type=str,
                       required=False,
                       help='Start Match Recording'))

        # Stop match logging
        await self.instance.command_manager.register(
            Command(command='stop', aliases=['mstop'], namespace=self.namespace, target=self.match_stop,
                    perms='rankingsaver:match', admin=True, description='Stop Match Recording')
            .add_param('',
                       nargs='*',
                       type=str,
                       required=False,
                       help='Stop Match Recording'))

    async def match_start(self, player, data, **kwargs):
        """
        Called when the start command is given.
        """
        # ensure the matchresults directory exists
        filename = "matchresults/matchresults.json"

        os.makedirs(os.path.dirname(filename), exist_ok=True)
        self.enabled = True
        self.running = True

        message = '$o$20atBG $fff- BIGGAMER tournament tracking will begin after map resets. $20aGLHF!$z'
        await self.instance.chat(message)

        await asyncio.sleep(5)
        await self.instance.gbx('RestartMap')

    async def match_stop(self, player, data, **kwargs):
        """
        Called when the stop command is given.
        """
        if self.enabled and self.running:
            message = '$o$20atBG $fff- Tournament will end at the conclusion of this map.$z'
            await self.instance.chat(message)
            self.running = False

    async def map_end(self, map):
        """
        Callback: map ended.
        """
        if not self.running:
            self.enabled = False
            message = '$o$20atBG $fff- Tournament tracking concluded. Go get a nice Sunday morning cup of tea!$z'
            await self.instance.chat(message)

    async def scores(self, section: str, players: dict, teams: dict, **kwargs):
        """
        Callback: New scores are available
        (usually because the round has ended and the podium is about to be displayed).
        """
        if self.enabled:
            if section == 'EndMap':
                round_result = await render_map_result(self.instance.map_manager.current_map.name, players, teams)
                winner = await get_round_result_winner(round_result)
                if winner is not None:
                    message = (f'$o$20atBG $fff- Congratulations to $z{winner}$fff! '
                               f'$i{random.choice(winner_congrats_messages)}$z')
                else:
                    message = '$o$20atBG $fff- Congratulations to... wait, nobody completed the map? Pff.$fff'
                await self.instance.chat(message)

                logging.info("Round Results:")
                logging.info(round_result)

                try:
                    await update_matchresult(round_result)
                    message = '$o$20atBG $fff- Map scores saved successfully.$z'
                except Exception as e:
                    logging.exception(e)
                    message = '$o$20atBG $fff- $f00An error occurred saving the match results.$z'
                    await self.instance.chat(message)
                    raise e

                await self.instance.chat(message)


async def get_round_result_winner(round_result: dict) -> Optional[str]:
    """
    get_round_result_winner returns the player with the fastest valid time.
    If there are no valid times, this returns None.

    Returns:
        str: The nickname of the winning player, or None if there are no valid times.
    """
    if round_result.get('RacerResults', None) is not None and len(round_result['RacerResults']) > 0:
        if round_result['RacerResults'][0].get('BestTime', None) is not None:
            return round_result.get('RacerResults')[0].get('Nick', "Unknown Racer")

    # There are no valid times.
    return None


async def render_map_result(map_name: str, players: dict, teams: dict) -> dict:
    """
    render_map_result returns a correctly formatted dictionary ready to be saved to disk.
    This function only works properly in time attack.

    Returns:
        dict: The RoundResult object.
    """
    timestr = datetime.utcnow().isoformat()

    # Create base dictionary (this will form the JSON output later)
    round_result = {
        "TrackName": style_strip(map_name, STRIP_ALL),
        "RacedAtUtc": timestr,
        "RacerResults": [
            # Nick (string / null)
            # BestTime (.net format duration)
            # Rank (int)
        ],
    }

    # This is presently done as two separate for loops because I'm lazy.
    # It should be trivial to move this first filter out to the main
    # sorting loop if it becomes a performance bottleneck.

    # Firstly we need to sort the players with invalid (unset times) out
    # so that they can be put to the back of the queue.
    match_player_bucket = []
    match_player_invalid_time_bucket = []
    for player in sorted(players, key=lambda p: p['best_race_time']):
        if player['best_race_time'] not in [-1, 0]:
            # Player has a valid race time,
            match_player_bucket.append(player)
        else:
            # Player did not set a time.
            match_player_invalid_time_bucket.append(player)

    # Append the invalid times to the end of the ranking, so that they are dealt with last.
    for player in match_player_invalid_time_bucket:
        match_player_bucket.append(player)

    player_ptr = 0
    rank_ptr = 1
    racer_results = []
    for player in match_player_bucket:
        # Initialise a new Racer.
        result = {
            'Nick': style_strip(player['player'].nickname, STRIP_ALL),
            'Rank': rank_ptr
        }

        # best_race_time is stored in milliseconds.
        best_race_time = int(player.get('best_race_time'))
        previous_record = match_player_bucket[player_ptr - 1]
        # Only write a time to the output if a valid time was set by the racer.
        if best_race_time not in [None, -1, 0]:
            if previous_record is not None and best_race_time == previous_record.get('best_race_time'):
                # It's a tie.
                # Set the rank of this player to the same as the previous player
                # (i.e 1, 2, _2_, 4)
                if 0 <= (player_ptr - 1) <= len(racer_results):
                    result['Rank'] = racer_results[player_ptr - 1]['Rank']
                else:
                    # Tied for first!
                    result['Rank'] = 1

            # Only write a time if one has been set.
            result['BestTime'] = format_net_timespan(best_race_time)

        # Nudge the rank pointer on for the next Racer.
        rank_ptr += 1

        # Also nudge the player access pointer on.
        player_ptr += 1

        # Finally, write the racer to the main results array.
        racer_results.append(result)

        # Write the current state of play to the match results file.
        round_result['RacerResults'] = racer_results

    return round_result
