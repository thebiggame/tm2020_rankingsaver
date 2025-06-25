import unittest

import pyplanet.apps.core.maniaplanet.models

from tbg.rankingsaver import get_round_result_winner, render_map_result


class TestGetRoundResultWinner(unittest.TestCase):
    async def test_invalid_data(self):
        # Bad data
        data = {}
        result = await get_round_result_winner(data)
        assert result is None

    async def test_no_valid_time(self):
        data = {"TrackName": "Training - 01", "RacedAtUtc": "2025-03-30T21:52:51.961133",
                "RacerResults": [{"Nick": "duckfullstop", "Rank": 1}]}
        result = await get_round_result_winner(data)
        assert result is None

    async def test_valid_time(self):
        data = {"TrackName": "Training - 01", "RacedAtUtc": "2025-03-30T21:52:51.961133",
                "RacerResults": [{"Nick": "duckfullstop", "Rank": 1, "BestTime": "0:0:8.247000"},
                                 {"Nick": "putty_thing", "Rank": 2, "BestTime": "0:0:57.000000"},
                                 {"Nick": "Jynx", "Rank": 3, "BestTime": "0:1:10.200000"},
                                 {"Nick": "Blackstar", "Rank": 4}, ]}
        result = await get_round_result_winner(data)
        assert result is not None
        assert result["Nick"] == "duckfullstop"
        assert result["Rank"] == 1
        assert result["BestTime"] == "0:0:8.247000"


