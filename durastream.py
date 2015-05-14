__author__ = 'greg@thousandyeardrift.com'
from flask import *
from werkzeug.contrib.cache import SimpleCache
import requests
from requests.auth import HTTPBasicAuth
import re
import json
import os

app = Flask(__name__)
app.config.from_object('default_config')
if 'DURASTREAM_SETTINGS' in os.environ:
    app.config.from_envvar('DURASTREAM_SETTINGS')

DURASTREAM_TIMEOUT_HRS = app.config['DURASTREAM_TIMEOUT_HRS']
DURASTREAM_TIMEOUT_SECS = DURASTREAM_TIMEOUT_HRS * 60 * 60

DURACLOUD_URL = app.config['DURACLOUD_URL']
DURACLOUD_USERNAME = app.config['DURACLOUD_USERNAME']
DURACLOUD_PASSWORD = app.config['DURACLOUD_PASSWORD']

spaceCache = SimpleCache()


# AJAX requests for streaming URLS
@app.route('/getStreamURL', methods=['POST'])
def search():
    spaceId = request.form["spaceId"]
    contentId = request.form["contentId"]
    info = getSpaceInfo(spaceId)
    if info['Streaming Type'] == 'OPEN':
        url = getOpenURL(spaceId, contentId, None)
        rbody = json.dumps({'streamUrl': url})
        return responseWithCookie(rbody, "application/json", url, spaceId, contentId)
    elif info['Access Requirement'] == 'CAMPUS_OR_SECURE':
        if oncampus(request.remote_addr):
            url = getSignedURL(spaceId, contentId, None, request.remote_addr)
            rbody = json.dumps({'streamUrl': url})
            return responseWithCookie(rbody, "application/json", url, spaceId, contentId)
    return json.dumps({'secure': True, 'message': 'You must log in to view this stream.'})


# A page, requiring authentication, that delivers the streaming URL as a cookie.
@app.route('/getStreamURLSecure', methods=['POST'])
def get_authenticated_stream():
    spaceId = request.form["spaceId"]
    contentId = request.form["contentId"]
    backURL = request.form["backURL"]
    ipAddress = request.remote_addr

    url = getSignedURL(spaceId, contentId, None, ipAddress)

    # Thank you page with redirect and link back to content page.
    respBody = render_template('authenticated.html', backURL = backURL, timeout = DURASTREAM_TIMEOUT_HRS)
    return responseWithCookie(respBody, "text/html", url, spaceId, contentId)

# Set client-side cookie with requested streaming URL (and timeout)
def responseWithCookie(respBody, contentType, url, spaceId, contentId):
    resp = make_response(respBody)
    resp.headers['Content-Type'] = contentType
    # max_age is seconds, taking away 30 to make sure it is never stale
    maxage = DURASTREAM_TIMEOUT_SECS - 30
    resp.set_cookie("durastream|"+spaceId+"|"+contentId, value = str(url), max_age = maxage);
    return resp


if __name__ == '__main__':
    app.run()


def getOpenURL(spaceId, contentId, resourcePrefix):
    postBody = json.dumps({'spaceId': spaceId, 'contentId': contentId})
    url = DURACLOUD_URL+ "durastore/task/get-url"
    headers = {'Content-Type':'application/json'}
    auth = HTTPBasicAuth(DURACLOUD_USERNAME, DURACLOUD_PASSWORD)
    try:
        res = requests.post(url, data=postBody, headers=headers, auth=auth)
        response = res.json()
        result = response['streamUrl']
        return result
    except RequestException as e:
        print e.read()

def getSignedURL(spaceId, contentId, resourcePrefix, ipAddress):
    postBody = json.dumps(
        {'spaceId': spaceId, 'contentId': contentId, 'ipAddress': ipAddress,
         'minutesToExpire': DURASTREAM_TIMEOUT_HRS * 60})
    url = DURACLOUD_URL+ "durastore/task/get-signed-url"
    headers = {'Content-Type':'application/json'}
    auth = HTTPBasicAuth(DURACLOUD_USERNAME, DURACLOUD_PASSWORD)
    try:
        res = requests.post(url, data=postBody, headers=headers, auth=auth)
        response = res.json()
        result = response['signedUrl']
        return result
    except RequestException as e:
        print e.read()


def getSpaceInfo(spaceId):
    # TODO check spaceCache, otherwise fetch info from DuraCloud
    return {'Streaming Type': 'OPEN'}

def onCampus(remoteAddress):
    # TODO regex pattern matching on remote address
    return True
