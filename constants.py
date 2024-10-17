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

####Datenvorbereitung####
EXPECTED_KEYS = {
    "title": ["title", "songtitle", "name"],
    "lyrics": ["lyrics", "text", "songtext"],
    "styles": ["styles", "genre", "genres", "style"],
    "metatags": ["metatags", "tags", "meta"],
    "language": ["language", "lang", "sprache"]
}

####Training####
#trainingdata
TRAININGDATA_FILE = 'trainingdata.json'

# Standardwerte für das Training
DEFAULT_MODEL_NAME = "gpt2"
DEFAULT_EPOCHS = 3
DEFAULT_LEARNING_RATE = 5e-5
DEFAULT_BATCH_SIZE = 4
DEFAULT_MAX_LENGTH = 128
DEFAULT_WARMUP_STEPS = 500
DEFAULT_WEIGHT_DECAY = 0.01
DEFAULT_GRADIENT_ACCUMULATION_STEPS = 4
DEFAULT_LOGGING_STEPS = 100
DEFAULT_SAVE_STEPS = 500
DEFAULT_EVAL_STEPS = 500

