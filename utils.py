import re
import regex
import os
import json
from threading import Lock
from constants import *


# Erstelle die Ordner, falls sie nicht vorhanden sind
if not os.path.exists(SONGS_DIR):
    os.makedirs(SONGS_DIR)

if not os.path.exists(SONG_META_DIR):  # Füge dies für den neuen song_meta-Ordner hinzu
    os.makedirs(SONG_META_DIR)

# Sperrmechanismus für Dateioperationen (Vermeidung von Konflikten bei parallelen Schreibvorgängen)
file_lock = Lock()

#textfilter
def remove_non_text_characters(text):
    # Regex, der Buchstaben, Zahlen und eine breite Palette von Satzzeichen und Symbolen zulässt
    pattern = regex.compile(r'[^\p{L}\p{N}\s\.,\'#,\.\-_:;!"§$%&/()=?{[\]}\´`+*~#\'|<>]', regex.UNICODE)
    return pattern.sub('', text)

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
    return re.findall(r'\[.*?\]', lyrics)

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

################Trainingdata#########################

def clean_song_data(song_data):
    """Bereinigt die Felder eines Songs und entfernt unnötige Leerzeichen"""
    title = remove_non_text_characters(song_data.get('title', '')).strip()
    lyrics = remove_non_text_characters(song_data.get('lyrics', '')).strip()
    styles = [remove_non_text_characters(style).strip() for style in song_data.get('styles', [])]
    metatags = [remove_non_text_characters(tag).strip() for tag in song_data.get('metatags', [])]
    language = remove_non_text_characters(song_data.get('language', '')).strip()

    # Hier wird der Dateiname hinzugefügt
    filename = song_data.get('filename', '')

    return {
        "title": title,
        "lyrics": lyrics,
        "styles": styles,
        "metatags": metatags,
        "language": language,
        "filename": filename  # Der Dateiname bleibt jetzt erhalten
    }

