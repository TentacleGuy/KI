import os
import json
from langdetect import detect  # Bibliothek zur Spracherkennung
import time
from utils import clean_song_data  # Importiere die Bereinigungsfunktion aus der utils.py

def prepare_data(song_folder_path, title_key, lyrics_key, styles_key, metatag_key, language_key, detect_language, progress_callback):
    training_data = []
    
    # Hole alle JSON-Dateien aus dem Ordner
    json_files = [f for f in os.listdir(song_folder_path) if f.endswith('.json')]
    total_songs = len(json_files)
    processed_songs = 0

    for json_file in json_files:
        file_path = os.path.join(song_folder_path, json_file)

        # Lade die JSON-Datei
        with open(file_path, 'r', encoding='utf-8') as file:
            song_data = json.load(file)

        # Extrahiere die Trainingsdaten basierend auf den Keys
        title = song_data.get(title_key, "No Title")
        lyrics = song_data.get(lyrics_key, "")
        styles = song_data.get(styles_key, [])
        metatags = song_data.get(metatag_key, [])

        # Überspringe Songs ohne Lyrics
        if not lyrics:
            continue

        # Wenn die automatische Spracherkennung aktiviert ist
        if detect_language:
            try:
                language = detect(lyrics)
            except:
                language = "unknown"
        else:
            language = song_data.get(language_key, "unknown")

        # Erstelle ein Trainingsdatensatz-Objekt vor der Bereinigung
        song_data_to_clean = {
            "title": title,
            "lyrics": lyrics,
            "styles": styles,
            "metatags": metatags,
            "language": language
        }

        # Bereinigung der Songdaten
        cleaned_song_data = clean_song_data(song_data_to_clean)

        # Trainingsdatensatz zur Liste hinzufügen
        training_data.append(cleaned_song_data)

        # Aktualisiere den Fortschritt
        processed_songs += 1
        progress = (processed_songs / total_songs) * 100
        progress_callback(progress)
        time.sleep(0.1)  # Simuliert die Bearbeitungszeit, damit der Fortschrittsbalken sichtbar ist

    # Speichere die verarbeiteten Daten in die Datei trainingdata.json
    with open('trainingdata.json', 'w', encoding='utf-8') as outfile:
        json.dump(training_data, outfile, ensure_ascii=False, indent=4)

    return processed_songs, total_songs
