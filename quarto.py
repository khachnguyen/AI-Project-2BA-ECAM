#!/usr/bin/env python3
# quarto.py
# Author: Quentin Lurkin
# Version: March 29, 2018

import argparse
import socket
import sys
import random
import json
import copy

from lib import game
from easyAI import TwoPlayersGame
from easyAI import AI_Player
from easyAI.AI import  TT, SSS, Negamax

class QuartoState(game.GameState):
    '''Class representing a state for the Quarto game.'''
    def __init__(self, initialstate=None, currentPlayer=None):
        self.__player = 0
        random.seed()
        if initialstate is None:
            pieces = []
            for shape in ['round', 'square']:
                for color in ['dark', 'light']:
                    for height in ['low', 'high']:
                        for filling in ['empty', 'full']:
                            pieces.append({
                                'shape': shape,
                                'color': color,
                                'height': height,
                                'filling': filling
                            })
            initialstate = {
                'board': [None] * 16,
                'remainingPieces': pieces,
                'pieceToPlay': None,
                'quartoAnnounced': False
            }

        if currentPlayer is None:
            currentPlayer = random.randrange(2)

        super().__init__(initialstate, currentPlayer=currentPlayer)

    def applymove(self, move):
        #{pos: 8, quarto: true, nextPiece: 2}
        stateBackup = copy.deepcopy(self._state)
        try:
            state = self._state['visible']
            if state['pieceToPlay'] is not None:
                try:
                    if state['board'][move['pos']] is not None:
                        raise game.InvalidMoveException('The position is not free')
                    state['board'][move['pos']] = state['remainingPieces'][state['pieceToPlay']]
                    del(state['remainingPieces'][state['pieceToPlay']])
                except game.InvalidMoveException as e:
                    raise e
                except:
                    raise game.InvalidMoveException("Your move should contain a \"pos\" key in range(16)")

            if len(state['remainingPieces']) > 0:
                try:
                    state['pieceToPlay'] = move['nextPiece']
                except:
                    raise game.InvalidMoveException("You must specify the next piece to play")
            else:
                state['pieceToPlay'] = None

            if 'quarto' in move:
                state['quartoAnnounced'] = move['quarto']
                winner = self.winner()
                if winner is None or winner == -1:
                    raise game.InvalidMoveException("There is no Quarto !")
            else:
                state['quartoAnnounced'] = False
        except game.InvalidMoveException as e:
            self._state = stateBackup
            raise e

    
    def _same(self, feature, elems):
        try:
            elems = list(map(lambda piece: piece[feature], elems))
        except:
            return False
        return all(e == elems[0] for e in elems)

    def _quarto(self, elems):
        return self._same('shape', elems) or self._same('color', elems) or self._same('filling', elems) or self._same('height', elems)
    
    def winner(self):
        state = self._state['visible']
        board = state['board']
        player = self._state['currentPlayer']

        # 00 01 02 03
        # 04 05 06 07
        # 08 09 10 11
        # 12 13 14 15

        if state['quartoAnnounced']:
            # Check horizontal and vertical lines
            for i in range(4):
                if self._quarto([board[4 * i + e] for e in range(4)]):
                    return player
                if self._quarto([board[4 * e + i] for e in range(4)]):
                    return player
            # Check diagonals
            if self._quarto([board[5 * e] for e in range(4)]):
                return player
            if self._quarto([board[3 + 3 * e] for e in range(4)]):
                return player
        return None if board.count(None) == 0 else -1
    
    def displayPiece(self, piece):
        if piece is None:
            return " " * 6
        bracket = ('(', ')') if piece['shape'] == "round" else ('[', ']')
        filling = 'E' if piece['filling'] == 'empty' else 'F'
        color = 'L' if piece['color'] == 'light' else 'D'
        format = ' {}{}{}{} ' if piece['height'] == 'low' else '{0}{0}{1}{2}{3}{3}'
        return format.format(bracket[0], filling, color, bracket[1])

    def prettyprint(self):
        state = self._state['visible']

        print('Board:')
        for row in range(4):
            print('|', end="")
            for col in range(4):
                print(self.displayPiece(state['board'][row*4+col]), end="|")
            print()
        
        print('\nRemaining Pieces:')
        print(", ".join([self.displayPiece(piece) for piece in state['remainingPieces']]))

        if state['pieceToPlay'] is not None:
            print('\nPiece to Play:')
            print(self.displayPiece(state['remainingPieces'][state['pieceToPlay']]))

    def nextPlayer(self):
        self._state['currentPlayer'] = (self._state['currentPlayer'] + 1) % 2


