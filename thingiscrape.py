import requests
import json
import sys
import argparse
import os.path
import webbrowser
from collections import OrderedDict
from dotenv import load_dotenv
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

load_dotenv()

downloads_path = "./downloads"
stl_path = os.path.join(downloads_path, "stls")
json_path = os.path.join(downloads_path, "json")

if not os.path.exists(downloads_path):
    os.makedirs(downloads_path)
if not os.path.exists(stl_path):
    os.makedirs(stl_path)
if not os.path.exists(json_path):
    os.makedirs(json_path)

thingiverse_api_base = "https://api.thingiverse.com/"
access_keyword = "?access_token="
# Go to https://www.thingiverse.com/apps/create and create your own Desktop app
api_token = "6bb2ee0a0f3e3c640df67ecafbc6fbfa"

# OAuth settings - needed for NSFW content access
# When you create an app at https://www.thingiverse.com/apps/create, you get:
# - App Token (above) - for basic API access
# - Client ID and Client Secret (below) - for OAuth user login
oauth_client_id = os.getenv("THINGIVERSE_CLIENT_ID", "")
oauth_client_secret = os.getenv("THINGIVERSE_CLIENT_SECRET", "")
oauth_redirect_uri = "http://localhost:8080/callback"

if not api_token:
    print("ERROR: API_TOKEN environment variable not set.")
    print("Go to https://www.thingiverse.com/apps/create to create a new app and get your API token.")
    sys.exit(1)

rest_keywords = {
    "users": "users/",
    "likes": "likes/",
    "things": "things/",
    "files": "/files",
    "search": "search/",
    "pages": "&page=",
    "sort": "&sort={}", # relevant, text, popular, makes, newest
    "license": "&license={}", # cc, cc-sa, cc-nd, cc-nc-sa, cc-nc-nd, pd0, gpl, lgpl, bsd
    "nsfw": "&nsfw=true"
}

hall_of_fame = []
all_files_flag = False
nsfw_only_flag = False

def load_data():
    # Load the data from the file to a list
    if os.path.isfile("hall_of_fame.list"):
        file = open("hall_of_fame.list", "r")
        hall_of_fame = file.readlines()
        file.close()
        # Removing \n
        hall_of_fame = [x.strip() for x in hall_of_fame]

    # for n in hall_of_fame:
    #     print(n)
    # else:
    #     print("Hall of fame file not found")


def save_data():
    # Save the data
    ordered_halloffame = list(OrderedDict.fromkeys(hall_of_fame))
    ordered_halloffame.sort()
    file = open("hall_of_fame.list", "w")
    for user in ordered_halloffame:
        try:
            file.write(user)
        except:
            print("Error in name: {}".format(user))
            file.write(user)
            continue
    file.close()

# OAuth callback handler
class OAuthCallbackHandler(BaseHTTPRequestHandler):
    auth_code = None
    
    def do_GET(self):
        # Parse the authorization code from the callback URL
        query_components = parse_qs(urlparse(self.path).query)
        if 'code' in query_components:
            OAuthCallbackHandler.auth_code = query_components['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body><h1>Authorization successful!</h1><p>You can close this window and return to the terminal.</p></body></html>')
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body><h1>Authorization failed!</h1><p>No code received.</p></body></html>')
    
    def log_message(self, format, *args):
        # Suppress log messages
        pass

