import os
import unittest

from app import app, settings, db

class TestBase(unittest.TestCase):
    def _set_app(self):
        self.app = app
        self.app.testing = True

        self.test_client_app = self.app.test_client()

        #if settings.DEBUG:
            # fix,something in the python env cert, not working with sendgrid on local
            #import ssl
            #ssl._create_default_https_context = ssl._create_unverified_context

    def has_no_empty_params(self, rule):
        defaults = rule.defaults if rule.defaults is not None else ()
        arguments = rule.arguments if rule.arguments is not None else ()
        return len(defaults) >= len(arguments)

    def callable_url(self, url):
        """
        past urls that are just listing out results so we can just
        hit and ensure they run
        """
        pass_urls = ['/list', '/data', '/today']

        for pass_url in pass_urls:
            if url.find(pass_url) == -1:
                return False

        return True

    def _get_response_data(self, request_response):
        ret = request_response.get_data()
        ret = ret.replace('null', 'None').replace('false', 'False').replace('true', 'True')
        return eval(ret)

    def setUp(self):
        self._set_app()

        #self.app.test_request_context().push()
        #self.test_client_app = self.app.test_client()

    def tearDown(self):
        #os.close(self.db_fd)
        pass
