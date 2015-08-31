__author__ = 'greg@thousandyeardrift.com'
from flask import *
import requests
from requests.exceptions import RequestException
from requests.auth import HTTPBasicAuth
import json, os
import errno
from werkzeug.contrib.cache import FileSystemCache
from socket import inet_aton
from struct import unpack
import logging, logging.handlers

app = Flask(__name__)
app.config.from_object('default_config')
if 'DURASTREAM_SETTINGS' in os.environ:
    app.config.from_envvar('DURASTREAM_SETTINGS')
import sys
sys.path.insert(0,'/htdocs/includes/webdata/durastream')
app.config.from_object('durastream_config')

LOG_FILENAME = '/tmp/durastream-errors.log'
DURASTREAM_TIMEOUT_HRS = app.config['DURASTREAM_TIMEOUT_HRS']
DURASTREAM_TIMEOUT_SECS = DURASTREAM_TIMEOUT_HRS * 60 * 60

DURACLOUD_URL = app.config['DURACLOUD_URL']
DURACLOUD_USERNAME = app.config['DURACLOUD_USERNAME']
DURACLOUD_PASSWORD = app.config['DURACLOUD_PASSWORD']

DURACLOUD_SPACE_CACHE_DIR = app.config['DURACLOUD_SPACE_CACHE_DIR']
IP_RULES_CONFIG = app.config['IP_RULES_CONFIG']

app.logger.setLevel(logging.DEBUG) # use the native logger of flask
handler = logging.handlers.RotatingFileHandler(
    LOG_FILENAME,
    maxBytes=1024 * 1024 * 100,
    backupCount=20
    )
app.logger.addHandler(handler)

@app.route('/testFlowPlayer', methods=['GET'])
def test_flowplayer():
    return render_template('test-flowplayer.html', ip=request.remote_addr)

@app.route('/testMediaElement', methods=['GET'])
def test_player():
    return render_template('test-mediaelement.html', ip=request.remote_addr)

@app.route('/getIP', methods=['GET'])
def get_ip():
    app.logger.debug("get IP")
    resp = make_response(json.dumps({'IP': request.remote_addr}))
    resp.headers['Content-Type'] = "application/json"
    return resp

# AJAX requests for streaming URLS
@app.route('/getStreamUrl', methods=['POST'])
def get_stream():
    app.logger.debug("I am over here")
    spaceId = request.form["spaceId"]
    contentId = request.form["contentId"]
    info = getSpaceInfo(spaceId)
    app.logger.debug(info)
    if info['Access Control'] == 'PUBLIC':
        url = getOpenURL(spaceId, contentId, None)
        rbody = json.dumps({'streamUrl': url})
        return responseWithCookie(rbody, "application/json", url, spaceId, contentId, request.remote_addr)
    elif info['Access Control'] == 'CAMPUS_OR_SECURE':
        if oncampus(request.remote_addr):
            url = getSignedURL(spaceId, contentId, None, request.remote_addr)
            rbody = json.dumps({'streamUrl': url})
            return responseWithCookie(rbody, "application/json", url, spaceId, contentId, request.remote_addr)
    return json.dumps({'secure': True, 'message': 'You must log in to view this stream.'})

# A page, requiring authentication, that delivers the streaming URL as a cookie.
@app.route('/getStreamUrlSecure', methods=['POST','GET'])
def get_authenticated_stream():
    spaceId = request.values["spaceId"]
    contentId = request.values["contentId"]
    backURL = request.values["backURL"]
    ipAddress = request.remote_addr
    url = getSignedURL(spaceId, contentId, None, ipAddress)

    # Thank you page with redirect and link back to content page.
    respBody = render_template('authenticated.html', backURL = backURL, timeout = DURASTREAM_TIMEOUT_HRS)
    return responseWithCookie(respBody, "text/html", url, spaceId, contentId, request.remote_addr)

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
        print e

def getSignedURL(spaceId, contentId, resourcePrefix, ipAddress):
    postBody = json.dumps(
        {'spaceId': spaceId, 'contentId': contentId, 'ipAddress': ipAddress,
         'minutesToExpire': DURASTREAM_TIMEOUT_HRS * 60})
    app.logger.debug("getSignedURL request:\n"+postBody)
    url = DURACLOUD_URL+ "durastore/task/get-signed-url"
    headers = {'Content-Type':'application/json'}
    auth = HTTPBasicAuth(DURACLOUD_USERNAME, DURACLOUD_PASSWORD)
    try:
        res = requests.post(url, data=postBody, headers=headers, auth=auth)
        app.logger.debug("getSignedURL response:\n"+json.dumps(res.json()))
        response = res.json()
        result = response['signedUrl']
        return result
    except RequestException as e:
        print e

spaceCache = None

def getSpaceInfo(spaceId):
    global spaceCache
    if spaceCache is None:
        mkdir_p(DURACLOUD_SPACE_CACHE_DIR)
        spaceCache = FileSystemCache(DURACLOUD_SPACE_CACHE_DIR, threshold=50, default_timeout=(24*3600), mode=384)

    # check spaceCache, otherwise fetch info from DuraCloud
    result = spaceCache.get(spaceId)
    if result is None:
        url = DURACLOUD_URL+ "/duradmin/download/contentItem"
        auth = HTTPBasicAuth(DURACLOUD_USERNAME, DURACLOUD_PASSWORD)
        payload = {'spaceId': spaceId, 'contentId': 'info.json'}
        try:
            response = requests.get(url, params=payload, auth=auth)
            result = response.json()
            spaceCache.set(spaceId, result)
        except RequestException as e:
            print e
            raise
    return result

# Set client-side cookie with requested streaming URL (and timeout)
def responseWithCookie(respBody, contentType, url, spaceId, contentId, clientIP):
    resp = make_response(respBody)
    resp.headers['Content-Type'] = contentType
    # max_age is seconds, taking away 30 to make sure it is never stale
    maxage = DURASTREAM_TIMEOUT_SECS - 30
    resp.set_cookie("durastream|"+spaceId+"|"+contentId+"|"+clientIP, value = str(url), max_age = maxage);
    return resp

# pattern matching on remote address
def oncampus(remoteAddress):
    # compute integer value of remote address
    # loop through rules
    result = False
    with open(IP_RULES_CONFIG, "r") as rules:
        # skip to second IncludeIP line for UNC ranges
        count = 0
        for line in rules:
            if line.startswith('IncludeIP'):
                count = count + 1
                if count == 2:
                    break

        for line in rules:
            if line[0] == '#':
                continue
            if line.strip() == '':
                continue
            tokens = line.split()
            if tokens[0] in ('E','I'):
                applies = False
                if '-' in tokens[1]:
                    (lowStr, highStr) = tokens[1].split('-')
                    test = atol(remoteAddress)
                    low = atol(lowStr)
                    high = atol(highStr)
                    applies = (low <= test <= high)
                else:
                    applies = remoteAddress == tokens[1]
                if applies:
                    if tokens[0] == 'I':
                        return False
                    if tokens[0] == 'E':
                        result = True
    return result

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

# Make integer from IP address
def atol(a):
    return unpack(">L", inet_aton(a))[0]

if __name__ == '__main__':
    app.logger.setLevel(logging.INFO) # use the native logger of flask

    handler = logging.handlers.RotatingFileHandler(
        LOG_FILENAME,
        maxBytes=1024 * 1024 * 100,
        backupCount=20
        )

    app.logger.addHandler(handler)
    logging.basicConfig(filename='/tmp/durastream-errors.log',level=logging.DEBUG)

    app.run(host='0.0.0.0')
