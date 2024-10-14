import os
import json
from langdetect import detect  # Bibliothek zur Spracherkennung
import time
from utils import clean_song_data  # Importiere die Bereinigungsfunktion aus der utils.py

def prepare_data(song_folder_path, title_key, lyrics_key, styles_key, metatag_key, language_key, detect_language, progress_callback, log_callback):
    training_data_file = 'trainingdata.json'

    # Überprüfe, ob die Datei existiert, wenn nicht, erstelle sie
    if not os.path.exists(training_data_file):
        with open(training_data_file, 'w', encoding='utf-8') as file:
            json.dump([], file, ensure_ascii=False, indent=4)

    # Lade bestehende Daten (falls vorhanden)
    with open(training_data_file, 'r', encoding='utf-8') as file:
        existing_data = json.load(file)

    json_files = [f for f in os.listdir(song_folder_path) if f.endswith('.json')]
    total_songs = len(json_files)
    processed_songs = 0

    for json_file in json_files:
        file_path = os.path.join(song_folder_path, json_file)
        
        # Protokollieren, welcher Song gerade bearbeitet wird
        log_callback(f"Bearbeite Song: {json_file}")

        # Falls der Song bereits bearbeitet wurde, überspringen
        if any(song.get('filename') == json_file for song in existing_data):
            log_callback(f"Song bereits bearbeitet: {json_file}, überspringen.")
            continue

        with open(file_path, 'r', encoding='utf-8') as file:
            song_data = json.load(file)

        title = song_data.get(title_key, "No Title")
        lyrics = song_data.get(lyrics_key, "")
        styles = song_data.get(styles_key, [])
        metatags = song_data.get(metatag_key, [])

        if not lyrics:
            log_callback(f"Song {json_file} hat keine Lyrics, überspringen.")
            continue

        if detect_language:
            try:
                language = detect(lyrics)
            except:
                language = "unknown"
        else:
            language = song_data.get(language_key, "unknown")

        # Songdaten bereinigen und den Dateinamen hinzufügen
        cleaned_song_data = clean_song_data({
            "title": title,
            "lyrics": lyrics,
            "styles": styles,
            "metatags": metatags,
            "language": language,
            "filename": json_file  # Speichere den Dateinamen
        })

        existing_data.append(cleaned_song_data)

        # Speichern der Daten in die Datei, um Datenverlust bei Abstürzen zu verhindern
        with open(training_data_file, 'w', encoding='utf-8') as outfile:
            json.dump(existing_data, outfile, ensure_ascii=False, indent=4)

        processed_songs += 1
        progress = (processed_songs / total_songs) * 100
        progress_callback(progress, processed_songs, total_songs)
        log_callback(f"Song verarbeitet: {json_file}")

    return processed_songs, total_songs
