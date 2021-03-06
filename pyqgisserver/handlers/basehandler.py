#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

""" Base Request handler 
"""
import os
import tornado.web
import logging
import json
import traceback
from tornado.web import HTTPError

from urllib.parse import urlencode

from ..version import __version__
from ..config import get_config

LOGGER = logging.getLogger('QGSRV')


class BaseHandler(tornado.web.RequestHandler):
    """ Base class for HTTP request hanlers
    """
    def initialize(self):
        super().initialize()
        self._links    = []
        self.connection_closed = False
        self.logger = LOGGER
        self._cfg = get_config('server')

        self.url_encoded = len(self.request.body_arguments)
        # Replace query arguments to upper case:
        self.request.arguments = { k.upper():v for (k,v) in self.request.arguments.items() }

    def encode_arguments(self):
        return '?'+urlencode({k:v[0] for k,v in self.request.arguments.items()})

    def compute_etag(self):
        # Disable etag computation
        pass

    def set_default_headers(self):
        """ Override defaults HTTP headers 
        """
        self.set_header("Server",__version__)

    def on_connection_close(self):
        """ Override, log and set 'connection_closed' to True
        """
        self.connection_closed = True
        self.logger.warning("Connection closed by client: {}".format(self.request.uri))

    def write_json(self, chunk):
        """ Write body as json

            The method will also set CORS implicitely for any origin
            If this a security issue, we should allow it
            explicitely. 
        """
        if isinstance(chunk, dict):
            chunk = json.dumps(chunk, sort_keys=True)
        self.set_header('Content-Type', 'application/json;charset=utf-8')   
        # Allow CORS on all origin
        if self.request.headers.get('Origin'):
            self.set_header('Access-Control-Allow-Origin', '*')
        self.write(chunk)

    def write_error(self, status_code, **kwargs):
        """ Override, format error as json
        """
        message = self._reason

        if "exc_info" in kwargs:
            exception = kwargs['exc_info'][1]
            # Error was caused by a exception
            message = "{}".format(exception)
               
        self.logger.error("%s", message)
        response = dict(status="error" if status_code != 200 else "ok",
                        httpcode = status_code,
                        error    = { "message": message })

        self.write_json(response)
        self.finish()

    def proxy_url(self):
        """ Return the proxy_url
        """
        # Replace the status url with the proxy_url if any
        req = self.request
        proxy_url = self._cfg.get('host_proxy') or \
                    req.headers.get('X-Proxy-Location') or  \
                    "{0.protocol}://{0.host}{0.path}".format(req)
        return proxy_url                            
