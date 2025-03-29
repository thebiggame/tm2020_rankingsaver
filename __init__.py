import json
import time
import asyncio
import os
import shutil

from pyplanet.apps.config import AppConfig
from pyplanet.apps.core.trackmania import callbacks as tm_signals
from pyplanet.apps.core.maniaplanet import callbacks as mp_signals

from pyplanet.contrib.command import Command
from pyplanet.utils.style import STRIP_ALL, style_strip


from helpers import format_net_timespan


class RankingSaver(AppConfig):
    """
    Save RoundPoints on EndMap to DB
    """

    game_dependencies = ['trackmania_next', 'trackmania']
    mode_dependencies = ['TimeAttack']
    app_dependencies = ['core.maniaplanet', 'core.trackmania']

    def __init__(self, *args, **kwargs):
        """
        Initializes the plugin.
        """
        super().__init__(*args, **kwargs)

        self.namespace = 'match'
        self.enabled = False
        self.running = False
        self.list_view = None

    async def on_start(self):
        """
        Called on starting the application.
        """

        # Init settings.

        await self.instance.permission_manager.register(
            'start', 'Start MatchSaving command', app=self, min_level=2)

        # Listen to signals.
        self.context.signals.listen(tm_signals.scores, self.scores)
        self.context.signals.listen(mp_signals.map.map_end, self.map_end)

        # Start MatchSaving HTML on command
        await self.instance.command_manager.register(
            Command(command='start', aliases=['mstart'], namespace=self.namespace, target=self.match_start,
                    perms='match_results:start', admin=True, description='Start Match Recording').add_param('',
                                                                                                                nargs='*',
                                                                                                                type=str,
                                                                                                                required=False,
                                                                                                                help='Start Match Recording'))

        # Stop MatchSaving HTML on command
        await self.instance.command_manager.register(
            Command(command='stop', aliases=['mstop'], namespace=self.namespace, target=self.match_stop,
                    perms='match_results:start', admin=True, description='Stop Match Recording').add_param('',
                                                                                                               nargs='*',
                                                                                                               type=str,
                                                                                                               required=False,
                                                                                                               help='Stop Match Recording'))

    async def match_start(self, player, data, **kwargs):
        message = '$o$20a tBG $fff - BIGGAMER tournament tracking will begin after map resets. $20aGLHF!$z'
        # make a copy of the matchresults to work with
        filename = "matchresults/matchresults.json"
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        if not os.path.exists(filename):
            open(filename, 'w').close()
        src = "matchresults/matchresults.json"
        dst = "matchresults/matchresults_{}.html".format(time.strftime("%Y-%m-%d_%H-%M-%S"))
        shutil.copy(src, dst)
        os.remove('matchresults/matchresults.json')
        self.enabled = True
        self.running = True
        await self.instance.chat(message)
        await asyncio.sleep(5)
        await self.instance.gbx('RestartMap')

    async def match_stop(self, player, data, **kwargs):
        if self.enabled and self.running:
            message = '$o$20a tBG $fff - Tournament will end at the conclusion of this map.$z'
            await self.instance.chat(message)
            self.running = False

    async def map_end(self, map):
        if not self.running:
            self.enabled = False

    async def scores(self, section, players, teams, **kwargs):
        if not self.enabled:
            return
        else:
            if section == 'EndMap':
                await self.handle_scores(players, teams)

    async def handle_scores(self, players, teams):
        timestr = time.strftime("%Y-%m-%d_%H-%M-%S")

        # Create base dictionary
        matchState = {
            "TrackName": style_strip(self.instance.map_manager.current_map.name, STRIP_ALL),
            "RacedAtUtc": timestr,
            "RacerResults": [
                # Nick (string / null), BestTime (.net format duration), Rank (int)
            ],
        }

        with open('matchresults/matchresults.json', 'a', encoding="utf-8") as myFile:
            rank = 1
            racerResults = []
            for player in players:
                # Initialise a new Racer.
                result = {
                    'Nick': style_strip(player['player'].nickname, STRIP_ALL),
                    'Rank': rank
                }

                # Nudge the rank on for the next Racer.
                rank += 1

                # best_racetime is in ms.
                if player['best_race_time'] != -1:
                    # Only write a time if one has been set.
                    result['BestTime'] = format_net_timespan(int(player['best_race_time']))

                # Finally, write the racer to the main results array.
                racerResults.append(result)

            # Write the current state of play to the match results file.
            matchState['RacerResults'] = racerResults
            myFile.write(json.dumps(matchState))