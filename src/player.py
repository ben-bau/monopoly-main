from .cells import Property
from .util.configs import *
from .util.common import *
import progressbar
import random
from .board import Board
from .expectiminimax import GetActions, powerset
from statistics import mean
from src.util import *
from copy import deepcopy
import time

BANK_NAME = "BANK"


class Player:
    """Player class"""

    def __init__(self, name, starting_money, behaviour, simulation_conf, write_log, log):
        self.name = name
        self.write_log = write_log
        self.log = log
        self.position = 0
        self.money = starting_money
        self.consequent_doubles = 0
        self.in_jail = False
        self.days_in_jail = 0
        self.has_jail_card_chance = False
        self.has_jail_card_community = False
        self.is_bankrupt = False
        self.has_mortgages = []
        self.plots_wanted = []
        self.plots_offered = []
        self.plots_to_build = []
        self.cash_limit = behaviour.unspendable_cash
        self.behaviour = behaviour
        self.sim_conf = simulation_conf
        self.turns = 0 # for advanced jail strat
        self.action_list = []
        self.mcts_sim = False # for MCTS simulations, determine if current play is MCTS sim or real game
        self.mcts_count = 0 # Keep track of number of MCTS sims done
        self.mcts_single_move = False

    def __str__(self):
        return (
            "Player: "
            + self.name
            + ". Position: "
            + str(self.position)
            + ". Money: $"
            + str(self.money)
        )

    def get_money(self):
        return self.money

    def get_name(self):
        return self.name
    
    def add_turn(self):
        self.turns += 1

    # add money (salary, receive rent etc)
    def add_money(self, amount):
        self.money += amount

    # subtract money (pay rent, buy property etc)
    def take_money(self, amount, board, action_origin):
        amount_taken = min(self.money, amount)
        self.money -= amount
        final_account_balance = self.money
        self.check_bankruptcy(board, action_origin)
        if self.is_bankrupt:
            amount_taken += self.money - final_account_balance
        else:
            amount_taken = amount
        return amount_taken

    # subtract money (pay rent, buy property etc)
    def move_to(self, position):
        self.position = position
        if self.write_log:
            self.log.write(self.name + " moves to cell " + str(position), 3)

    # Calulate utility of current player
    def calc_self_utility(self, board):
        player_utilities = board.calcPlayerUtilities()
        self_utility = 0
        for player in player_utilities:
            # Add current players utility unscaled
            if player == self.name:
                self_utility += player_utilities[player]
            # Subtract scaled utility of every other player 
            else:
                self_utility -= (player_utilities[player] / 10)
        return self_utility

    # simulate one game from already in-progress point of a game, for MCTS
    def MCTS_one_game(self, run_number, board):    
        sim_conf = SimulationConfig()
        # create copy of board for simulation
        game_board = deepcopy(board)
        players = game_board.players

        # Get and perform random available action(s) for player
        # actions_powerset = GetActions(game_board, self)
        actions_powerset = powerset(["2waytrade", "3waytrade", "hasMortgage", "improveProperty"])
        action_choice = random.choice(actions_powerset)
        players[0].action_list = action_choice
        # Perform the single specified move, then playout game as normal behavior
        players[0].mcts_single_move = True
        while players[0].make_a_move(game_board):
            pass
        
        # Since self got an extra turn, give everyone else a turn
        for player in players[1::]:
                if not is_game_over(players):  # Only continue if 2 or more players
                    # returns True if player has to go again
                    while player.make_a_move(game_board):
                        pass

        last_turn = None
        # Complete the rest of the game simulation
        for i in range(self.turns, sim_conf.n_moves): # Subtract number of already played turns
            
            last_turn = i - 1

            if is_game_over(players) or self.is_bankrupt:
                break

            for player in players:
                if not is_game_over(players):  # Only continue if 2 or more players
                    # returns True if player has to go again
                    while player.make_a_move(game_board):
                        pass

        # tests
        # for player in players:
        # player.three_way_trade(gameBoard)

        # Revert back to MCTS behavior after game playout as normal player
        player[0].behaviour = MCTSPlayerBehaviourConfig(0)

        # return final scores and action(s) causing that
        results = [players[i].get_money() for i in range(sim_conf.n_players)]
        return results, last_turn, action_choice

    def MCTS_run_sim(self, board):
        sim_conf = SimulationConfig()

        results = []
        game_lengths = []
        i = 0
        tracking_winners = [0]*sim_conf.n_players

        MCTS_tracking = {}

        # timeout = 1 # How long each MCTS sim will run (seconds)
        # timeout_start = time.time()
        for i in range(sim_conf.MCTS_simulations):
            # If time runs out
            # if time.time() > timeout_start + timeout:
            #     break        
            
            # remaining players - add to the results list
            game_result = self.MCTS_one_game(i, board)
            print(f"Game result: {game_result}")
            results.append(game_result)

            # determine winner
            ending_net_worth, last_turn, actions = game_result
            if (last_turn != sim_conf.MCTS_simulations - 2):
                game_lengths.append(last_turn)
            
            winner_result_map = list(enumerate(ending_net_worth))
            winner_result_map = sorted(list(winner_result_map), reverse=True, key=lambda x: x[1])

            if (winner_result_map[1][1] < 0):
                tracking_winners[winner_result_map[0][0]] += 1

            print(f"Tracking Winners: {tracking_winners}")

            # Add/update actions and result from MCTS simulated game based on win or loss
            if tuple(actions) in MCTS_tracking:
                if self.is_bankrupt:
                    MCTS_tracking[tuple(actions)] -= 1
                else:
                    MCTS_tracking[tuple(actions)] += 2
            else:
                if self.is_bankrupt:
                    MCTS_tracking[tuple(actions)] = 1
                else:
                    MCTS_tracking[tuple(actions)] = 2

        # Get the action(s) with the best results(most wins)
        max_action = list(max(MCTS_tracking, key=MCTS_tracking.get))

        print(f"MCTS Winners distribution (A, B, C, D ...) across {len(game_lengths)} games that finished:")
        print(tracking_winners)

        if sum(game_lengths) > 0:
            print(f"Average game length: {mean(game_lengths)} (excluding games that did not finish).")
            print(f"MCTS simulation count: {self.mcts_count}, MCTS Result: {max_action}: {MCTS_tracking[tuple(max_action)]}")
        else:
            print("No games finished.")

        # Leaving MCTS simulation
        self.mcts_sim = False
        # Return key(actions) that resulted in most wins
        return max_action

    # make a move procedure
    def static_make_a_move(self, board, dieval):
        goAgain = False
        justLeftJail = False
        if dieval == 2:
            dice1 = 0
            dice2 = 2
        else:
            dice1 = dieval-1
            dice2  = 1
        # Only proceed if player is alive (not bankrupt)
        if self.is_bankrupt:
            return

        # to track the popular cells to land
        if self.sim_conf.write_mode == WriteMode.CELL_HEATMAP:
            self.log.write(str(self.position), data=True)

        self.log.write("Player " + self.name + " goes:", 2)

        # non-board actions: Trade, unmortgage, build
        # repay mortgage if you have X times more cash than mortgage cost
        if (self.behaviour.random and random.randint(0, 1)) or "hasMortgage" in self.action_list or self.behaviour.rule_based:
            while self.repay_mortgage(board):
                    board.recalculateAfterPropertyChange()

        # build houses while you have spare cash
        if (self.behaviour.random and random.randint(0, 1)) or "improveProperty" in self.action_list or self.behaviour.rule_based:
            while board.improveProperty(self, board, self.money - self.cash_limit):
                pass
        

        # Calculate property player wants to get and ready to give away
        if self.behaviour.refuse_to_trade:
                pass  # Experiement: do not trade
        elif (not self.behaviour.refuse_to_trade and ((self.behaviour.random and random.randint(0, 1))) or self.behaviour.rule_based):
            #  Make a trade
            if (
                not self.two_way_trade(board)
                and self.sim_conf.n_players >= 3
                and self.behaviour.three_way_trade
            ):
                self.three_way_trade(board)
        if ("2waytrade" in self.action_list):
            self.two_way_trade(board)
        if ("3waytrade" in self.action_list):
            self.three_way_trade(board)
        # roll dice
        
        self.add_turn()

        # Jail situation:
        # Stay unless you roll doubles, unless advanced behavior
        if self.in_jail:
            # If early on in game, get out ASAP if you have enough to buy properties after
            if self.behaviour.advanced_jail_strat and self.turns <= 20:
                # Try using GOOJF cards first
                if self.has_jail_card_chance:
                    self.has_jail_card_chance = False
                    board.chanceCards.append(1)  # return the card
                    self.log.write(
                        self.name + " uses the Chance GOOJF card to get out of jail", 3
                    )
                elif self.has_jail_card_community:
                    self.has_jail_card_community = False
                    board.communityCards.append(6)  # return the card
                    self.log.write(
                    self.name + " uses the Community GOOJF card to get out of jail", 3
                    )
                # Else if you have enough to buy a property outside of it, pay fine
                elif self.money >= (140 + board.game_conf.jail_fine):
                    self.take_money(
                        board.game_conf.jail_fine, board, BANK_NAME
                    )  # get out on fine
                    self.days_in_jail = 0
                    self.log.write(self.name + " pays fine and gets out of jail", 3)
                # If no other methods work, doubles needed
                elif dice1 != dice2:
                    self.days_in_jail += 1
                    if self.days_in_jail < 3:
                        self.log.write(self.name + " spends this turn in jail", 3)
                        return False  # skip turn in jail
                    else:
                        self.take_money(
                            board.game_conf.jail_fine, board, BANK_NAME
                        )  # get out on fine
                        self.days_in_jail = 0
                        self.log.write(self.name + " pays fine and gets out of jail", 3)
                else:  # get out of jail on doubles
                    self.log.write(self.name + " rolls double and gets out of jail", 3)
                    self.days_in_jail = 0
                    goAgain = False
                    justLeftJail = True
            # If late game, stay in jail as long as possible by just rolling(not using GOOJF card)
            elif self.behaviour.advanced_jail_strat and self.turns >= 40:
                if dice1 != dice2:
                    self.days_in_jail += 1
                    if self.days_in_jail < 3:
                        self.log.write(self.name + " spends this turn in jail", 3)
                        return False  # skip turn in jail
                    else:
                        self.take_money(
                            board.game_conf.jail_fine, board, BANK_NAME
                        )  # get out on fine
                        self.days_in_jail = 0
                        self.log.write(self.name + " pays fine and gets out of jail", 3)
                else:  # get out of jail on doubles
                    self.log.write(self.name + " rolls double and gets out of jail", 3)
                    self.days_in_jail = 0
                    goAgain = False
                    justLeftJail = True
            # If not advanced strat or midgame, stay in jail unless GOOJF card
            else:
                if self.has_jail_card_chance and ((self.behaviour.random and random.randint(0, 1)) or not self.behaviour.random):
                    self.has_jail_card_chance = False
                    board.chanceCards.append(1)  # return the card
                    self.log.write(
                        self.name + " uses the Chance GOOJF card to get out of jail", 3
                    )
                elif self.has_jail_card_community and ((self.behaviour.random and random.randint(0, 1)) or not self.behaviour.random):
                    self.has_jail_card_community = False
                    board.communityCards.append(6)  # return the card
                    self.log.write(
                        self.name + " uses the Community GOOJF card to get out of jail", 3
                    )
                # If random behavior, random chance to pay fine
                elif self.behaviour.random and random.randint(0, 1):
                    self.take_money(
                        board.game_conf.jail_fine, board, BANK_NAME
                    )  # get out on fine
                    self.days_in_jail = 0
                    self.log.write(self.name + " pays fine and gets out of jail", 3)
                elif dice1 != dice2:
                    self.days_in_jail += 1
                    if self.days_in_jail < 3:
                        self.log.write(self.name + " spends this turn in jail", 3)
                        return False  # skip turn in jail
                    else:
                        self.take_money(
                            board.game_conf.jail_fine, board, BANK_NAME
                        )  # get out on fine
                        self.days_in_jail = 0
                        self.log.write(self.name + " pays fine and gets out of jail", 3)
                else:  # get out of jail on doubles
                    self.log.write(self.name + " rolls double and gets out of jail", 3)
                    self.days_in_jail = 0
                    goAgain = False
                    justLeftJail = True
            self.in_jail = False

        # doubles, don't count if rolled in jail
        if dice1 == dice2 and not self.in_jail and not justLeftJail:
            goAgain = True  # go again if doubles
            self.consequent_doubles += 1
            self.log.write(
                "it's a number " + str(self.consequent_doubles) + " double in a row", 3
            )
            if self.consequent_doubles == 3:  # but go to jail if 3 times in a row
                self.in_jail = True
                self.log.write(self.name + " goes to jail on consequtive doubles", 3)
                self.move_to(10)
                self.consequent_doubles = 0
                return False
        else:
            self.consequent_doubles = 0  # reset doubles counter

        # move the piece
        self.position += dice1 + dice2

        # correction of the position if landed on GO or overshoot GO
        if self.position >= 40:
            # calculate correct cell
            self.position = self.position - 40
            # get salary for passing GO
            self.add_money(board.game_conf.salary)
            self.log.write(
                self.name + " gets salary: $" + str(board.game_conf.salary), 3
            )

        self.log.write(
            self.name
            + " moves to cell "
            + str(self.position)
            + ": "
            + board.b[self.position].name
            + (
                " (" + board.b[self.position].owner.name + ")"
                if type(board.b[self.position]) == Property
                and board.b[self.position].owner != ""
                else ""
            ),
            3,
        )

        # perform action of the cell player ended on
        board.action(self, self.position)

        if self.action_list:
            self.action_list.clear()

        if goAgain:
            self.log.write(self.name + " will go again now", 3)
            return True  # make a move again
        return False  # no extra move

        
    def make_a_move(self, board):
        goAgain = False
        justLeftJail = False

        # Only proceed if player is alive (not bankrupt)
        if self.is_bankrupt:
            return
        
        # If MCTS player, run simulations
        if self.behaviour.mcts and not self.mcts_sim:
            self.mcts_sim = True # We are entering MCTS simulation, don't want to recurse
            # Update actions with best actions found from MCTS
            self.action_list = self.MCTS_run_sim(board)
            self.mcts_count += 1

        # to track the popular cells to land
        if self.sim_conf.write_mode == WriteMode.CELL_HEATMAP and self.write_log:
            self.log.write(str(self.position), data=True)

        if self.write_log:
            self.log.write("Player " + self.name + " goes:", 2)

        # non-board actions: Trade, unmortgage, build
        # repay mortgage if you have X times more cash than mortgage cost
        if (self.behaviour.random and random.randint(0, 1)) or "hasMortgage" in self.action_list or self.behaviour.rule_based:
            while self.repay_mortgage(board):
                board.recalculateAfterPropertyChange()

        # build houses while you have spare cash
        if (self.behaviour.random and random.randint(0, 1)) or "improveProperty" in self.action_list or self.behaviour.rule_based:
            while board.improveProperty(self, board, self.money - self.cash_limit):
                pass
        

        # Calculate property player wants to get and ready to give away
        if self.behaviour.refuse_to_trade:
                pass  # Experiement: do not trade
        elif (self.behaviour.random and random.randint(0, 1)) or self.behaviour.rule_based or "2waytrade" in self.action_list:
            #  Make a trade, if not able to do 2 try 3 player
            if not self.two_way_trade(board):
                if ( # If expectiminimax behaviour
                    "3waytrade" in self.action_list
                    and self.sim_conf.n_players >= 3
                    and self.behaviour.three_way_trade
                ):
                    self.three_way_trade(board)
                elif ( # If other behavior
                    not self.behaviour.expectiminimax 
                    and self.sim_conf.n_players >= 3
                    and self.behaviour.three_way_trade
                ):
                    self.three_way_trade(board)

        # roll dice
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
    

        if self.write_log:
            self.log.write(
            self.name
            + " rolls "
            + str(dice1)
            + " and "
            + str(dice2)
            + " = "
            + str(dice1 + dice2),
            3,
            )
        self.add_turn()

        # Jail situation:
        # Stay unless you roll doubles, unless advanced behavior
        if self.in_jail:
            # If early on in game, get out ASAP if you have enough to buy properties after
            if self.behaviour.advanced_jail_strat and self.turns <= 20:
                # Try using GOOJF cards first
                if self.has_jail_card_chance:
                    self.has_jail_card_chance = False
                    board.chanceCards.append(1)  # return the card
                    if self.write_log:
                        self.log.write(
                            self.name + " uses the Chance GOOJF card to get out of jail", 3
                        )
                elif self.has_jail_card_community:
                    self.has_jail_card_community = False
                    board.communityCards.append(6)  # return the card
                    if self.write_log:
                        self.log.write(
                            self.name + " uses the Community GOOJF card to get out of jail", 3
                        )
                # Else if you have enough to buy a property outside of it, pay fine
                elif self.money >= (140 + board.game_conf.jail_fine):
                    self.take_money(
                        board.game_conf.jail_fine, board, BANK_NAME
                    )  # get out on fine
                    self.days_in_jail = 0
                    if self.write_log:
                        self.log.write(self.name + " pays fine and gets out of jail", 3)
                # If no other methods work, doubles needed
                elif dice1 != dice2:
                    self.days_in_jail += 1
                    if self.days_in_jail < 3:
                        if self.write_log:
                            self.log.write(self.name + " spends this turn in jail", 3)
                        return False  # skip turn in jail
                    else:
                        self.take_money(
                            board.game_conf.jail_fine, board, BANK_NAME
                        )  # get out on fine
                        self.days_in_jail = 0
                        if self.write_log:
                            self.log.write(self.name + " pays fine and gets out of jail", 3)
                else:  # get out of jail on doubles
                    if self.write_log:
                        self.log.write(self.name + " rolls double and gets out of jail", 3)
                    self.days_in_jail = 0
                    goAgain = False
                    justLeftJail = True
            # If late game, stay in jail as long as possible by just rolling(not using GOOJF card)
            elif self.behaviour.advanced_jail_strat and self.turns >= 40:
                if dice1 != dice2:
                    self.days_in_jail += 1
                    if self.days_in_jail < 3:
                        if self.write_log:
                            self.log.write(self.name + " spends this turn in jail", 3)
                        return False  # skip turn in jail
                    else:
                        self.take_money(
                            board.game_conf.jail_fine, board, BANK_NAME
                        )  # get out on fine
                        self.days_in_jail = 0
                        if self.write_log:
                            self.log.write(self.name + " pays fine and gets out of jail", 3)
                else:  # get out of jail on doubles
                    if self.write_log:
                        self.log.write(self.name + " rolls double and gets out of jail", 3)
                    self.days_in_jail = 0
                    goAgain = False
                    justLeftJail = True
            # If not advanced strat or midgame, stay in jail unless GOOJF card
            else:
                if self.has_jail_card_chance and ((self.behaviour.random and random.randint(0, 1)) or not self.behaviour.random):
                    self.has_jail_card_chance = False
                    board.chanceCards.append(1)  # return the card
                    if self.write_log:
                        self.log.write(
                            self.name + " uses the Chance GOOJF card to get out of jail", 3
                        )
                elif self.has_jail_card_community and ((self.behaviour.random and random.randint(0, 1)) or not self.behaviour.random):
                    self.has_jail_card_community = False
                    board.communityCards.append(6)  # return the card
                    if self.write_log:
                        self.log.write(
                            self.name + " uses the Community GOOJF card to get out of jail", 3
                        )
                # If random behavior, random chance to pay fine
                elif self.behaviour.random and random.randint(0, 1):
                    self.take_money(
                        board.game_conf.jail_fine, board, BANK_NAME
                    )  # get out on fine
                    self.days_in_jail = 0
                    if self.write_log:
                        self.log.write(self.name + " pays fine and gets out of jail", 3)
                elif dice1 != dice2:
                    self.days_in_jail += 1
                    if self.days_in_jail < 3:
                        if self.write_log:
                            self.log.write(self.name + " spends this turn in jail", 3)
                        return False  # skip turn in jail
                    else:
                        self.take_money(
                            board.game_conf.jail_fine, board, BANK_NAME
                        )  # get out on fine
                        self.days_in_jail = 0
                        if self.write_log:
                            self.log.write(self.name + " pays fine and gets out of jail", 3)
                else:  # get out of jail on doubles
                    if self.write_log:
                        self.log.write(self.name + " rolls double and gets out of jail", 3)
                    self.days_in_jail = 0
                    goAgain = False
                    justLeftJail = True
            self.in_jail = False

        # doubles, don't count if rolled in jail
        if dice1 == dice2 and not self.in_jail and not justLeftJail:
            goAgain = True  # go again if doubles
            self.consequent_doubles += 1
            if self.write_log:
                self.log.write(
                    "it's a number " + str(self.consequent_doubles) + " double in a row", 3
                )
            if self.consequent_doubles == 3:  # but go to jail if 3 times in a row
                self.in_jail = True
                if self.write_log:
                    self.log.write(self.name + " goes to jail on consequtive doubles", 3)
                self.move_to(10)
                self.consequent_doubles = 0
                return False
        else:
            self.consequent_doubles = 0  # reset doubles counter

        # move the piece
        self.position += dice1 + dice2

        # correction of the position if landed on GO or overshoot GO
        if self.position >= 40:
            # calculate correct cell
            self.position = self.position - 40
            # get salary for passing GO
            self.add_money(board.game_conf.salary)
            if self.write_log:
                self.log.write(
                    self.name + " gets salary: $" + str(board.game_conf.salary), 3
                )

        if self.write_log:
                self.log.write(
                    self.name
                    + " moves to cell "
                    + str(self.position)
                    + ": "
                    + board.b[self.position].name
                    + (
                        " (" + board.b[self.position].owner.name + ")"
                        if type(board.b[self.position]) == Property
                        and board.b[self.position].owner != ""
                        else ""
                    ),
                    3,
                )

        # perform action of the cell player ended on
        board.action(self, self.position)

        # if this move was the specified MCTS action, revert to normal behavior
        if self.mcts_single_move:
            self.mcts_single_move = False
            self.behaviour = PlayerBehaviourConfig(0)
            self.action_list = []
            print("MCTS player switched to normal")

        if goAgain:
            if self.write_log:
                self.log.write(self.name + " will go again now", 3)
            return True  # make a move again
        return False  # no extra move

        if self.action_list:
            self.action_list.clear()
    # get the cheapest mortgage property (name, price)

    def cheapest_mortgage(self):
        cheapest = False
        for mortgage in self.has_mortgages:
            if not cheapest or mortgage[1] < cheapest[1]:
                cheapest = mortgage
        return cheapest

    # Chance card make general repairs: 25/house 100/hotel
    def make_repairs(self, board, repairtype):
        repairCost = 0
        if repairtype == "chance":
            perHouse, perHotel = 25, 100
        else:
            perHouse, perHotel = 40, 115
        if self.write_log:
                self.log.write(
                    "Repair cost: $"
                    + str(perHouse)
                    + " per house, $"
                    + str(perHotel)
                    + " per hotel",
                    3,
                )

        for plot in board.b:
            if type(plot) == Property and plot.owner == self:
                if plot.hasHouses == 5:
                    repairCost += perHotel
                else:
                    repairCost += plot.hasHouses * perHouse
        self.take_money(repairCost, board, BANK_NAME)
        if self.write_log:
            self.log.write(self.name + " pays total repair costs $" + str(repairCost), 3)

    # check if player has negative money
    # if so, start selling stuff and mortgage plots
    # if that's not enough, player bankrupt

    def check_bankruptcy(self, board, bankrupter):
        if self.money < 0:
            if self.write_log:
                self.log.write(self.name + " doesn't have enough cash", 3)
            while self.money < 0:
                worstAsset = board.choosePropertyToMortgageDowngrade(self)
                if worstAsset == False:
                    self.is_bankrupt = True
                    if (
                        bankrupter == BANK_NAME
                        or board.game_conf.bankruptcy_goes_to_bank
                    ):
                        board.sellAll(self)
                        if self.write_log:
                            self.log.write(
                                "The bank bankrupted "
                                + self.name
                                + ". Their property is back on the board",
                                3,
                            )
                    elif bankrupter == "noone":
                        if self.write_log:
                            self.log.write("that shouldn't have happened...", 3)
                    else:
                        board.sellAll(self, bankrupter)
                        if self.write_log:
                            self.log.write(
                                self.name
                                + " is now bankrupt. "
                                + bankrupter.name
                                + " bankrupted them",
                                3,
                            )
                    board.recalculateAfterPropertyChange()

                    # to track players who lost
                    if self.sim_conf.write_mode == WriteMode.LOSERS:
                        if self.write_log:
                            self.log.write(self.name, data=True)

                    # to track cells to land one last time
                    if self.sim_conf.write_mode == WriteMode.CELL_HEATMAP:
                        if self.write_log:
                            self.log.write(str(self.position), data=True)

                    return
                else:
                    board.b[worstAsset].mortgage(self, board)
                    board.recalculateAfterPropertyChange()

    # Calculate net worth of a player (for property tax)
    def net_worth(self, board):
        worth = self.money
        for plot in board.b:
            if type(plot) == Property and plot.owner == self:
                if plot.isMortgaged:
                    worth += plot.cost_base // 2
                else:
                    worth += plot.cost_base
                    worth += plot.cost_house * plot.hasHouses
        return worth

    # Behaviours

    # if there is a mortgage with pay less then current money // behaveUnmortgageCoeff
    # repay the mortgage
    def repay_mortgage(self, board):
        cheapest = self.cheapest_mortgage()
        if cheapest and self.money > cheapest[1] * self.behaviour.unmortgage_coeff:
            cheapest[0].unmortgage(self, board)
            return True
        return False

    # does player want to buy a property
    def wants_to_buy(self, base_cost, cost, group, board):
        if self.name == "exp" and group == expRefuseProperty:
            if self.write_log:
                self.log.write(
                    self.name + " refuses to buy " + expRefuseProperty + " property", 3
                )
            return False

        # If a player already has a property then they
        # are willing to pay up to double the value of
        # the property in an auction in order to have
        # that property. Otherwise they are only
        # willing to pay up to the bank value of the
        # property.
        groups = {}
        for plot in board.b:
            if plot.group == group:
                if plot.group in groups:
                    groups[plot.group][0] += 1
                else:
                    groups[plot.group] = [1, 0]
                if plot.owner == self:
                    groups[plot.group][1] += 1
        if groups[group][1] >= 1:
            if self.money > cost + self.cash_limit and cost <= base_cost * 2:
                return True
            else:
                return False
        else:
            if self.money > cost + self.cash_limit and cost <= base_cost:
                return True
            else:
                return False
    
    def look_for_two_way_trade(self,board):
        trade_happened = False
        for IWant in self.plots_wanted[::-1]:
            ownerOfWanted = board.b[IWant].owner
            if ownerOfWanted == "":
                continue
            # Find a match betwee what I want / they want / I have / they have
            for TheyWant in ownerOfWanted.plots_wanted[::-1]:
                if (
                    TheyWant in self.plots_offered
                    and board.b[IWant].group != board.b[TheyWant].group
                ):  # prevent exchanging in groups of 2
                    # Compensate that one plot is cheaper than another one
                    if board.b[IWant].cost_base < board.b[TheyWant].cost_base:
                        cheaperOne, expensiveOne = IWant, TheyWant
                    else:
                        cheaperOne, expensiveOne = TheyWant, IWant
                    priceDiff = (
                        board.b[expensiveOne].cost_base - board.b[cheaperOne].cost_base
                    )
                    if (
                        board.b[cheaperOne].owner.money - priceDiff
                        >= board.b[cheaperOne].owner.cash_limit
                    ):
                        trade_happened = True
        return trade_happened
    
    # Look for and perform a two-way trade
    def two_way_trade(self, board):
        trade_happened = False
        for IWant in self.plots_wanted[::-1]:
            ownerOfWanted = board.b[IWant].owner
            if ownerOfWanted == "":
                continue
            # Find a match betwee what I want / they want / I have / they have
            for TheyWant in ownerOfWanted.plots_wanted[::-1]:
                if (
                    TheyWant in self.plots_offered
                    and board.b[IWant].group != board.b[TheyWant].group
                ):  # prevent exchanging in groups of 2
                    if self.write_log:
                        self.log.write(
                            "Trade match: "
                            + self.name
                            + " wants "
                            + board.b[IWant].name
                            + ", and "
                            + ownerOfWanted.name
                            + " wants "
                            + board.b[TheyWant].name,
                            3,
                        )

                    # Compensate that one plot is cheaper than another one
                    if board.b[IWant].cost_base < board.b[TheyWant].cost_base:
                        cheaperOne, expensiveOne = IWant, TheyWant
                    else:
                        cheaperOne, expensiveOne = TheyWant, IWant
                    priceDiff = (
                        board.b[expensiveOne].cost_base - board.b[cheaperOne].cost_base
                    )
                    if self.write_log:
                        self.log.write("Price difference is $" + str(priceDiff), 3)

                    # make sure they they can pay the money
                    if (
                        board.b[cheaperOne].owner.money - priceDiff
                        >= board.b[cheaperOne].owner.cash_limit
                    ):
                        if self.write_log:
                            self.log.write(
                                "We have a deal. Money and property changed hands", 3
                            )
                        # Money and property change hands
                        board.b[cheaperOne].owner.take_money(priceDiff, board, "noone")
                        board.b[expensiveOne].owner.add_money(priceDiff)
                        board.b[cheaperOne].owner, board.b[expensiveOne].owner = (
                            board.b[expensiveOne].owner,
                            board.b[cheaperOne].owner,
                        )
                        trade_happened = True

                        # recalculated wanted and offered plots
                        board.recalculateAfterPropertyChange()
        return trade_happened

    def look_for_three_way_trade(self, board):
        """Look for and perform a three-way trade"""
        trade_happened = False
        for wanted1 in self.plots_wanted[::-1]:
            first_owner_of_wanted = board.b[wanted1].owner
            if first_owner_of_wanted == "":
                continue
            for wanted2 in first_owner_of_wanted.plots_wanted[::-1]:
                second_owner_of_wanted = board.b[wanted2].owner
                if second_owner_of_wanted == "":
                    continue
                for wanted3 in second_owner_of_wanted.plots_wanted[::-1]:
                    if wanted3 in self.plots_offered:
                        # check we have property from 3 groups
                        # otherwise someone can give and take brown or indigo at the same time
                        check_diff_group = set()
                        check_diff_group.add(board.b[wanted1].group)
                        check_diff_group.add(board.b[wanted2].group)
                        check_diff_group.add(board.b[wanted3].group)
                        if len(check_diff_group) < 3:
                            continue

                        topay1 = board.b[wanted1].cost_base - board.b[wanted3].cost_base
                        topay2 = board.b[wanted2].cost_base - board.b[wanted1].cost_base
                        topay3 = board.b[wanted3].cost_base - board.b[wanted2].cost_base
                        if (
                            self.money - topay1 > self.cash_limit
                            and first_owner_of_wanted.money - topay2
                            > first_owner_of_wanted.cash_limit
                            and first_owner_of_wanted.money - topay3
                            > second_owner_of_wanted.cash_limit
                        ):
                            tradeHappened = True
                            
        return trade_happened
    def three_way_trade(self, board):
        """Look for and perform a three-way trade"""
        trade_happened = False
        for wanted1 in self.plots_wanted[::-1]:
            first_owner_of_wanted = board.b[wanted1].owner
            if first_owner_of_wanted == "":
                continue
            for wanted2 in first_owner_of_wanted.plots_wanted[::-1]:
                second_owner_of_wanted = board.b[wanted2].owner
                if second_owner_of_wanted == "":
                    continue
                for wanted3 in second_owner_of_wanted.plots_wanted[::-1]:
                    if wanted3 in self.plots_offered:
                        # check we have property from 3 groups
                        # otherwise someone can give and take brown or indigo at the same time
                        check_diff_group = set()
                        check_diff_group.add(board.b[wanted1].group)
                        check_diff_group.add(board.b[wanted2].group)
                        check_diff_group.add(board.b[wanted3].group)
                        if len(check_diff_group) < 3:
                            continue

                        topay1 = board.b[wanted1].cost_base - board.b[wanted3].cost_base
                        topay2 = board.b[wanted2].cost_base - board.b[wanted1].cost_base
                        topay3 = board.b[wanted3].cost_base - board.b[wanted2].cost_base
                        if (
                            self.money - topay1 > self.cash_limit
                            and first_owner_of_wanted.money - topay2
                            > first_owner_of_wanted.cash_limit
                            and first_owner_of_wanted.money - topay3
                            > second_owner_of_wanted.cash_limit
                        ):
                            if self.write_log:
                                self.log.write("Three way trade: ", 3)
                                self.log.write(
                                    self.name
                                    + " gives "
                                    + board.b[wanted3].name
                                    + " and $"
                                    + str(topay1)
                                    + " for "
                                    + board.b[wanted1].name,
                                    4,
                                )
                                self.log.write(
                                    first_owner_of_wanted.name
                                    + " gives "
                                    + board.b[wanted1].name
                                    + " and $"
                                    + str(topay2)
                                    + " for "
                                    + board.b[wanted2].name,
                                    4,
                                )
                                self.log.write(
                                    second_owner_of_wanted.name
                                    + " gives "
                                    + board.b[wanted2].name
                                    + " and $"
                                    + str(topay3)
                                    + " for "
                                    + board.b[wanted3].name,
                                    4,
                                )
                            # Money and property change hands
                            board.b[wanted1].owner = self
                            board.b[wanted2].owner = first_owner_of_wanted
                            board.b[wanted3].owner = second_owner_of_wanted
                            self.take_money(
                                topay1, board, "noone"
                            )  # guaranteed to have enough money
                            first_owner_of_wanted.take_money(topay2, board, "noone")
                            second_owner_of_wanted.take_money(topay3, board, "noone")
                            tradeHappened = True
                            # recalculated wanted and offered plots
                            board.recalculateAfterPropertyChange()
        return trade_happened
