import json
import os
import requests
import time
import re

CLIENT_ID = 'e0bbeac986d4711b5f29e40dd3b58a25f673d5f8b15f9f6cb7f2ef4fe8896d2a'
CLIENT_SECRET = '45768e6434ad9d5935dd8e8dbc7188a9f9d4ab5ab407fa843783668b96c5cdee'
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"

TMDB_API_KEY = 'dcb49c5fac43125b701a78377830fbb1'

TRAKT_API_ENDPOINT = 'https://api.trakt.tv'
TMDB_API_ENDPOINT = "https://api.themoviedb.org"
TMDB_URL = 'https://www.themoviedb.org'

TOKEN_FILE = 'trakt_token.json'
CACHE_FILE = 'cache.json'

MOVIES_DIR = './movies'
TVSHOWS_DIR = './tvshows'

def sanitize_filename(name, max_length=100):
    name = re.sub(r'[\\/:*?"<>|]', '-', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:max_length].rstrip()
  
def load_cache():
  if os.path.exists(CACHE_FILE):
    try:
      with open(CACHE_FILE, 'r') as f:
        raw = json.load(f)
        return {
          "movies": set(raw.get('movies', [])),
          "tvshows": set(raw.get('tvshows', []))
        }
    except (json.JSONDecodeError, ValueError):
      # file exists but is empty or corrupted → reset
      return {"movies": set(), "tvshows": set()}
  return {"movies": set(), "tvshows": set()}

def save_cache(cache):
  with open(CACHE_FILE, 'w') as f:
    json.dump({
      'movies': sorted(list(cache['movies'])),
      'tvshows': sorted(list(cache['tvshows'])),
    }, f)

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
  
  page = 1
  all_lists = []
  limit=100
  
  while True:
    res = requests.get(f"{TRAKT_API_ENDPOINT}/users/likes/lists?page={page}&limit={limit}", headers=headers)
    if res.status_code == 502:
      raise requests.exceptions.HTTPError("502 Bad Gateway")
    res.raise_for_status()
  
    data = res.json()
    if not data:
      break
    
    all_lists.extend(data)
    if len(data) < limit:
      break
    page += 1
  
  return all_lists


def get_list_items(tokens, username, list_id):
  headers = {
        "Authorization": f"Bearer {tokens['access_token']}",
        "trakt-api-version": "2",
        "trakt-api-key": CLIENT_ID
    }
  
  res = requests.get(f"{TRAKT_API_ENDPOINT}/users/{username}/lists/{list_id}/items", headers=headers)
  
  return res.json() if res.status_code == 200 else []

def get_tmdb_movie(tmdb_id):
  res = requests.get(f"{TMDB_API_ENDPOINT}/3/movie/{tmdb_id}?api_key={TMDB_API_KEY}&language=en-US")
  return res.json() if res.status_code == 200 else None

def get_tmdb_show(tmdb_id):
  res = requests.get(f"{TMDB_API_ENDPOINT}/3/tv/{tmdb_id}?api_key={TMDB_API_KEY}&language=en-US")
  return res.json() if res.status_code == 200 else None
  
def get_tmdb_season(tmdb_id, season):
  res = requests.get(f"{TMDB_API_ENDPOINT}/3/tv/{tmdb_id}/season/{season}?api_key={TMDB_API_KEY}&language=en-US")
  return res.json() if res.status_code == 200 else None

def write_strm(path, content):
  try:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
      f.write(content)
  except Exception as e:
    print(e)
    
def write_movie_nfo(info, folder):
  tmdb_id = info.get('id')
  if tmdb_id:
    nfo_path = os.path.join(folder, 'movie.nfo')
    os.makedirs(folder, exist_ok=True)
    with open(nfo_path, 'w') as f:
      f.write(f"{TMDB_URL}/movie/{tmdb_id}")
      
def write_show_nfo(info, folder):
  tmdb_id = info.get('id')
  if tmdb_id:
    nfo_path = os.path.join(folder, 'movie.nfo')
    os.makedirs(folder, exist_ok=True)
    with open(nfo_path, 'w') as f:
      f.write(f"{TMDB_URL}/tv/{tmdb_id}")
      
def process_item(item, list_name, cache):
  tp = item['type']
  data = item.get(tp, {})
  title = data.get('title', "Unknown")
  year = data.get('year', "0000")
  tmdb_id = data.get("ids", {}).get("tmdb")
  if not tmdb_id:
    return
  
  str_tmdb = str(tmdb_id)
  safe_list = sanitize_filename(list_name)
  safe_title = sanitize_filename(f"{title} ({year})")
  
  if tp == 'movie':
    if str_tmdb in cache['movies']:
      return
    
    folder = os.path.join(MOVIES_DIR, safe_list, safe_title)
    strm_path = os.path.join(folder, title + ".strm")
    write_strm(strm_path, f"plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=movie&islocal=True&tmdb_id={tmdb_id}")
    info = get_tmdb_movie(tmdb_id)
    if info:
      write_movie_nfo(info, folder)
    print(f"Film: {title} {year}")
    cache['movies'].add(str_tmdb)
  
  elif tp == 'show':
    if str_tmdb in cache['tvshows']:
      return
    
    folder = os.path.join(TVSHOWS_DIR, safe_list, safe_title)
    info = get_tmdb_show(tmdb_id)
    if info:
      write_show_nfo(info, folder)
      
      for season in info.get('seasons', []):
        number = season.get("season_number")
        if number and number > 0:
          season_folder = os.path.join(folder, f"season {number:02d}")
          season_data = get_tmdb_season(tmdb_id, number)
          if season_data:
            for episode in season_data.get('episodes', []):
              ep_num = episode.get('episode_number')
              ep_name = episode.get("name", "")
              fname = f"S{number:02d}E{ep_num:02d} - {ep_name}"
              strm_path = os.path.join(season_folder, fname + '.strm')
              line = (f"plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&islocal=True"
                                    f"&tmdb_id={tmdb_id}&season={number}&episode={ep_num}")
              write_strm(strm_path, line)
      
      print(f"Serie: {title} {year}")
      cache['tvshows'].add(str_tmdb)    
  
if __name__ == '__main__':
  tokens = autheticate()
  cache = load_cache()
  liked_lists = get_liked_lists(tokens)
  
  for lst in liked_lists:
    user = lst['list']['user']['ids']['slug']
    slug = lst['list']["ids"]["slug"]
    list_name = lst['list']['name']
    
    print(list_name)
    
    items = get_list_items(tokens, user, slug)
    
    for item in items:
      process_item(item, list_name, cache)
    
    save_cache(cache)