class QuartoServer(game.GameServer):
    '''Class representing a server for the Quarto game.'''
    def __init__(self, verbose=False):
        super().__init__('Quarto', 2, QuartoState(), verbose=verbose)
    
    def applymove(self, move):
        try:
            move = json.loads(move)
        except:
            raise game.InvalidMoveException('A valid move must be a valid JSON string')
        else:
            self._state.applymove(move)

class QuartoClient(game.GameClient):
    '''Class representing a client for the Quarto game.'''
    def __init__(self, name, server, verbose=False):
        super().__init__(server, QuartoState, verbose=verbose)
        self.__name = name
    
    def _handle(self, message):
        pass
    
    def _nextmove(self, state):
        visible = state._state['visible']
        move = {}
          
        #List of the number of free places on the board
        verif = []
        for i in range(4):
            verif.append([visible['board'][4 * i + e] for e in range(4)].count(None))
            verif.append([visible['board'][4 * e + i] for e in range(4)].count(None))
        verif.append([visible['board'][5 * e ] for e in range(4)].count(None))
        verif.append([visible['board'][3 + 3 * e] for e in range(4)].count(None))
        
        #First is a random AI  
        if verif.count(1) == 0 :
            ls_test = [i for i,x in enumerate(visible['board']) if x == None]    
            
            # select a random position
            
            if visible['pieceToPlay'] is not None:
                move['pos'] = random.choice(ls_test)
                
            # select a random piece
            
            test1 = visible['remainingPieces']
            a = random.randint(0,len(test1)-2)
            move['nextPiece'] = a   
            
            # applymove will raise if we announce a quarto while there is not            
            move['quarto'] = True
            try:
                state.applymove(move)
            except:
                del(move['quarto'])
        
            return json.dumps(move)  # send the move
            
        #When the number of free place per line/column/diag is brought down to 1, begin easyAI
        else:
            easyAI.ttentry = lambda self: state 
            ai_algo_neg = Negamax(6, tt=TT(), win_score=90)         # Algorithm
            Quarto = easyAI([AI_Player(ai_algo_neg), AI_Player(ai_algo_neg)], state)
            best_move = Quarto.get_move()        # find the best move possible
            print("BEST MOVE", best_move)
            return json.dumps(best_move)  # send the Move

class easyAI (TwoPlayersGame):
    def __init__(self,players,state): #initialization of the game
        self.state = state
        self.players = players #liste des 2 joueurs
        self.nplayer = 1    
    
    def possible_moves(self) : #returns of all moves allowed
        list_moves = []
        visible = self.state._state['visible']
        for i in range (16):
            for piece in range (len(visible['remainingPieces'])-1) :
                move = {}
                move['pos'] = i
                move['nextPiece'] = piece
                move['quarto'] = True
                if visible['board'][i] is None:
                    try:
                        CopyState = copy.deepcopy(self.state)
                        CopyState.applymove(move)
                    except:
                        del (move['quarto'])
                    list_moves.append(move)
        return list_moves


    def make_move(self, move): #transforms the game according to the move
        visible = self.state._state['visible']
        if visible['board'][move['pos']] is None:
            move['quarto'] = True
            try:
                self.state.applymove(move)
            except:
                del(move['quarto'])
        

    def lose(self):
        return self.state.winner() == self.nopponent

    def is_over(self): #check whether the game has ended
        return self.lose()

    def scoring(self):
        return 100 if self.lose() else 0

        
    

if __name__ == '__main__':
    # Create the top-level parser
    parser = argparse.ArgumentParser(description='Quarto game')
    subparsers = parser.add_subparsers(description='server client', help='Quarto game components', dest='component')
    # Create the parser for the 'server' subcommand
    server_parser = subparsers.add_parser('server', help='launch a server')
    server_parser.add_argument('--host', help='hostname (default: localhost)', default='localhost')
    server_parser.add_argument('--port', help='port to listen on (default: 5000)', default=5000)
    server_parser.add_argument('--verbose', action='store_true')
    # Create the parser for the 'client' subcommand
    client_parser = subparsers.add_parser('client', help='launch a client')
    client_parser.add_argument('name', help='name of the player')
    client_parser.add_argument('--host', help='hostname of the server (default: localhost)', default='127.0.0.1')
    client_parser.add_argument('--port', help='port of the server (default: 5000)', default=5000)
    client_parser.add_argument('--verbose', action='store_true')
    # Parse the arguments of sys.args
    args = parser.parse_args()
    if args.component == 'server':
        QuartoServer(verbose=args.verbose).run()
    else:
        QuartoClient(args.name, (args.host, args.port), verbose=args.verbose)