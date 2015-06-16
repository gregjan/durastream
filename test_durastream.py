import os
import durastream
import unittest
import tempfile

OPEN_SPACEID = 'open-streaming'
AUTH_SPACEID = 'secure-streaming'
CONTENTID = 'wildlife.mp4'

class DurastreamTestCase(unittest.TestCase):

    def setUp(self):
        durastream.app.config['TESTING'] = True
        durastream.app.config['DEBUG'] = True
        self.app = durastream.app.test_client()

    # def tearDown(self):

    def test_openStreamURL(self):
        rv = self.app.post('/getStreamUrl', data=dict(
            spaceId=OPEN_SPACEID,
            contentId=CONTENTID
        ), follow_redirects=True, environ_base={'REMOTE_ADDR': '127.0.0.1'})
        assert 'streamUrl' in rv.data

    def test_authStreamURL(self):
        rv = self.app.post('/getStreamUrlSecure', data=dict(
            spaceId=AUTH_SPACEID,
            contentId=CONTENTID,
            backURL="http://example.com/my/content/item.html"
        ), follow_redirects=True, environ_base={'REMOTE_ADDR': '127.0.0.1'})
        assert 'Streaming Content Authentication' in rv.data

    def test_oncampus(self):
        assert durastream.oncampus("152.23.166.2") == True
        assert durastream.oncampus("204.85.192.55") == False
        assert durastream.oncampus("198.85.230.44") == True
        assert durastream.oncampus("152.2.71.18") == False

if __name__ == '__main__':
    unittest.main()
