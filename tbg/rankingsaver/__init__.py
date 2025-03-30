import json
from datetime import datetime
import asyncio
import os
import random

from pyplanet.apps.config import AppConfig
from pyplanet.apps.core.trackmania import callbacks as tm_signals
from pyplanet.apps.core.maniaplanet import callbacks as mp_signals

from pyplanet.contrib.command import Command
from pyplanet.utils.style import STRIP_ALL, style_strip


from .helpers import format_net_timespan

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
                    perms='tbg:match', admin=True, description='Start Match Recording')
            .add_param('',
                       nargs='*',
                       type=str,
                       required=False,
                       help='Start Match Recording'))

        # Stop match logging
        await self.instance.command_manager.register(
            Command(command='stop', aliases=['mstop'], namespace=self.namespace, target=self.match_stop,
                    perms='tbg:match', admin=True, description='Stop Match Recording')
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

        message = '$o$20a tBG $fff - BIGGAMER tournament tracking will begin after map resets. $20aGLHF!$z'
        await self.instance.chat(message)

        await asyncio.sleep(5)
        await self.instance.gbx('RestartMap')

    async def match_stop(self, player, data, **kwargs):
        """
        Called when the stop command is given.
        """
        if self.enabled and self.running:
            message = '$o$20a tBG $fff - Tournament will end at the conclusion of this map.$z'
            await self.instance.chat(message)
            self.running = False

    async def map_end(self, map):
        """
        Callback: map ended.
        """
        if not self.running:
            self.enabled = False
            message = '$o$20a tBG $fff - Tournament tracking concluded. Go get a nice Sunday morning cup of tea!$z'
            await self.instance.chat(message)

    async def scores(self, section: str, players: dict, teams: dict, **kwargs):
        """
        Callback: New scores are available
        (usually because the round has ended and the podium is about to be displayed).
        """
        if self.enabled:
            if section == 'EndMap':
                winner = await self.handle_scores(players, teams)
                if winner is not None:
                    message = (f'$o$20a tBG $fff - Congratulations to $z{winner["player"].nickname}$fff! '
                               f'$i{random.choice(winner_congrats_messages)}$z')
                else:
                    message = '$o$20a tBG $fff - Congratulations to... wait, nobody completed the map? Pff.$fff'
                await self.instance.chat(message)

                message = '$o$20a tBG $fff - Map scores saved successfully.$z'
                await self.instance.chat(message)


    async def handle_scores(self, players: dict, teams: dict) -> dict:
        """
        handle_scores dumps the current state of players to a JSON file on disk.
        This function only works properly in time attack.

        Returns:
            dict: The winning player.
        """
        timestr = datetime.utcnow().isoformat()

        # Create base dictionary (this will form the JSON output later)
        match_state = {
            "TrackName": style_strip(self.instance.map_manager.current_map.name, STRIP_ALL),
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


        with open(f"matchresults/matchresults_{timestr}.json", 'w', encoding="utf-8") as match_file:
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
                            result['Rank'] = racer_results[player_ptr - 1]['Rank'] - 1
                        else:
                            # Tied for first!
                            result['Rank'] = 1

                    # Only write a time if one has been set.
                    result['BestTime'] = format_net_timespan(best_race_time)

                # Nudge the rank pointer on for the next Racer.
                rank_ptr += 1

                # Also nudge the player access pointer on.

                # Finally, write the racer to the main results array.
                racer_results.append(result)


            # Write the current state of play to the match results file.
            match_state['RacerResults'] = racer_results
            match_file.write(json.dumps(match_state))

        # Finally, return the player that came first.
        return match_player_bucket[0]