def get_oauth_token():
    """
    Performs OAuth 2.0 authentication flow to get a user access token.
    This token allows access to NSFW content.
    """
    if not oauth_client_id or not oauth_client_secret:
        print("\nERROR: OAuth credentials not configured!")
        print("To access NSFW content, you need to set up OAuth:")
        print("1. Go to https://www.thingiverse.com/apps/create")
        print("2. Note your Client ID and Client Secret")
        print("3. Set them as environment variables:")
        print("   - THINGIVERSE_CLIENT_ID")
        print("   - THINGIVERSE_CLIENT_SECRET")
        print("4. Or add them to a .env file")
        return None
    
    # Step 1: Get authorization code
    auth_url = (
        f"https://www.thingiverse.com/login/oauth/authorize"
        f"?client_id={oauth_client_id}"
        f"&redirect_uri={oauth_redirect_uri}"
        f"&response_type=code"
    )
    
    print("\n=== OAuth Authentication Required ===")
    print("Opening browser for Thingiverse login...")
    print(f"If browser doesn't open, visit: {auth_url}")
    print("\nWaiting for authorization...")
    
    # Open browser for user to authorize
    webbrowser.open(auth_url)
    
    # Start local server to receive callback
    server = HTTPServer(('localhost', 8080), OAuthCallbackHandler)
    server.handle_request()  # Handle one request (the callback)
    
    auth_code = OAuthCallbackHandler.auth_code
    if not auth_code:
        print("\nERROR: Failed to get authorization code")
        return None
    
    # Step 2: Exchange authorization code for access token
    token_url = "https://www.thingiverse.com/login/oauth/access_token"
    token_data = {
        'client_id': oauth_client_id,
        'client_secret': oauth_client_secret,
        'code': auth_code,
        'redirect_uri': oauth_redirect_uri
    }
    
    try:
        response = requests.post(token_url, data=token_data)
        if response.status_code == 200:
            # Parse response - it comes as URL-encoded parameters
            token_params = parse_qs(response.text)
            if 'access_token' in token_params:
                access_token = token_params['access_token'][0]
                print("\n✓ Successfully authenticated!")
                print("You now have access to NSFW content.")
                return access_token
            else:
                print(f"\nERROR: No access token in response: {response.text}")
                return None
        else:
            print(f"\nERROR: Token request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"\nERROR: Exception during token exchange: {e}")
        return None

def generic_search(term=None, sort_type=None, license=None, nsfw=False, n_pages=1, user_token=None):
    # Use OAuth token if provided (required for NSFW), otherwise use API token
    token = user_token if user_token else api_token
    
    for idx in range(n_pages):
        file_name = "search"
        print("\n\nPage: {}".format(idx + 1))
        rest_url = thingiverse_api_base + rest_keywords["search"]
        if term and isinstance(term, str):
            rest_url += term
            file_name += "_"
            file_name += term.replace(" ", "_")
        rest_url += access_keyword + token + rest_keywords["pages"] + str(idx + 1)
        if sort_type and isinstance(sort_type, str):
            rest_url += rest_keywords["sort"].format(sort_type)
            file_name += "_"
            file_name += sort_type
        if license and isinstance(license, str):
            rest_url += rest_keywords["license"].format(license)
        if nsfw:
            rest_url += rest_keywords["nsfw"]
            file_name += "_nsfw"
        file_name += ".json"
        print("url: {}".format(rest_url))
        download_objects(rest_url, file_name, "search", token=token, filter_nsfw=nsfw)

def relevant(n_pages=1):
    generic_search(sort_type="relevant", n_pages=n_pages)

def text(n_pages=1):
    generic_search(sort_type="text", n_pages=n_pages)

def popular(n_pages=1):
    generic_search(sort_type="popular", n_pages=n_pages)

def makes(n_pages=1):
    generic_search(sort_type="makes", n_pages=n_pages)

def newest(n_pages=1):
    generic_search(sort_type="newest", n_pages=n_pages)


def user(username, n_pages=1):
    # /users/{$username}/things
    for index in range(n_pages):
        print("\n\nPage: {}".format(index+1))
        rest_url = thingiverse_api_base + \
            rest_keywords["users"]+username+"/"+rest_keywords["things"] + \
            access_keyword+api_token+rest_keywords["pages"]+str(index+1)
        print(rest_url)
        download_objects(rest_url, str(username+".json"))


def likes(username, n_pages=1):
    # /users/{$username}/things
    for index in range(n_pages):
        print("\n\nPage: {}".format(index+1))
        rest_url = thingiverse_api_base + \
            rest_keywords["users"]+username+"/"+rest_keywords["likes"] + \
            access_keyword+api_token+rest_keywords["pages"]+str(index+1)
        # print(rest_url)
        download_objects(rest_url, str(username+"_likes.json"))


def parser_info(rest_url, file_name):
    s = requests.Session()  # It creates a session to speed up the downloads
    r = s.get(rest_url)
    data = r.json()

    # Save the data
    file = open(file_name, "w")
    file.write(json.dumps(data, indent=4, sort_keys=True, ensure_ascii=False))
    file.close()

    # Reading the json file
    file = open(file_name, "r")
    data_pd = json.loads(file.read())

    # The page has objects?
    if (len(data_pd) == 0):
        print("\n\nNo more pages- Finishing the program")
        save_data()
        sys.exit()

    # Is it an error page?
    for n in data_pd:
        if (n == "error"):
            print("\n\nNo more pages- Finishing the program")
            save_data()
            sys.exit()

    print("Parsing data from {} objects from thingiverse".format(len(data_pd)))

    for object in range(len(data_pd)):

        object_id = str(data_pd[object]["id"])
        print("\n{} -> {}".format(data_pd[object]["name"], data_pd[object]["public_url"]))

        # Name and last name
        print("Name: {} {}".format(data_pd[object]["creator"]
                                   ["first_name"], data_pd[object]["creator"]["last_name"]))

        # If the name and last name are empty, we use the username
        # TODO check if the name is already on the list or is new->call the twitter api
        # 3 in [1, 2, 3] # => True
        if (data_pd[object]["creator"]["first_name"] == "" and data_pd[object]["creator"]["last_name"] == ""):
            hall_of_fame.append(data_pd[object]["creator"]["name"]+"\n")
        else:
            hall_of_fame.append(data_pd[object]["creator"]["first_name"] +
                                " "+data_pd[object]["creator"]["last_name"]+"\n")


def download_objects(rest_url, file_name, mode = "none", token=None, filter_nsfw=False):
    # Use provided token or default to api_token
    auth_token = token if token else api_token
    
    s = requests.Session()  # It creates a session to speed up the downloads
    # Add authorization header for NSFW content access
    headers = {"Authorization": f"Bearer {auth_token}"}
    r = s.get(rest_url, headers=headers)
    data = r.json()

    # Save the data
    json_file_path = os.path.join(json_path, file_name)
    json_file = open(json_file_path, "w", encoding="utf-8")

    # print(json.dumps(data, indent=4, sort_keys=True,ensure_ascii=False)) # debug print
    json_file.write(json.dumps(data, indent=4, sort_keys=True, ensure_ascii=False))
    json_file.close()

    # Reading the json file
    json_file = open(json_file_path, "r", encoding="utf-8")
    data_pd = json.loads(json_file.read())

    if mode == "search":
        print(data_pd) # BUG: hits DNE 
        data_pd = data["hits"]

        # The page has objects?
        if (data_pd is None):
            print("\n\nNo more pages- Finishing the program")
            save_data()
            sys.exit()

        # Is it an error page?
        for n in data_pd:
            if (n == "error"):
                print("\n\nNo more pages- Finishing the program")
                save_data()
                sys.exit()
    else:
        data_pd = data

        # The page has objects?
        if (len(data_pd) == 0):
            print("\n\nNo more pages- Finishing the program")
            save_data()
            sys.exit()

        # Is it an error page?
        for n in data_pd:
            if (n == "error"):
                print("\n\nNo more pages- Finishing the program")
                save_data()
                sys.exit()



    print("Downloading {} objects from thingiverse".format(len(data_pd)))
    # print(data_pd)

    for object in range(len(data_pd)):
        # print(object)
        # print(data_pd[object])
        object_id = str(data_pd[object]["id"])
        
        # Filter by NSFW status if requested
        if filter_nsfw:
            is_nsfw = data_pd[object].get("is_nsfw", False)
            if is_nsfw is not True:  # Skip if is_nsfw is False or None
                print("\n⊘ Skipping non-NSFW item: {} (is_nsfw: {})".format(data_pd[object]["name"], is_nsfw))
                continue
        
        print("\n{} -> {}".format(data_pd[object]["name"], data_pd[object]["public_url"]))
        print("Object id: {}".format(object_id))

        # Sanitize filename for Windows - remove invalid characters
        safe_name = data_pd[object]["name"]
        for char in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']:
            safe_name = safe_name.replace(char, '-')
        safe_name = safe_name.replace(" ", "_")
        
        file_path = os.path.join(stl_path, safe_name)
        if not os.path.exists(file_path):
            os.makedirs(file_path)
        else:
            print("\nSkipping already downloaded object")
            continue

        # User name
        print("{} {}".format(data_pd[object]["creator"]["first_name"],
                             data_pd[object]["creator"]["last_name"]))

        # If the name and last name are empty, we use the username
        if (data_pd[object]["creator"]["first_name"] == "" and data_pd[object]["creator"]["last_name"] == ""):
            hall_of_fame.append(data_pd[object]["creator"]["name"]+"\n")
        else:
            hall_of_fame.append(data_pd[object]["creator"]["first_name"] +
                                " "+data_pd[object]["creator"]["last_name"]+"\n")
            # GET /things/{$id}/files/{$file_id}

        # Get file from a things
        headers = {"Authorization": f"Bearer {api_token}"}
        r = s.get(thingiverse_api_base+rest_keywords["things"] +
                  object_id+rest_keywords["files"]+access_keyword+api_token, headers=headers)
        # print(r)
        # print(thingiverse_api_base+rest_keywords["things"]+object_id+rest_keywords["files"]+access_keyword+api_token)
        files_info = r.json()

        for file in range(len(files_info)):

            if (all_files_flag):  # Download all the files
                print("    "+files_info[file]["name"])
                # Download the file
                download_link = files_info[file]["download_url"]+access_keyword+api_token
                print(download_link)
                r = s.get(download_link)
                with open(file_path+"/"+files_info[file]["name"], "wb") as code:
                    code.write(r.content)
            else:  # Download only the .stls
                if(files_info[file]["name"].find(".stl")) != -1:
                    print("    "+files_info[file]["name"])
                    # Download the file
                    download_link = files_info[file]["download_url"]+access_keyword+api_token
                    print(download_link)
                    r = s.get(download_link)
                    with open(file_path+"/"+files_info[file]["name"], "wb") as code:
                        code.write(r.content)


if __name__ == "__main__":

    print("\nTHINGISCRAPE")
    print("Complex Additive Materials Group")
    print("University of Cambridge")

    parser = argparse.ArgumentParser()

    parser.add_argument("--newest", type=bool, dest="newest_true",
                        help="It takes the newest objects uploaded")

    parser.add_argument("--popular", type=bool, dest="popular_true",
                        help="It takes the most popular objects uploaded")

    parser.add_argument("--user", type=str, dest="username",
                        help="Downloads the object of a specified user")

    parser.add_argument("--pages", type=int, default=1,
                        help="Defines the number of pages to be downloaded.")

    parser.add_argument("--all", type=bool, default=False,
                        help="Download all the pages available (MAX 1000).")

    parser.add_argument("--likes", type=str, dest="likes",
                        help="Downloads the likes of a specified user")

    parser.add_argument("--search", type=str, dest="keywords",
                        help="Downloads the objects that match the keywords. 12 objects per page\n Example: --search 'star wars'")
    parser.add_argument("--all-files", type=bool, dest="all_files",
                        help="Download all the files, images, stls and others\n Example: --all-files True")
    parser.add_argument("--nsfw", type=bool, dest="nsfw_only", default=False,
                        help="Include NSFW (Not Safe For Work) models in search results\n Example: --nsfw True")

    args = parser.parse_args()

    load_data()

    if args.all:
        args.pages = 1000
    if args.all_files:
        all_files_flag = True
    if args.nsfw_only:
        nsfw_only_flag = True

    # If NSFW requested, we need OAuth authentication
    user_oauth_token = None
    if args.nsfw_only:
        print("\n=== NSFW Content Access ===")
        print("NSFW content requires user authentication via OAuth.")
        user_oauth_token = get_oauth_token()
        if not user_oauth_token:
            print("\nFailed to authenticate. Cannot access NSFW content.")
            print("Exiting...")
            sys.exit(1)

    if args.newest_true:
        newest(args.newest_true)
    if args.popular_true:
        popular(args.popular_true)
    elif args.username:
        user(args.username, args.pages)
    elif args.likes:
        likes(args.likes, args.pages)
    elif args.keywords:
        generic_search(args.keywords, n_pages=args.pages, nsfw=nsfw_only_flag, user_token=user_oauth_token)
    else:
        newest(1)
