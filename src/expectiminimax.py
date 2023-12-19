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
    if depth > 5:
        return True
    if is_game_over(board.players):
        return True
    return False

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
    if(len(actions) > 1):
        for r in range(2,len(actions)+1):
            newlist = actions
            for i in actions:
                if len(i) == 1:
                    newlist.append(i)
            combos = list(itertools.combinations('ABC', r))
            for j in combos:
                actions.append(j)

    return actions
    
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
        self.chance_val =0 
    def __init__(self, board,chance,prev_move) -> None:
        self.board = board 
        self.children = []
        self.prev_move = prev_move
        self.chance_val = chance
    def getBoard(self):
        return self.board
    




def ExpectiMiniMaxSearch(node, depth, board,player):
    if IsCutoff(depth, board) or not GetActions(board,player):
        return Eval(player,board)
    if node == None:
        node = Node(board)
    for actions in GetActions(board,player):
        player.action_list = actions
        newBoard = copy.deepcopy(board)
        for players in newBoard.players:
            if players.name == player.name:
                newPlayer = players
        newPlayer.takeAction(newBoard)
        node.children.append(Node(newBoard,actions))
    for child in node.children:
        chancevals = {2:1/36,3:2/36,4:3/36,5:4/36,6:5/36,7:1/6,8:5/36,9:4/36,10:3/36,11:3/36,12:1/36}
        for states in range(2,12):
            newBoard = copy.deepcopy(child.getBoard)
            for players in newBoard.players:
                if players.name == player.name:
                    newPlayer = players
            newPlayer.static_make_a_move(newBoard,states)
            newnode = Node(newBoard,chancevals[states],child.prev_move)
            child.children.append(chancevals[states]*ExpectiMiniMaxSearch(newnode,depth+1,newBoard,player.getNextPlayer))
            
    return max(node.children.children)
    if is_max:
        child_values = []
        for child in node.children:
            child_values.append(ExpectiMiniMaxSearch(child,depth+1,newBoard,getNextPlayer(player),max_player,False))
        return max(child_values)