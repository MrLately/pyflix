#real_debrid.py
import requests
import time
import json
import httpx

def load_config():
    with open('config.json', 'r') as config_file:
        return json.load(config_file)  
    
config = load_config()
REAL_DEBRID_API_TOKEN = config['REAL_DEBRID_API_TOKEN']

async def check_rd_cache(torrent_hash):
    headers = {"Authorization": f"Bearer {REAL_DEBRID_API_TOKEN}"}
    api_url = f"https://api.real-debrid.com/rest/1.0/torrents/instantAvailability/{torrent_hash}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(api_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        return torrent_hash in data and data[torrent_hash] and any(value for value in data[torrent_hash].values() if value)
       
       
def get_existing_torrent_id(torrent_hash):
    headers = {"Authorization": f"Bearer {REAL_DEBRID_API_TOKEN}"}
    response = requests.get("https://api.real-debrid.com/rest/1.0/torrents", headers=headers)
    response.raise_for_status()
    
    torrents = response.json()
    for torrent in torrents:
        if torrent['hash'].lower() == torrent_hash.lower():
            return torrent['id']
        
    return None


def get_download_link_from_id(torrent_id):
    headers = {"Authorization": f"Bearer {REAL_DEBRID_API_TOKEN}"}  
    response = requests.get(f"https://api.real-debrid.com/rest/1.0/torrents/info/{torrent_id}", headers=headers)
    response.raise_for_status()
    
    torrent_info = response.json()
    if torrent_info['status'] == 'downloaded':
        original_link = torrent_info['links'][0]
        return original_link
    
    return None


def add_magnet_to_realdebrid(hash):
    headers = {"Authorization": f"Bearer {REAL_DEBRID_API_TOKEN}"}
    magnet = f"magnet:?xt=urn:btih:{hash}"
    response = requests.post("https://api.real-debrid.com/rest/1.0/torrents/addMagnet", headers=headers, data={"magnet": magnet})
    response.raise_for_status()
    
    return response.json()['id']


def select_files_and_start_download(torrent_id):
    config = load_config()
    CURRENT_SEASON = config['CURRENT_SEASON']
    CURRENT_EPISODE = config['CURRENT_EPISODE']
    headers = {"Authorization": f"Bearer {REAL_DEBRID_API_TOKEN}"}
    response = requests.get(f"https://api.real-debrid.com/rest/1.0/torrents/info/{torrent_id}", headers=headers)
    response.raise_for_status()
    files_info = response.json()['files']

    excluded_dirs = [
        "featurettes", "deleted scenes", "specials", "sample", 
        "extras", "bonus", "interviews", "trailers", "ost"
    ]
    
    video_files = [
        file for file in files_info 
        if file['path'].lower().endswith(('.mp4', '.mkv', '.avi', '.mov'))
        and not any(excluded_dir in file['path'].lower() for excluded_dir in excluded_dirs)
    ]

    selected_file_id = None
    # i may want to select all if series or season instead of one like im doing now
    if CURRENT_SEASON != "0" and CURRENT_EPISODE != "0":
        season_episode_str = f"S{CURRENT_SEASON}E{CURRENT_EPISODE}".lower()
        print(f"Attempting to match: {season_episode_str}")
        for file in video_files:
            print(f"Checking: {file['path']}")
            if season_episode_str in file['path'].lower():
                selected_file_id = file['id']
                print(f"Match found: {file['path']}")
                break

    if selected_file_id:
        response = requests.post(f"https://api.real-debrid.com/rest/1.0/torrents/selectFiles/{torrent_id}", headers=headers, data={"files": str(selected_file_id)})
        response.raise_for_status()
    else:
        # this works well for movies
        largest_file_id = sorted(video_files, key=lambda x: x['bytes'], reverse=True)[0]['id']
        response = requests.post(f"https://api.real-debrid.com/rest/1.0/torrents/selectFiles/{torrent_id}", headers=headers, data={"files": str(largest_file_id)})
        response.raise_for_status()


def check_download_status(torrent_id):
    headers = {"Authorization": f"Bearer {REAL_DEBRID_API_TOKEN}"}
    
    while True:
        response = requests.get(f"https://api.real-debrid.com/rest/1.0/torrents/info/{torrent_id}", headers=headers)
        response.raise_for_status()
        
        torrent_info = response.json()
        if torrent_info['status'] == 'downloaded':
            download_link = torrent_info['links'][0]
            return download_link
        time.sleep(1) 

def unrestrict_link(download_link):
    headers = {"Authorization": f"Bearer {REAL_DEBRID_API_TOKEN}"}
    response = requests.post("https://api.real-debrid.com/rest/1.0/unrestrict/link", headers=headers, data={"link": download_link})
    response.raise_for_status()
    
    return response.json()['download']


def main(infoHash):
    config = load_config()
    torrent_id = get_existing_torrent_id(infoHash)
    download_link = None
    is_series_episode = config['CURRENT_SEASON'] != "0" and config['CURRENT_EPISODE'] != "0"

    if torrent_id:
        if not is_series_episode: # is movie and already exists
            print(f"Torrent ID already exists: {torrent_id}")
            download_link = get_download_link_from_id(torrent_id)
        else:
            # for now its force re adding the torrent for series
            torrent_id = None

    if not download_link:
        if not torrent_id:
            torrent_id = add_magnet_to_realdebrid(infoHash)
            print(f"Torrent hash added successfully, torrent ID: {torrent_id}")

        select_files_and_start_download(torrent_id)
        print("File selected")
        download_link = check_download_status(torrent_id)
        print(f"Download link obtained")

    unrestricted_link = unrestrict_link(download_link)
    print(f"Unrestricted Direct Download Link: {unrestricted_link}")
    return unrestricted_link





