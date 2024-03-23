# scraper.py
import httpx
import json
from real_debrid import check_rd_cache
import asyncio

def load_config():
    with open('config.json', 'r') as config_file:
        return json.load(config_file)

def save_config(config):
    with open('config.json', 'w') as config_file:
        json.dump(config, config_file, indent=4)

def normalize_quality(title): # was having issue with 4k not being grouped with 2160p
    lower_title = title.lower()
    if '4k' in lower_title or '2160p' in lower_title:
        return '2160p'
    if '1080p' in lower_title:
        return '1080p'
    if '720p' in lower_title:
        return '720p'
    if '480p' in lower_title:
        return '480p'
    return 'other'

async def fetch_stream_data(url):
    print('fetch_stream_data')
    """fetch streaming data from a given url."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

async def fetch_torrents(video_id: str, catalog_type: str, season: int = None, episode: int = None) -> list:
    config = load_config()
    config['video_id'] = video_id  # update the current video_id in the config
    save_config(config)
    SCRAPE_URLS = config['SCRAPE_URLS']
    print('fetch_torrents')
    torrents = []
    for url in SCRAPE_URLS:
        try:
            if catalog_type == "series":
                print("checking for series")
                # set the currebt season and episode in config
                config['CURRENT_SEASON'] = str(season).zfill(2)
                config['CURRENT_EPISODE'] = str(episode).zfill(2)
                save_config(config)
                fetch_url = f"{url}/stream/{catalog_type}/{video_id}:{season}:{episode}.json"
            else:
                print("checking for movie")
                # reset the current season and episode to 0
                config['CURRENT_SEASON'] = "0"
                config['CURRENT_EPISODE'] = "0"
                save_config(config)
                fetch_url = f"{url}/stream/{catalog_type}/{video_id}.json"
            
            stream_data = await fetch_stream_data(fetch_url)
            if stream_data.get("streams"):
                torrents.extend(stream_data.get("streams"))
                break
        except Exception as e:
            print(f"Failed to fetch from {url}: {e}")
    return torrents

def sort_torrents_by_quality(torrents):
    config = load_config()
    QUALITY_ORDER = config['QUALITY_ORDER']
    UNDESIRABLE_LIST = config['UNDESIRABLE_LIST']
    LIMIT_PER_QUAL = config['LIMIT_PER_QUAL']
    print('sorting')  
    filtered_torrents = [torrent for torrent in torrents if not any(keyword in torrent['title'].lower() for keyword in UNDESIRABLE_LIST)]

    filtered_torrents.sort(key=lambda torrent: QUALITY_ORDER.get(normalize_quality(torrent['title']), float('inf')))

    quality_limited_torrents = {}
    for torrent in filtered_torrents:
        quality = normalize_quality(torrent['title'])
        if quality not in quality_limited_torrents:
            quality_limited_torrents[quality] = [torrent]
        elif len(quality_limited_torrents[quality]) < LIMIT_PER_QUAL:
            quality_limited_torrents[quality].append(torrent)

    final_sorted_torrents = [torrent for quality_group in sorted(quality_limited_torrents.keys(), key=lambda q: QUALITY_ORDER.get(q, float('inf'))) for torrent in quality_limited_torrents[quality_group]]

    return final_sorted_torrents

async def check_and_append_cache_status(sorted_torrents):
    print('check_and_append_cache_status')
    async with httpx.AsyncClient() as client:
        tasks = []
        for torrent in sorted_torrents:
            torrent_hash = torrent['infoHash']
            task = asyncio.create_task(check_rd_cache(torrent_hash))
            tasks.append(task)
        
        cache_statuses = await asyncio.gather(*tasks)

        for torrent, is_cached in zip(sorted_torrents, cache_statuses):
            torrent['cache_status'] = "CACHED" if is_cached else "NOT CACHED"
    
    return sorted_torrents
