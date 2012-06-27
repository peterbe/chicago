import datetime
from collections import defaultdict
import tornado.options
import tornado.escape
from tornado import web, ioloop
from sockjs.tornado import SockJSRouter, SockJSConnection
from tornado.options import define, options
import redis.client
import settings
import cookies
from table import Table


define("debug", default=False, help="run in debug mode", type=bool)
define("port", default=9999, help="run on the given port", type=int)


class PlayConnection(SockJSConnection):
    _connected = set()
    _waiting = []
    _opponents = defaultdict(list)
    _tables = {}

    @property
    def redis(self):
        global _redis_connection
        if not _redis_connection:
            _redis_connection = redis.client.Redis(settings.REDIS_HOST,
                                                   settings.REDIS_PORT)
        return _redis_connection

    def on_open(self, request):
        cookie_parser = cookies.CookieParser(request)
        username = cookie_parser.get_secure_cookie('user')
        self._connected.add(self)

        if username:
            self._on_register(username)

    def on_message(self, msg):
        try:
            data = tornado.escape.json_decode(msg)
        except ValueError:
            data = msg
        if data.get('register'):
            self._on_register(data.get('register'))
        elif data.get('button'):
            self._on_button(data.get('button'))
        elif 'discard' in data:
            self._on_discard(data.get('discard'))
        elif data.get('refuse'):
            self._on_refuse()
        elif data.get('accept'):
            self._on_accept()
        elif data.get('final_card'):
            self._on_final_card(data.get('final_card'))
        else:
            print "-> DATA", repr(data)
            data['date'] = datetime.datetime.now().strftime('%H:%M:%S')
            opponents = self._opponents.get(self.session, [])
            self.broadcast(opponents + [self], data)

    def on_close(self):
        print "Closing", self.session, getattr(self, 'nick', '*no nick*')
        opponent = self._opponents.get(self.session)
        if opponent:
            opponent.send({'status': self.nick + ' disconnected :(',
                           'color': 'red'})
            del self._opponents[opponent.session]
            del self._opponents[self.session]
        # Remove client from the clients list and broadcast leave message
        self._connected.remove(self)
        #self.broadcast(self.participants, "Someone left.")

    def _on_register(self, username):
        self.nick = username
        self.send({'registered': self.nick})
        #score = self._get_score(self.nick)
        #self.send({'update_score': score})
        while self._waiting:
            opponent = self._waiting.pop()
            if opponent.is_closed:
                continue

            self._opponents[self.session].append(opponent)
            self._opponents[opponent.session].append(self)
            self.send({'status': "playing against " + opponent.nick,
                       'ready': True})
            opponent.send({'status': "playing against " + self.nick,
                           'ready': True})

            table_id = Table.new_table_id()
            players = [self, opponent]
            for player in players:
                player.table_id = table_id
                player.changes = 0
            table = Table(players)
            self._tables[table_id] = table # could be more
            table.deal_5_cards_each()
            for player in table.players:
                player.send({'hand': player.cards})

        else:
            self._waiting.append(self)
            self.send({'status': 'Waiting', 'color': 'orange'})

    def _on_discard(self, cards):
        table = self._tables[self.table_id]
        assert not table.in_final
        print self.nick, "discards", cards
        table.discard(self, cards)

        for other in table.players:
            if other != self:
                other.send({'status': self.nick + ' discarded %s cards' % len(cards)})

        if len(cards) == 1 and not getattr(self, 'preview', None):
            self.to_preview = True

        changes = sum(x.changes for x in table.players)
        if changes == 6:
            table.receive_new_cards()
            for player in table.players:
                player.send({'hand': player.cards})
                player.send({'status': 'Final can begin!'})
            self._start_final(table)

        if changes == 2 or changes == 4:
            if any(getattr(p, 'to_preview', None) for p in table.players):
                for player in table.players:
                    if getattr(player, 'to_preview', None):
                        choice = table.preview_one_card()
                        player.preview = choice
                        player.send({'preview': choice})
                        for other in table.players:
                            if other != player:
                                other.send({'previewed': choice,
                                            'player': player.nick})

            elif 0 and len(cards) == 1 and not getattr(self, 'preview', None):
                choice = table.preview_one_card()
                self.preview = choice
                self.send({'preview': choice})
                for player in table.players:
                    if player != self:
                        player.send({'previewed': choice})
            else:
                table.receive_new_cards()
                for player in table.players:
                    player.send({'hand': player.cards})

                self._pick_points_winner(table)
        else:
            print "changes", changes
        #else:
        #    raise NotImplementedError(changes)

        print "#cards left", len(table.deck)

    def _pick_points_winner(self, table):
        winner, points = table.get_winner_and_points()
        if winner:
            winner.send({'status': 'You won %d points' % points})
            for player in table.players:
                if player != winner:
                    player.send({'status': winner.nick + ' won %d points' % points})
        else:
            for player in table.players:
                player.send({'status': 'No winner and no points awarded'})

    def _on_refuse(self):
        table = self._tables[self.table_id]
        # player was offered...
        assert self.preview
        # but choose to refuse it
#        refused_card = self.preview
        self.preview = None
        self.to_preview = False
        assert len(self.cards) == 4, self.cards
        self.cards.append(table.preview_one_card())
        self.send({'hand': self.cards})
        for player in table.players:
            if player != self:
                player.send({'status': self.nick + ' said no to that card',
                             'refused': True})
        self._oneup_continue(table)


    def _on_accept(self):
        table = self._tables[self.table_id]
        assert self.preview
        assert len(self.cards) == 4, self.cards
        self.cards.append(self.preview)
        self.preview = None
        self.to_preview = False
        self.send({'hand': self.cards})
        for player in table.players:
            if player != self:
                player.send({'status': self.nick + ' accepted that card',
                             'accepted': True})
        self._oneup_continue(table)

    def _oneup_continue(self, table):
        if any(getattr(p, 'to_preview', None) for p in table.players):
            for player in table.players:
                if getattr(player, 'to_preview', None):
                    choice = table.preview_one_card()
                    player.preview = choice
                    player.send({'preview': choice})
                    for other in table.players:
                        if other != player:
                            other.send({'previewed': choice,
                                        'player': player.nick})
                    break

        else:
            table.receive_new_cards()
            for player in table.players:
                if player != self:
                    player.send({'hand': player.cards})
            self._pick_points_winner(table)

    def _start_final(self, table):
        table.in_final = True

        # XXX this needs to change
        table.final_turn_index = 0
        turn = table.players[table.final_turn_index]

        turn.send({'final': {'turn': True}})
        for player in table.players:
            if player != turn:
                player.send({'final': {'status': turn.nick + ' starts'}})

    def _on_final_card(self, card):
        table = self._tables[self.table_id]
        self.cards.remove(card)
        for player in table.players:
            if player != self:
                player.send({'final': {'laid': card, 'player': self.nick}})

        # XXX this needs to change
        table.final_turn_index += 1
        table.final_turn_index %= len(table.players)
        turn = table.players[table.final_turn_index]

        turn.send({'final': {'turn': True}})
        for player in table.players:
            if player != turn:
                player.send({'final': {'status': turn.nick + "'s turn"}})


_redis_connection = None

if __name__ == '__main__':

    tornado.options.parse_command_line()
    EchoRouter = SockJSRouter(PlayConnection, '/play')
    app_settings = dict(
      debug=options.debug,
      cookie_secret=settings.COOKIE_SECRET,
    )
    app = web.Application(EchoRouter.urls, **app_settings)
    app.listen(options.port)
    print "Running sock app on port", options.port
    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        pass
