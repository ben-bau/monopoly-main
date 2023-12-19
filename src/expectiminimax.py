from itertools import chain, combinations
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
    if depth > 5:
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
def GenerateChildNodes(node,player,board):
    for i in range(2,13):
        newBoard = copy.deepcopy(board)
        for players in newBoard.players:
            if players.name == player.name:
                players.static_make_a_move(newBoard,i)
                node.children.append(Node(newBoard))
    return node.children


def ExpectiMiniMaxSearch(node, depth, board,player,max_player, is_max):
    if IsCutoff(depth, board) or not GetActions(board,player):
        return Eval(max_player,board)
    for actions in GetActions(board,player):
        player.action_list = actions
        newBoard = copy.deepcopy(board)
        for players in newBoard.players:
            if players.name == player.name:
                newPlayer = players.name
        move = newPlayer.make_a_move(newBoard) 
        while(move):
            newPlayer.action_list = actions
            move = newPlayer.make_a_move(newBoard)
        node.children.append(Node(newBoard))
    if is_max:
        child_values = []
        for child in node.children:
            child_values.append(ExpectiMiniMaxSearch(child,depth+1,newBoard,getNextPlayer(player),max_player,False))
        return max(child_values)