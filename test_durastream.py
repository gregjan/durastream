import os
import durastream
import unittest
import tempfile

OPEN_SPACEID = 'streaming-test-1'
AUTH_SPACEID = 'streaming-test-2'
CONTENTID = 'wildlife.mp4'

class DurastreamTestCase(unittest.TestCase):

    def setUp(self):
        durastream.app.config['TESTING'] = True
        durastream.app.config['DEBUG'] = True
        self.app = durastream.app.test_client()

    # def tearDown(self):

    def test_openStreamURL(self):
        rv = self.app.post('/getStreamURL', data=dict(
            spaceId=OPEN_SPACEID,
            contentId=CONTENTID
        ), follow_redirects=True, environ_base={'REMOTE_ADDR': '127.0.0.1'})
        print rv.data
        assert 'streamUrl' in rv.data

    def test_authStreamURL(self):
        rv = self.app.post('/getStreamURLSecure', data=dict(
            spaceId=AUTH_SPACEID,
            contentId=CONTENTID,
            backURL="http://example.com/my/content/item.html"
        ), follow_redirects=True, environ_base={'REMOTE_ADDR': '127.0.0.1'})
        print rv.data
        assert 'Streaming Content Authentication' in rv.data

if __name__ == '__main__':
    unittest.main()
