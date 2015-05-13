__author__ = 'greg@thousandyeardrift.com'
from flask import *
from contextlib import closing
from werkzeug.contrib.cache import SimpleCache
import urllib2
import re
import json
import os
import httplib

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

proxy_support = urllib2.ProxyHandler({}) #{'http': 'http://localhost:8080', 'https': 'http://localhost:8080'})
passwordMgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
passwordMgr.add_password(None, DURACLOUD_URL, DURACLOUD_USERNAME, DURACLOUD_PASSWORD)


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
    ipAddress = request.remote_addr
    url = getSignedURL(spaceId, contentId, None, ipAddress)

    # Thank you page with link back to streaming content page.
    backURL = request.form["backURL"]
    respBody = render_template('authenticated.html', backURL = backURL, timeout = DURASTREAM_TIMEOUT_SECS)
    return responseWithCookie(respBody, "text/html", url, spaceId, contentId)

def responseWithCookie(respBody, contentType, url, spaceId, contentId):
    print "body\n"+respBody
    print "ct "+contentType
    print "u "+str(url)
    print "s "+spaceId
    print "c "+contentId
    resp = make_response(respBody)
    resp.headers['Content-Type'] = contentType
    # Set client-side cookie with requested streaming URL (and timeout)
    # max_age is seconds, taking away 30 to make sure it is never stale
    maxage = DURASTREAM_TIMEOUT_SECS - 30
    resp.set_cookie("durastream|"+spaceId+"|"+contentId, value = str(url), max_age = maxage);
    return resp


if __name__ == '__main__':
    app.run()


# input a string and return a dictionary
def getOpenURL(spaceId, contentId, resourcePrefix):
    # POST params and get back JSON
    postBody = json.dumps({'spaceId': spaceId, 'contentId': contentId})
    url = DURACLOUD_URL+ "durastore/task/get-url"
    print url
    print postBody
    req = urllib2.Request(url, postBody)
    req.add_header('Content-Type', 'application/json')
    try:
        urllib2.install_opener(
            urllib2.build_opener(
                urllib2.HTTPBasicAuthHandler(passwordMgr),
                proxy_support))
        response = urllib2.urlopen(req)
        responseBody = response.read()
        result = json.loads(responseBody)['streamUrl']
        return result
    except urllib2.HTTPError as e:
        print e.read()

def getSignedURL(spaceId, contentId, resourcePrefix, ipAddress):
    # POST params and get back JSON
    postBody = json.dumps(
        {'spaceId': spaceId, 'contentId': contentId, 'ipAddress': ipAddress,
         'minutesToExpire': str(DURASTREAM_TIMEOUT_HRS * 60)})
    url = DURACLOUD_URL+ "durastore/task/get-signed-url"
    print url
    print postBody
    req = urllib2.Request(url, postBody)
    req.add_header('Content-Type', 'application/json')
    try:
        urllib2.install_opener(
            urllib2.build_opener(
                urllib2.HTTPBasicAuthHandler(passwordMgr),
                proxy_support))
        response = urllib2.urlopen(req)
        responseBody = response.read()
        result = json.loads(responseBody)['signedUrl']
        return result
    except urllib2.HTTPError as e:
        print e.read()

def getSpaceInfo(spaceId):
    # TODO check spaceCache, otherwise fetch info from DuraCloud
    return {'Streaming Type': 'OPEN'}

def onCampus(remoteAddress):
    # TODO regex pattern matching on remote address
    return True
