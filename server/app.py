import os
import urllib
from collections import defaultdict
import tornado.httpclient
import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado.options import define, options
import redis.client
import settings


define("debug", default=False, help="run in debug mode", type=bool)
define("port", default=8000, help="run on the given port", type=int)


class HomeHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('index.html')


class ManifestHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header('Content-Type', 'application/x-web-app-manifest+json')
        self.render('manifest.json')


class SignoutHandler(tornado.web.RequestHandler):
    def get(self):
        self.clear_cookie('user')
        self.redirect('/')


class CardsCSSHandler(tornado.web.RequestHandler):
    def get(self):
        css = """
        .card {
          background: url(%s);
          background-position: 0 0;
        }
        """ % self.static_url('images/pairs.png')

        self.set_header('text/css')
        self.write(css)

class BrowserIDAuthLoginHandler(tornado.web.RequestHandler):

    def check_xsrf_cookie(self):
        pass

    @tornado.web.asynchronous
    def post(self):
        assertion = self.get_argument('assertion')
        http_client = tornado.httpclient.AsyncHTTPClient()
        domain = self.request.host
        url = 'https://browserid.org/verify'
        data = {
          'assertion': assertion,
          'audience': domain,
        }
        response = http_client.fetch(
          url,
          method='POST',
          body=urllib.urlencode(data),
          callback=self.async_callback(self._on_response)
        )

    def _on_response(self, response):
        if 'email' in response.body:
            # all is well
            struct = tornado.escape.json_decode(response.body)
            assert struct['email']
            email = struct['email']

            self.set_secure_cookie('user', email, expires_days=10)
        self.write(struct)
        self.finish()


class Application(tornado.web.Application):

    _redis = None

    @property
    def redis(self):
        if not self._redis:
            self._redis = redis.client.Redis(settings.REDIS_HOST,
                                             settings.REDIS_PORT)
        return self._redis


def app():
    app_settings = dict(
      static_path=os.path.join(os.path.dirname(__file__), 'static'),
      template_path=os.path.join(os.path.dirname(__file__), 'templates'),
      debug=options.debug,
      cookie_secret=settings.COOKIE_SECRET,
    )

    return Application([
        (r'/', HomeHandler),
        #(r'/manifest.webapp', ManifestHandler),
        (r'/browserid/', BrowserIDAuthLoginHandler),
        (r'/cards.css', CardsCSSHandler),
        #(r'/highscore.json', HighscoreHandler),
        (r'/signout/', SignoutHandler),
    ], **app_settings)


if __name__ == '__main__':
    tornado.options.parse_command_line()
    app().listen(options.port)
    print 'Running on port', options.port
    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        pass
