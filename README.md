# Install
The service may be installed on any python WSGI webserver. The server must be hosted on the same domain as the sites where it will
be used. This is due to the use of cross-domain cookies to cache streaming URLs in the browser. The service is a Flash application, see [Flask install documentation](http://flask.pocoo.org/docs/0.10/deploying/#deployment) for instructions for various web servers. There are many deployment options for Flask apps.

## Settings
The default configuration is in default_config.py. Instead of
modifying that file directly, here is the preferred way to configure:

1. Make your own copy of the file someplace safely outside of the application, like /etc/durastream_config.py.
+ Modify that file as needed.
+ Add that file to your CM tool, if applicable.
+ Set the "DURASTREAM_SETTINGS" environment variable to the location of the new file.


    export DURASTREAM_SETTINGS=/etc/durastream_config.py

It is also possible to modify your code to point directly at a configuration file.
This is how the default configuration is loaded, prior to customizations. Create a
durastream_config.py file and add the appropriate directory to the path in durastream.py.
Then add this line, after the default_config line:

    app.config.from_object('durastream_config')
    
Note that adding a using "from_object" method above may require adding the folder to the python path, as follows:

    import sys
    sys.path.insert(0,'/etc/durastream')

## Access Controls for Spaces
All of the streams can be either public or secured on the space level. Secure spaces
can require login or also allow streaming within a set of configurable IP ranges.
Space access controls are contained in an info.json file that is placed in the
root directory of the space. Examples are provided of the three forms for these
ACLs, see [acl_public.json](acl_public.json), [acl_secure.json](acl_secure.json), [acl_campus.json](acl_campus.json). One of these three files can be uploaded to a space and renamed to info.json.

# Integrating Streaming into Web Sites
This tool has been tested with the JW Player and when you run Durastream.py, the server includes a test page with JW Player. You can find the template for the test page in the templates folder.

The test.html file uses two snippets of Javascript to do all of the
server communication and streaming. The streaming can be initiated from a hyperlink, a button or any page event. The stream() function in the test page is hardcoded with a contentId. You will want to modify the streaming functions to match your page design, passing contentId and spaceId appropriately and embedding the player in the right portion of your pages. In addition, a the variable for DURASTREAM_URL must be set somewhere in the Javascript, similar to the following line:

    var DURASTREAM_URL='http://durastream.mydomain.edu';

# How it Works
An AJAX JSON API is used to query the service for a streaming URL.
The URL is stored in a browser cookie for the lifetime that the
streaming URL is valid, or 2 hours, whichever is sooner.
If the user returns to the same streaming page within the alloted time, they will use the cookie.

Here is the control flow:

1. User navigates to the page of a streaming resource
2. The browser's real IP is obtained from the durastream API.
+ If there is a domain cookie that matches: contentId, spaceId, client IP, then:
  + Feed that URL to the javascript player (DONE!)
  + NOTE: Cookie timeout is always shorter than streaming URL timeout
+ Otherwise, an AJAX request is made to /getStreamURL, with contentId and spaceId
+ On server side, we fetch the space access control (may be cached)
+ If space is public, mint URL, respond with JSON and cookie.
+ If IP range is acceptable AND their IP is in range, mint secure URL and respond with JSON and cookie.
+ Otherwise, if stream is login restricted or outside of IP range, then:
  + If request is Shib authenticated or has remote user, mint secure URL and respond with JSON and cookie (user already logged in, perhaps for a prior stream)
  + Otherwise, return JSON:
    `{"message": "Onyen authentication is required", "url": "durastream.mydomain.edu/getStreamUrlSecure"}`
+ The browser receives a response from the server.
+ If we get JSON with a streaming URL and a cookie, then play stream immediately. (DONE!)
+ If we get a JSON auth challenge, prompt user with the link to authenticate for streaming and give them any further information.
+ User follows link to the durastream authorization page. The link contains the requested contentId and spaceId, as well as the return URL.
+ User is prompted to authenticate before they reach the durastream authorization page.
+ Server checks space access controls and mints a streaming URL. The server responds with a web page containing a link back to the return URL. It also sets the streaming URL in the cookie.
+ User follows link (you may modify the authenticated.html template to perform a redirect) back to the original streaming item page.
+ We go back to the top of this control flow, this time with the streaming URL already set in a cookie.
