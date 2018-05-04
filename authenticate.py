from base64 import b64encode
import urllib.request, urllib.error, urllib.parse
import json

def Authenticate(domain, username, password, app_token):
	try:
		resource = 'https://'+domain+"/api/users/current.json"
		request = urllib.request.Request(resource, headers=get_headers(domain, username, password, app_token))
		r = urllib2.urlopen(request)
		response = json.load(r)
		if "roleName" in response:
			return True
		else:
			return False
	except urllib.error.URLError as e:
		return False

def get_headers(domain, username, password, app_token):
    headers = {}

    headers["Authorization"] = "Basic %s" % get_auth_token(username=username,password=password)

    headers['X-Socrata-Host'] = domain

    headers['X-App-Token'] = app_token

    return headers

def get_auth_token(auth = None, username = None, password = None):
    if auth is not None:
        result = b64encode(b"%s" % auth).decode("ascii")
    else:
        result = b64encode(b"{0}:{1}".format(username, password).decode("ascii"))
    return result
