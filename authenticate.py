def Authenticate(domain, username, password, app_token):
	return False

def get_headers(self):
    headers = {}

    headers["Authorization"] = "Basic %s" % get_auth_token(username=self.username,password=self.password)

    headers['X-Socrata-Host'] = self.domain

    headers['X-App-Token'] = self.app_token

    return headers  