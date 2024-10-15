# Ordner für die Song-JSON-Dateien
SONGS_DIR = "songs"
SONG_META_DIR = "song_meta"  # Neuer Ordner für die JSON-Dateien

# JSON Datei Pfade im Ordner 'song_meta'
SCRAPED_PLAYLISTS_FILE = f"{SONG_META_DIR}/auto_playlists_and_songs.json"
MANUAL_PLAYLISTS_FILE = f"{SONG_META_DIR}/manual_playlists_and_songs.json"
STYLES_FILE = f"{SONG_META_DIR}/all_styles.json"
SONG_STYLES_MAPPING_FILE = f"{SONG_META_DIR}/song_styles_mapping.json"
META_TAGS_FILE = f"{SONG_META_DIR}/all_meta_tags.json"
SONG_META_MAPPING_FILE = f"{SONG_META_DIR}/song_meta_mapping.json"


#Datenvorbereitung
EXPECTED_KEYS = {
    "title": ["title", "songtitle", "name"],
    "lyrics": ["lyrics", "text", "songtext"],
    "styles": ["styles", "genre", "genres", "style"],
    "metatags": ["metatags", "tags", "meta"],
    "language": ["language", "lang", "sprache"]
}

#trainingdata
TRAININGDATA_FILE = 'trainingdata.json'

#Training
# Standardwerte für das Training
DEFAULT_EPOCHS = 10
DEFAULT_LEARNING_RATE = 0.001
DEFAULT_BATCH_SIZE = 32


