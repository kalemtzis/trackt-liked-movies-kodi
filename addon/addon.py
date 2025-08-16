import xbmcplugin
import xbmcgui
import xbmcaddon
import sys
import json
import os
import requests

addon_handle = int(sys.argv[1])
addon = xbmcaddon.Addon()

ADDON_PATH = xbmcaddon.Addon().getAddonInfo('path')
TOKEN_FILE = os.path.join(ADDON_PATH, 'resources', 'token.json')

CLIENT_ID = 'e0bbeac986d4711b5f29e40dd3b58a25f673d5f8b15f9f6cb7f2ef4fe8896d2a'
CLIENT_SECRET = '45768e6434ad9d5935dd8e8dbc7188a9f9d4ab5ab407fa843783668b96c5cdee'
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"

TRAKT_API_ENDPOINT = 'https://api.trakt.tv'

def autheticate():
  if os.path.exists(TOKEN_FILE):
    with open(TOKEN_FILE, 'r') as f:
      return json.load(f)
  
  auth_url = f"https://trakt.tv/oauth/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}"
  xbmcgui.Dialog().ok("Trakt Authentication", f"Visit this URL:\n{auth_url}\n\nEnter the PIN code below in the next step.")
  
  keyboard = xbmcgui.Dialog().input("Enter Trakt PIN")
  pin = keyboard.strip()
  
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

def get_liked_movies(tokens):
  headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {tokens['access_token']}",
    "trakt-api-version": "2",
    "trakt-api-key": CLIENT_ID
  }
  
  res = requests.get(f"{TRAKT_API_ENDPOINT}/sync/likes/movies", headers=headers)
  
  if res.status_code != 200:
    xbmcgui.Dialog().ok("Error", f"Failed to fetch: {res.text}")
    return []
  
  data = res.json()
  
  return [m["movie"] for m in data]

def list_movies():
  tokens = autheticate()
  liked_movies = get_liked_movies(tokens)
  
  for movie in liked_movies:
    title = f"{movie['title']} {movie['year']}"
    li = xbmcgui.ListItem(label=title)
    
    if movie.get("ids", {}).get('tmdb'):
      tmdb_id = movie['ids']['tmdb']
      poster_url = f"https://image.tmdb.org/t/p/w500/{tmdb_id}.jpg"
      li.setArt({"poster": poster_url, "thumb": poster_url, "fanart": poster_url})
    
    xbmcplugin.addDirectoryItem(handle=addon_handle, url="", listitem=li, isFolder=False)
    
  xbmcplugin.endOfDirectory(addon_handle)
  
if __name__ == '__main__':
  list_movies()