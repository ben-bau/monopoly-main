import itertools
from .board import Board
import copy
from .player import *

def getNextPlayer(player, board):
    player_index = 0
    for i in range(len(board.players)):
        if board.players[i].name == player.name:
            player_index = i
    if i == len(board.players)-1:
        return  board.players[0]
    else:
        return board.players[player_index+1]
def Eval(player, board):
    player_utilities = board.calcPlayerUtilities()
    self_utility = 0
    for players in player_utilities:
        # Add current players utility unscaled
        if players == player.name:
            self_utility += player_utilities[players]
        # Subtract scaled utility of every other player 
        else:
            self_utility -= (player_utilities[players] / 10)
    return self_utility 

def IsCutoff(depth, board):
    if depth > 7:
        return True
    if is_game_over(board.players):
        return True
    return False

def powerset(some_list):
    """Returns all subsets of size 0 - len(some_list) for some_list"""
    if len(some_list) == 0:
        return [[]]

    subsets = []
    first_element = some_list[0]
    remaining_list = some_list[1:]
    # Strategy: get all the subsets of remaining_list. For each
    # of those subsets, a full subset list will contain both
    # the original subset as well as a version of the subset
    # that contains first_element
    for partial_subset in powerset(remaining_list):
        subsets.append(partial_subset)
        subsets.append(partial_subset[:] + [first_element])

    return subsets

def GetActions(board, player):
    actions = []
    if (player.look_for_two_way_trade(board)):
        actions.append("2waytrade")
    if (player.look_for_three_way_trade(board)):
        actions.append("3waytrade")
    if player.has_mortgages:
        actions.append("hasMortgage")
    propertyToImprove = board.choosePropertyToBuild(player, player.money)
    if type(propertyToImprove) != bool:
        actions.append("improveProperty")
    return powerset(actions)
    
class Node:
    def __init__(self, board) -> None:
        self.board = board 
        self.children = []
        self.prev_move = []
        self.prev_move = []
        self.chance_val =0
    def __init__(self, board,prev_move) -> None:
        self.board = board 
        self.children = []
        self.prev_move = prev_move
    def getBoard(self):
        return self.board

class ChanceNode:
    def __init__(self, board) -> None:
        self.board = board 
        self.children = []
        self.prev_move = []
        self.chance_val =0
    def __init__(self, board,chance) -> None:
        self.board = board 
        self.children = []
        self.prev_move = []
        self.chance_val =chance
    




def ExpectiMiniMaxSearch(node, depth, board,player):
    if IsCutoff(depth, board) or not GetActions(board,player):
        return Eval(player,board)
    if node == None:
        node = Node(board)
    if type(node) == Node:
        val = -100000
        for actions in GetActions(board,player):
            player.action_list = actions
            newBoard = copy.deepcopy(board)
            for players in newBoard.players:
                if players.name == player.name:
                    newPlayer = players
            newPlayer.takeAction(newBoard)
            newnode = ChanceNode(newBoard)
            node.children.append(newnode)
            val1 = max(ExpectiMiniMaxSearch(newnode,depth+1,newBoard,getNextPlayer(newPlayer,newBoard)))
            if val1 > val:
                val = val1
        return val
    if type(node) == ChanceNode:
        value = 0
        chancevals = {2:1/36,3:2/36,4:3/36,5:4/36,6:5/36,7:1/6,8:5/36,9:4/36,10:3/36,11:3/36,12:1/36}
        for states in range(2,12):
            newBoard = copy.deepcopy(board)
            for players in newBoard.players:
                if players.name == player.name:
                    
                    players.static_make_a_move(newBoard,states)
                    newnode = Node(newBoard)
                    value += chancevals[states] * ExpectiMiniMaxSearch(newnode,depth +1,newBoard,getNextPlayer(players,newBoard))
            
        return value