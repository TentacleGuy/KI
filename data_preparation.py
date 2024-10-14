import os
import json
from langdetect import detect  # Bibliothek zur Spracherkennung
import time
from utils import clean_song_data  # Importiere die Bereinigungsfunktion aus der utils.py
from constants import *

def prepare_data(song_folder_path, title_key, lyrics_key, styles_key, metatag_key, language_key, detect_language, progress_callback, log_callback):
    training_data_file = 'trainingdata.json'

    # Überprüfe, ob die Datei existiert, wenn nicht, erstelle sie
    if not os.path.exists(training_data_file) or os.path.getsize(training_data_file) == 0:
        with open(training_data_file, 'w', encoding='utf-8') as file:
            json.dump([], file, ensure_ascii=False, indent=4)

    # Lade bestehende Daten (falls vorhanden)
    try:
        with open(training_data_file, 'r', encoding='utf-8') as file:
            existing_data = json.load(file)
    except json.JSONDecodeError:
        log_callback(f"Fehler beim Laden von {training_data_file}, Initialisiere als leeres Array.")
        existing_data = []

    # Liste der JSON-Dateien im Songs-Ordner
    json_files = [f for f in os.listdir(song_folder_path) if f.endswith('.json')]
    total_songs = len(json_files)

    if total_songs == 0:
        log_callback("Keine Songs im Verzeichnis gefunden.")
        return 0, 0

    # Initialisierung der Zähler
    processed_songs = 0
    skipped_existing = 0
    skipped_lyrics = 0

    # Bearbeitung der Dateien
    for json_file in json_files:
        file_path = os.path.join(song_folder_path, json_file)

        log_callback(f"Bearbeite Song: {json_file}")

        # Prüfen, ob der Song bereits vorhanden ist (in der trainingdata.json)
        if any(song.get('filename') == json_file for song in existing_data):
            log_callback(f"Song bereits bearbeitet, wird übersprungen.")
            skipped_existing += 1
            # Fortschrittsbalken aktualisieren
            progress_callback(processed_songs, total_songs, skipped_existing, skipped_lyrics)
            continue

        with open(file_path, 'r', encoding='utf-8') as file:
            song_data = json.load(file)

        title = song_data.get(title_key, "No Title")
        lyrics = song_data.get(lyrics_key, "")
        styles = song_data.get(styles_key, [])
        metatags = song_data.get(metatag_key, [])

        # Wenn keine Lyrics vorhanden sind, überspringen
        if not lyrics:
            log_callback(f"Song hat keine Lyrics, wird übersprungen.")
            skipped_lyrics += 1
            # Fortschrittsbalken aktualisieren
            progress_callback(processed_songs, total_songs, skipped_existing, skipped_lyrics)
            continue

        # Spracherkennung, falls aktiviert
        if detect_language:
            try:
                language = detect(lyrics)
            except:
                language = "unknown"
        else:
            language = song_data.get(language_key, "unknown")

        # Bereinigen und den Dateinamen hinzufügen
        cleaned_song_data = clean_song_data({
            "title": title,
            "lyrics": lyrics,
            "styles": styles,
            "metatags": metatags,
            "language": language,
            "filename": json_file  # Dateiname
        })

        # Füge die Daten zu den vorhandenen hinzu
        existing_data.append(cleaned_song_data)

        # Schreibe die Daten sofort nach jedem Song
        with open(training_data_file, 'w', encoding='utf-8') as outfile:
            json.dump(existing_data, outfile, ensure_ascii=False, indent=4)

        processed_songs += 1
        # Fortschrittsbalken aktualisieren
        progress_callback(processed_songs, total_songs, skipped_existing, skipped_lyrics)

    return processed_songs, total_songs
