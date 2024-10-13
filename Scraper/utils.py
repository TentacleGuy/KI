import re
import os
import json
from threading import Lock

# Ordner für die Song-JSON-Dateien
SONGS_DIR = "songs"

if not os.path.exists(SONGS_DIR):
    os.makedirs(SONGS_DIR)

# JSON Datei Pfade
SCRAPED_PLAYLISTS_FILE = "auto_playlists_and_songs.json"
MANUAL_PLAYLISTS_FILE = "manual_playlists_and_songs.json"
STYLES_FILE = "all_styles.json"
SONG_STYLES_MAPPING_FILE = "song_styles_mapping.json"
META_TAGS_FILE = "all_meta_tags.json"
SONG_META_MAPPING_FILE = "song_meta_mapping.json"

# Sperrmechanismus für Dateioperationen (Vermeidung von Konflikten bei parallelen Schreibvorgängen)
file_lock = Lock()

# Lade JSON Datei, falls vorhanden
def load_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {}

# Speichern der JSON Datei mit einem Sperrmechanismus, um Dateikonflikte zu vermeiden
def save_json(data, file_path):
    with file_lock:
        with open(file_path, 'w', encoding="utf-8") as file:
            json.dump(data, file, indent=4)

# Bereinige ungültige Zeichen im Dateinamen
def clean_filename(filename):
    filename = re.sub(r'[^A-Za-z0-9 _\-.]', '', filename)
    filename = re.sub(r'\s+', ' ', filename).strip()
    return filename

# Meta-Tags extrahieren
def extract_meta_tags(lyrics):
    return re.findall(r'\[(.*?)\]', lyrics)

# Song-ID aus der URL extrahieren
def extract_song_id_from_url(song_url):
    match = re.search(r'/song/([^/]+)', song_url)
    if match:
        return match.group(1)
    return "unbekannte_id"

# Verarbeitete Song-IDs aus den Dateinamen im 'songs'-Ordner abrufen
def get_processed_song_ids():
    song_ids = set()
    for filename in os.listdir(SONGS_DIR):
        if filename.endswith('.json'):
            name = filename[:-5]  # Dateinamen ohne Erweiterung
            song_id = name.split('_')[-1]  # Song-ID extrahieren (letzter Unterstrich)
            song_ids.add(song_id)
    return song_ids
