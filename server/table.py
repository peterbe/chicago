import uuid
import random
from collections import defaultdict

DECK = [x + y for x in
        [str(x) for x in range(2, 11)] + list('JQKA')
        for y in list('SCDH')]

class Table(object):

    def __init__(self, players):
        self.players = players
        self.deck = DECK[:]
        random.shuffle(self.deck)
        self.in_final = False
        #self.changes = 0

    @classmethod
    def new_table_id(cls):
        return uuid.uuid4().get_hex()

    def deal_5_cards_each(self):
        for player in self.players:
            cards = []
            for i in range(5):
                cards.append(self.deck.pop())
            player.cards = cards
            #player.send({'hand': cards})

    def discard(self, player, cards):
        for card in cards:
            player.cards.remove(card)
        player.changes += 1

    def receive_new_cards(self):
        for player in self.players:
            for i in range(5 - len(player.cards)):
                player.cards.append(self.deck.pop())

    def preview_one_card(self):
        return self.deck.pop()

    def get_winner_and_points(self):
        best = []
        for player in self.players:
            best.append((get_best(player.cards), player))

        # if both people had shit cards, don't bother comparing
        if not sum(x[0][0] for x in best):
            return (None, 0)

        best.sort(reverse=True)
        if best[0][0][0] == best[1][0][0]:
            if best[0][0][1] == best[1][0][1]:
                cardnumbers1 = _cards_to_numbers(best[0][1].cards)
                cardnumbers2 = _cards_to_numbers(best[1][1].cards)
                while best[0][0][1] in cardnumbers1:
                    cardnumbers1.remove(best[0][0][1])
                while best[0][0][1] in cardnumbers2:
                    cardnumbers2.remove(best[0][0][1])

                if (sorted(cardnumbers1, reverse=True)[0] >
                    sorted(cardnumbers2, reverse=True)[0]):
                    return best[0][1], best[0][0][0]
                else:
                    return best[1][1], best[1][0][0]
            else:
                if best[0][0][1] > best[1][0][1]:
                    return best[0][1], best[0][0][0]
                else:
                    return best[1][1], best[1][0][0]
        else:
            return best[0][1], best[0][0][0]

def _cards_to_numbers(cards):
    return [int(x[0]
                .replace('J', '11')
                .replace('Q', '12')
                .replace('K', '13')
                .replace('A', '14'))
            for x in cards]

def get_best(cards):
    numbers = _cards_to_numbers(cards)
    repeats = defaultdict(int)
    for number in numbers:
        repeats[number] += 1
    pairs = sorted((v, k) for k, v in repeats.items() if v > 1)

    if 4 in repeats.values():
        # four of a kind
        return (7, pairs[0][1])

    if 2 in repeats.values() and 3 in repeats.values():
        # full house
        return (6, pairs[0][1])

    if len(set(x[1] for x in cards)) == 1:
        # flush
        return (5, sorted(numbers)[-1])

    if sum([max(numbers) - x for x in numbers]) == 10:
        # straight
        return (4, sorted(numbers)[-1])

    if 3 in repeats.values():
        # three of a kind
        return (3, pairs[0][1])

    if 2 in repeats.values():
        # 2 of a kind
        return (repeats.values().count(2),
                sorted(x[1] for x in pairs)[-1])

    return 0, 0


import unittest

class Player:
    def __init__(self, name):
        self.name = name
        self.cards = []