class TestRenderMapResult:
    async def test_no_times(self):
        players = {}
        teams = {}
        round_result = await render_map_result("Training - 01", players, teams)
        assert round_result is not None
        assert round_result.get('TrackName') == "Training - 01"
        assert round_result.get('RacedAtUtc') is not None
        assert round_result.get('RacerResults') is not None

    async def test_player_single_without_time(self):
        player_1 = dict(
            player = pyplanet.apps.core.maniaplanet.models.Player(nickname="duckfullstop"),
            best_race_time = -1,
        )
        players = [player_1]
        teams = []
        round_result = await render_map_result("Training - 01", players, teams)
        assert round_result is not None
        assert round_result.get('TrackName') == "Training - 01"
        assert round_result.get('RacedAtUtc') is not None
        assert round_result.get('RacerResults') is not None
        assert len(round_result['RacerResults']) == 1
        assert round_result['RacerResults'][0]['Nick'] == 'duckfullstop'
        assert round_result['RacerResults'][0]['Rank'] == 1
        assert round_result['RacerResults'][0].get('BestTime') is None

    async def test_player_single_with_time(self):
        player_1 = dict(
            player = pyplanet.apps.core.maniaplanet.models.Player(nickname="duckfullstop"),
            best_race_time=123456,
        )
        players = [player_1]
        teams = []
        round_result = await render_map_result("Training - 01", players, teams)
        assert round_result is not None
        assert round_result.get('TrackName') == "Training - 01"
        assert round_result.get('RacedAtUtc') is not None
        assert round_result.get('RacerResults') is not None
        assert len(round_result['RacerResults']) == 1
        assert round_result['RacerResults'][0]['Nick'] == 'duckfullstop'
        assert round_result['RacerResults'][0]['Rank'] == 1
        assert round_result['RacerResults'][0]['BestTime'] == '0:2:3.456000'

    async def test_player_multiple_with_times(self):
        players = []
        player_1 = dict(
            player = pyplanet.apps.core.maniaplanet.models.Player(nickname="Racer1"),
            best_race_time=100000,
        )
        players.append(player_1)
        player_2 = dict(
            player=pyplanet.apps.core.maniaplanet.models.Player(nickname="Racer2"),
            best_race_time=100002,
        )
        players.append(player_2)
        # Players 3 and 4 are tied for third.
        player_3 = dict(
            player=pyplanet.apps.core.maniaplanet.models.Player(nickname="Racer3"),
            best_race_time=100003,
        )
        players.append(player_3)
        player_4 = dict(
            player=pyplanet.apps.core.maniaplanet.models.Player(nickname="Racer4"),
            best_race_time=100003,
        )
        players.append(player_4)
        player_5 = dict(
            player=pyplanet.apps.core.maniaplanet.models.Player(nickname="Racer5"),
            best_race_time=100005,
        )
        players.append(player_5)

        teams = []
        round_result = await render_map_result("Training - 01", players, teams)
        assert round_result is not None
        assert round_result.get('TrackName') == "Training - 01"
        assert round_result.get('RacedAtUtc') is not None
        assert round_result.get('RacerResults') is not None
        assert len(round_result['RacerResults']) == 5
        # Rank 1
        rcr = round_result['RacerResults'][0]
        assert rcr['Nick'] == "Racer1"
        assert rcr['Rank'] == 1
        assert rcr['BestTime'] == '0:1:40.0'
        # Rank 2
        rcr = round_result['RacerResults'][1]
        assert rcr['Nick'] == "Racer2"
        assert rcr['Rank'] == 2
        assert rcr['BestTime'] == '0:1:40.2000'
        # Rank 3
        rcr = round_result['RacerResults'][2]
        assert rcr['Nick'] == "Racer3"
        assert rcr['Rank'] == 3
        assert rcr['BestTime'] == '0:1:40.3000'
        # Rank 4
        rcr = round_result['RacerResults'][3]
        assert rcr['Nick'] == "Racer4"
        assert rcr['Rank'] == 3
        assert rcr['BestTime'] == '0:1:40.3000'
        # Rank 5
        rcr = round_result['RacerResults'][4]
        assert rcr['Nick'] == "Racer5"
        assert rcr['Rank'] == 5
        assert rcr['BestTime'] == '0:1:40.5000'

    async def test_player_multiple_mix(self):
        players = []
        # Players 1 and 2 are tied for first.
        player_1 = dict(
            player=pyplanet.apps.core.maniaplanet.models.Player(nickname="Racer1"),
            best_race_time=100000,
        )
        players.append(player_1)
        player_2 = dict(
            player=pyplanet.apps.core.maniaplanet.models.Player(nickname="Racer2"),
            best_race_time=100000,
        )
        players.append(player_2)
        player_3 = dict(
            player=pyplanet.apps.core.maniaplanet.models.Player(nickname="Racer3"),
            best_race_time=100003,
        )
        players.append(player_3)
        # Players 4 and 5 did not set a time.
        player_4 = dict(
            player=pyplanet.apps.core.maniaplanet.models.Player(nickname="Racer4"),
            best_race_time=-1,
        )
        players.append(player_4)
        player_5 = dict(
            player=pyplanet.apps.core.maniaplanet.models.Player(nickname="Racer5"),
            best_race_time=0,
        )
        players.append(player_5)

        teams = []
        round_result = await render_map_result("Training - 01", players, teams)
        assert round_result is not None
        assert round_result.get('TrackName') == "Training - 01"
        assert round_result.get('RacedAtUtc') is not None
        assert round_result.get('RacerResults') is not None
        assert len(round_result['RacerResults']) == 5
        # Rank 1
        rcr = round_result['RacerResults'][0]
        assert rcr['Nick'] == "Racer1"
        assert rcr['Rank'] == 1
        assert rcr['BestTime'] == '0:1:40.0'
        # Rank 2
        rcr = round_result['RacerResults'][1]
        assert rcr['Nick'] == "Racer2"
        assert rcr['Rank'] == 1
        assert rcr['BestTime'] == '0:1:40.0'
        # Rank 3
        rcr = round_result['RacerResults'][2]
        assert rcr['Nick'] == "Racer3"
        assert rcr['Rank'] == 3
        assert rcr['BestTime'] == '0:1:40.3000'
        # Rank 4
        rcr = round_result['RacerResults'][3]
        assert rcr['Nick'] == "Racer4"
        assert rcr['Rank'] == 4
        assert rcr.get('BestTime') is None
        # Rank 5
        rcr = round_result['RacerResults'][4]
        assert rcr['Nick'] == "Racer5"
        assert rcr['Rank'] == 5
        assert rcr.get('BestTime') is None