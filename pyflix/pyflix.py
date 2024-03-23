#pyflix.py
from flask import Flask, jsonify, make_response, request, redirect, url_for, render_template
import asyncio
from scraper import fetch_torrents, sort_torrents_by_quality, check_and_append_cache_status
import real_debrid
import json
import time
from threading import Lock

def load_config():
    with open('config.json', 'r') as config_file:
        return json.load(config_file)

config = load_config()

FLASK_PORT = config['FLASK_PORT']
FLASK_DEBUG = config['FLASK_DEBUG']
FLASK_HOST = config['FLASK_HOST']

app = Flask(__name__)

conversion_locks = {}
conversion_results = {}

def update_configuration(form_data):
    config = load_config()
    config['REAL_DEBRID_API_TOKEN'] = form_data.get('REAL_DEBRID_API_TOKEN', '')

    new_quality_order = {}
    draggable_qualities = form_data.getlist('quality_order[]')
    fixed_positions = {
        "other": len(draggable_qualities) + 1,
        "bottom": len(draggable_qualities) + 2
    }

    for index, quality in enumerate(draggable_qualities, start=1):
        new_quality_order[quality] = index

    new_quality_order.update(fixed_positions)
    config['QUALITY_ORDER'] = new_quality_order
    config['LIMIT_PER_QUAL'] = int(form_data.get('LIMIT_PER_QUAL', 5))

    with open('config.json', 'w') as config_file:
        json.dump(config, config_file, indent=4)

def respond_with(data):
    resp = make_response(jsonify(data))
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = '*'
    return resp

@app.route('/configure', methods=['GET', 'POST'])
def configure():
    if request.method == 'POST':
        update_configuration(request.form)
        return redirect(url_for('configure'))
    else:
        config_vars = load_config()
        return render_template('configure.html', config=config_vars)
    
@app.route("/manifest.json")
def get_manifest():
    logo_url = url_for('static', filename='logo.png', _external=True)
    background_url = url_for('static', filename='background.png', _external=True)
    manifest = {
        "id": "org.pyflix.addon",
        "version": "1.1.0",
        "name": "PyFlix",
        "description": "Turns torrents into HTTP streams.",
        "resources": ["stream"],
        "types": ["movie", "series"],
        "catalogs": [],
        "idPrefixes": ["tt"],
        "logo": logo_url,
        "background": background_url
    }
    return respond_with(manifest)

@app.route("/stream/<type>/<id>.json")
async def get_stream(type, id):
    print('get_stream')
    parts = id.split(":")
    video_id, season, episode = (parts + [None, None, None])[:3]
    torrents = await fetch_torrents(video_id, type, season, episode)
    sorted_torrents = sort_torrents_by_quality(torrents)
    sorted_and_cached_torrents = await check_and_append_cache_status(sorted_torrents)
    
    streams = [
        {
            "name": f"PyFlix {'☁️✅' if torrent['cache_status'] == 'CACHED' else '☁️❌'}", 
            "title": torrent['title'], 
            "infoHash": torrent['infoHash'],
            "url": f"http://{request.host}/convert/{torrent['infoHash']}"
        } 
        for torrent in sorted_and_cached_torrents
    ]
    
    return respond_with({"streams": streams})

# convert_torrent sends the selected torrent through the real_debrid.py process
@app.route("/convert/<infoHash>")
def convert_torrent(infoHash):
    global conversion_locks, conversion_results
    lock = conversion_locks.setdefault(infoHash, Lock())

    with lock:
        if infoHash in conversion_results and time.time() - conversion_results[infoHash]['timestamp'] < 5:
            return redirect(conversion_results[infoHash]['url'])
        print('convert_torrent called for', infoHash)
        try:
            direct_stream_url = real_debrid.main(infoHash)
            conversion_results[infoHash] = {'url': direct_stream_url, 'timestamp': time.time()}
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return redirect(direct_stream_url)

if __name__ == "__main__":
    app.run(debug=FLASK_DEBUG, host=FLASK_HOST, port=FLASK_PORT)





