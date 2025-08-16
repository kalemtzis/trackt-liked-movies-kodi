import json
import os
import requests

CLIENT_ID = 'e0bbeac986d4711b5f29e40dd3b58a25f673d5f8b15f9f6cb7f2ef4fe8896d2a'
CLIENT_SECRET = '45768e6434ad9d5935dd8e8dbc7188a9f9d4ab5ab407fa843783668b96c5cdee'
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"
TRAKT_API_ENDPOINT = 'https://api.trakt.tv'
TOKEN_FILE = 'trakt_token.json'

def autheticate():
  if os.path.exists(TOKEN_FILE):
    with open(TOKEN_FILE, 'r') as f:
      return json.load(f)
  
  auth_url = f"https://trakt.tv/oauth/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}"
  
  print(f"Go to this URL in your browser, login and get a PIN:\n{auth_url}")
  
  pin = input(f"Enter your PIN from Trakt: ").strip()
  
  res = requests.post(f"{TRAKT_API_ENDPOINT}/oauth/token", json={
    "code": pin,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "redirect_uri": REDIRECT_URI,
    "grant_type": "authorization_code"
  })
  
  tokens = res.json()
  
  with open(TOKEN_FILE, 'w') as f:
    json.dump(tokens, f)
    
  return tokens

def get_username(tokens):
  headers = {
        "Authorization": f"Bearer {tokens['access_token']}",
        "trakt-api-version": "2",
        "trakt-api-key": CLIENT_ID
    }
  resp = requests.get(f"{TRAKT_API_ENDPOINT}/users/me", headers=headers)
  resp.raise_for_status()
  return resp.json()["username"]

def get_liked_lists(tokens): 
  headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {tokens['access_token']}",
    "trakt-api-version": "2",
    "trakt-api-key": CLIENT_ID
  }
  
  res = requests.get(f"{TRAKT_API_ENDPOINT}/users/likes/lists", headers=headers)
  res.raise_for_status()
  
  
  return res.json()

def get_list_movies(tokens, username, list_id):
  headers = {
        "Authorization": f"Bearer {tokens['access_token']}",
        "trakt-api-version": "2",
        "trakt-api-key": CLIENT_ID
    }
  res = requests.get(f"{TRAKT_API_ENDPOINT}/users/{username}/lists/{list_id}/items", headers=headers)
  res.raise_for_status()
  
  data = res.json()
  
  movies = [item['movie'] for item in data if item['type'] == 'movie']
  
  return movies
  
if __name__ == '__main__':
  tokens = autheticate()
  username = get_username(tokens)
  print("Username: ", username)
  liked_lists = get_liked_lists(tokens)
  
  for lst in liked_lists:
    print(lst['list']['name'])  
  
  #all_movies = []
  for lst in liked_lists:
    list_id = lst['list']["ids"]["slug"]
    creatorUsername = lst['list']['user']['username']
    list_name = lst['list']['name']
    
    movies = get_list_movies(tokens, creatorUsername, list_id)
    
    os.makedirs(f"{list_name}", exist_ok=True)
    list_dir = os.path.join(os.getcwd(), list_name)
    
    with open(os.path.join(list_dir, f"{list_name}.json"), 'w', encoding='utf-8') as f:
      json.dump(movies, f, indent=2)
    #all_movies.extend(movies)

  #with open('list.json', 'w') as f:
    # json.dump(all_movies, f, indent=2)