#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from flask import _app_ctx_stack, Flask, request, url_for
from flask.ext.assets import Environment as AssetEnvironment
from flask.ext.babel import Babel

import settings
from utils.assets import asset
from utils.host import host
from utils.i18n import get_locale, name2eng, party2eng
from utils.mongodb import mongojsonify
from utils.linkall import LinkAllFilter


##### utils #####
class ReverseProxied(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = settings.SCRIPT_NAME
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)




app = Flask(__name__)
app.debug = settings.SERVER_SETTINGS['debug']
app.wsgi_app = ReverseProxied(app.wsgi_app)
assets = AssetEnvironment(app)


def init_cache():
    app.config['CACHE_SETTINGS'] = settings.CACHE_SETTINGS

    @app.teardown_appcontext
    def close_cache(error=None):
        con = getattr(_app_ctx_stack.top, 'cache', None)
        if con is not None:
            con.disconnect_all()


def init_db():
    app.config['DB_SETTINGS'] = settings.DB_SETTINGS

    @app.teardown_appcontext
    def close_db(error=None):
        con = getattr(_app_ctx_stack.top, 'db', None)
        if con is not None:
            con.close()


def init_i18n():
    babel = Babel(app, **settings.BABEL_SETTINGS)
    babel.localeselector(get_locale)


def init_routes():
    '''
    Register all app modules specified in settings.
    '''

    from views.main import register; register(app)
    from views.party import register; register(app)
    from views.person import register; register(app)


def register_filters():
    app.jinja_env.filters['mongojsonify'] = mongojsonify
    app.jinja_env.filters['name2eng'] = name2eng
    app.jinja_env.filters['party2eng'] = party2eng

    # FIXME: keyword source
    with open('keywords.txt', 'r') as f:
        keywords = f.read().decode('utf-8').split()
    url_map = lambda keyword: url_for('entity_page', keyword=keyword)
    any_re = '|'.join(keywords + ['[1-9][0-9]{3}'])
    linkall = LinkAllFilter(url_map, any_re).get()
    app.jinja_env.filters['linkall'] = linkall


def register_context_processors():

    @app.context_processor
    def inject_asset():
        return dict(asset=asset)

    @app.context_processor
    def inject_locales():
        locale_links = dict((locale, request.url.replace(request.host, host(locale)))
                for locale in settings.LOCALES)
        return dict(locale_links=locale_links,
                locale=get_locale())


##### setup #####

init_cache()
init_db()
init_i18n()
init_routes()

register_filters()
register_context_processors()


##### main #####

if __name__ == '__main__':
    app.run(**settings.SERVER_SETTINGS)