class TestCase(unittest.TestCase):

    def test_get_best(self):
        cards = ['7D', '7H', '7S', '7C', 'JH']
        self.assertEqual(get_best(cards), (7, 7))

        cards = ['7D', '7H', '7S', 'JD', 'JH']
        self.assertEqual(get_best(cards), (6, 11))

        cards = ['7D', '3D', 'JD', 'QD', '2D']
        self.assertEqual(get_best(cards), (5, 12))

        cards = ['4D', '7H', '3D', '5D', '6S']
        self.assertEqual(get_best(cards), (4, 7))

        cards = ['7D', '7H', '3D', '7C', 'JH']
        self.assertEqual(get_best(cards), (3, 7))

        cards = ['7D', '2H', '3D', '7C', '3H']  # 2x 7, 2x 3
        self.assertEqual(get_best(cards), (2, 7))

        cards = ['7D', '2H', '3D', '7C', 'JH']  # 2x 7
        self.assertEqual(get_best(cards), (1, 7))

        cards = ['JD', '2H', '3D', '7C', 'JH']  # 2x J
        self.assertEqual(get_best(cards), (1, 11))

        cards = ['10D', '2H', '3D', '7C', 'JH']
        self.assertEqual(get_best(cards), (0, 0))

    def test_get_winner_and_points(self):
        player1 = Player('player1')
        player2 = Player('player2')
        table = Table([player1, player2])
        for card in ['7D', '7H', '3D', '7S', 'JH']:  # 3 of a kind
            table.deck.remove(card)
            player1.cards.append(card)

        for card in ['4D', '7C', '3C', '5D', '6S']:  # straight
            table.deck.remove(card)
            player2.cards.append(card)

        self.assertEqual(table.get_winner_and_points(),
                         (player2, 4))

    def test_get_winner_and_points_draw1(self):
        player1 = Player('player1')
        player2 = Player('player2')
        table = Table([player1, player2])
        for card in ['7D', '7H', '3D', '7S', 'JH']:  # 3 of a kind
            table.deck.remove(card)
            player1.cards.append(card)

        for card in ['AD', 'AC', 'AH', '5D', '6S']:  # 3 of a kind aces high
            table.deck.remove(card)
            player2.cards.append(card)

        self.assertEqual(table.get_winner_and_points(),
                         (player2, 3))

    def test_get_winner_and_points_draw2(self):
        player1 = Player('player1')
        player2 = Player('player2')
        table = Table([player1, player2])
        for card in ['AD', 'AC', 'AH', '5D', '6S']:  # 3 of a kind aces high
            table.deck.remove(card)
            player1.cards.append(card)

        for card in ['7D', '7H', '3D', '7S', 'JH']:  # 3 of a kind
            table.deck.remove(card)
            player2.cards.append(card)

        self.assertEqual(table.get_winner_and_points(),
                         (player1, 3))

    def test_get_winner_and_points_draw3(self):
        player1 = Player('player1')
        player2 = Player('player2')
        table = Table([player1, player2])
        for card in ['AD', 'AC', '5C', '5D', '6S']:  # 2 of a kind aces high
            table.deck.remove(card)
            player1.cards.append(card)

        for card in ['AS', 'AH', '3D', 'QS', 'QH']:  # 2 of a kind
            table.deck.remove(card)
            player2.cards.append(card)

        self.assertEqual(table.get_winner_and_points(),
                         (player2, 2))

    def test_get_winner_and_points_draw4(self):
        player1 = Player('player1')
        player2 = Player('player2')
        table = Table([player1, player2])
        for card in ['AD', 'AC', '5C', '4D', '6S']:  # 1 of a kind 6 high
            table.deck.remove(card)
            player1.cards.append(card)

        for card in ['AS', 'AH', '3D', 'JS', 'QH']:  # 1 of a kind queen high
            table.deck.remove(card)
            player2.cards.append(card)

        self.assertEqual(table.get_winner_and_points(),
                         (player2, 1))

    def test_get_winner_and_points_both_shit_cards(self):
        player1 = Player('player1')
        player2 = Player('player2')
        table = Table([player1, player2])

        # A, K, J high
        for card in ['7D', 'AS', '8S', 'KD', 'JS']:
            table.deck.remove(card)
            player1.cards.append(card)

        for card in ['AC', '8H', 'KS', 'QS', '10D']:  # 1 of a kind queen high
            table.deck.remove(card)
            player2.cards.append(card)

        self.assertEqual(table.get_winner_and_points(),
                         (None, 0))
