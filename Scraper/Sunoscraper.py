import os
import json
import time
import re
import threading
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
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
    """Lädt eine bestehende JSON-Datei, falls vorhanden."""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {}

# Speichern der JSON Datei mit einem Sperrmechanismus, um Dateikonflikte zu vermeiden
def save_json(data, file_path):
    """Speichert die JSON-Datei unter Verwendung eines Sperrmechanismus."""
    with file_lock:
        with open(file_path, 'w', encoding="utf-8") as file:
            json.dump(data, file, indent=4)

# Bereinige ungültige Zeichen im Dateinamen
def clean_filename(filename):
    """Bereinigt den Dateinamen von ungültigen Zeichen."""
    filename = re.sub(r'[^A-Za-z0-9 _\-.]', '', filename)
    filename = re.sub(r'\s+', ' ', filename).strip()
    return filename

# Meta-Tags extrahieren
def extract_meta_tags(lyrics):
    """Extrahiert Meta-Tags aus dem Songtext."""
    return re.findall(r'\[(.*?)\]', lyrics)

# Song-ID aus der URL extrahieren
def extract_song_id_from_url(song_url):
    """Extrahiert die kryptische Song-ID aus der URL."""
    match = re.search(r'/song/([^/]+)', song_url)
    if match:
        return match.group(1)
    return "unbekannte_id"

# Verarbeitete Song-IDs aus den Dateinamen im 'songs'-Ordner abrufen
def get_processed_song_ids():
    """Gibt ein Set der Song-IDs zurück, die bereits im 'songs'-Ordner vorhanden sind."""
    song_ids = set()
    for filename in os.listdir(SONGS_DIR):
        if filename.endswith('.json'):
            name = filename[:-5]  # Dateinamen ohne Erweiterung
            song_id = name.split('_')[-1]  # Song-ID extrahieren (letzter Unterstrich)
            song_ids.add(song_id)
    return song_ids

# Song-Daten abrufen
def fetch_song_data(driver, song_url):
    """Ruft die Song-Daten von der Songseite ab."""
    driver.get(song_url)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Suche nach dem Container-div basierend auf der class
    song_container = soup.find('div', class_='bg-vinylBlack-darker w-full h-full flex flex-col sm:flex-col md:flex-col lg:flex-row xl:flex-row lg:mt-8 xl:mt-8 lg:ml-32 xl:ml-32 overflow-y-scroll items-center sm:items-center md:items-center lg:items-start xl:items-start')

    if not song_container:
        return {}

    # Suche nach dem Titel im input-Feld
    title_input = song_container.find('input')
    title = title_input['value'] if title_input else None

    # Suche nach Genres
    genres = [a.get_text(strip=True).replace(",", "").replace(" ", "") for a in song_container.find_all('a', href=lambda href: href and '/style/' in href)]
    genres = genres or ["Keine Genres gefunden"]

    # Suche nach Songtext
    lyrics_textarea = song_container.find('textarea')
    lyrics = lyrics_textarea.get_text(strip=True) if lyrics_textarea else "Keine Lyrics gefunden"

    return {
        "song_url": song_url,
        "title": title,
        "styles": genres,
        "lyrics": lyrics
    }

# Hauptklasse für die GUI-Anwendung
class SunoScraperApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Suno Scraper")
        self.geometry("800x600")

        # Initialisiere Variablen
        self.playlists = {}
        self.scraped_playlists = {}
        self.driver = None
        self.is_scraping = False

        # Variablen für aktuelle und letzte Songinfos
        self.last_song_info = {}
        self.current_song_info = {}

        # Konfiguration des Hauptfensters
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)  # Zeile für main_frame

        # Erstelle Widgets
        self.create_widgets()

    def create_widgets(self):
        # Rahmen für die Buttons oben
        button_frame = tk.Frame(self)
        button_frame.grid(row=0, column=0, sticky="ew")
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        # Buttons für Aktionen
        scrape_playlists_button = ttk.Button(button_frame, text="URLs Scrapen", command=self.start_scrape_playlists)
        scrape_playlists_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        scrape_songs_button = ttk.Button(button_frame, text="Songs Scrapen", command=self.start_scrape_songs)
        scrape_songs_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Hauptframe für die zwei Spalten und Fortschrittsbalken
        main_frame = tk.Frame(self)
        main_frame.grid(row=1, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=0)  # Info frame
        main_frame.rowconfigure(1, weight=0)  # Progress frame
        main_frame.rowconfigure(2, weight=1)  # Output text

        # Rahmen für die zwei Spalten (letzter und aktueller Song)
        info_frame = tk.Frame(main_frame)
        info_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        info_frame.columnconfigure(0, weight=1)
        info_frame.columnconfigure(1, weight=1)

        # Spalte für letzter Song
        last_song_frame = tk.LabelFrame(info_frame, text="Letzter Song", padx=10, pady=10)
        last_song_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.last_song_text = tk.Text(last_song_frame, wrap=tk.WORD, height=10)
        self.last_song_text.pack(expand=True, fill='both')

        # Spalte für aktueller Song
        current_song_frame = tk.LabelFrame(info_frame, text="Aktueller Song", padx=10, pady=10)
        current_song_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        self.current_song_text = tk.Text(current_song_frame, wrap=tk.WORD, height=10)
        self.current_song_text.pack(expand=True, fill='both')

        # Rahmen für Fortschrittsbalken
        progress_frame = tk.Frame(main_frame)
        progress_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)

        # Fortschrittsbalken
        self.overall_label = ttk.Label(progress_frame, text="Gesamtfortschritt")
        self.overall_label.pack()
        self.overall_progress = ttk.Progressbar(progress_frame, orient='horizontal', mode='determinate')
        self.overall_progress.pack(fill=tk.X, pady=5)

        self.playlist_label = ttk.Label(progress_frame, text="Playlists")
        self.playlist_label.pack()
        self.playlist_progress = ttk.Progressbar(progress_frame, orient='horizontal', mode='determinate')
        self.playlist_progress.pack(fill=tk.X, pady=5)

        self.song_label = ttk.Label(progress_frame, text="Songs in Playlist")
        self.song_label.pack()
        self.song_progress = ttk.Progressbar(progress_frame, orient='horizontal', mode='determinate')
        self.song_progress.pack(fill=tk.X, pady=5)

        # Ausgabe-Textfeld
        self.output_text = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD)
        self.output_text.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.rowconfigure(2, weight=1)  # Ausgabe-Textfeld expandiert

    def log(self, message):
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)
        self.update()  # Hier wird die GUI sofort aktualisiert

    def update_last_song_info(self):
        self.last_song_text.delete('1.0', tk.END)
        if self.last_song_info:
            content = f"URL: {self.last_song_info.get('song_url', '')}\n"
            content += f"Titel: {self.last_song_info.get('title', '')}\n"
            content += f"Styles: {', '.join(self.last_song_info.get('styles', []))}\n"
            if 'updated_files' in self.last_song_info:
                content += "Aktualisierte Dateien:\n"
                for file in self.last_song_info['updated_files']:
                    content += f"- {file}\n"
            self.last_song_text.insert(tk.END, content)
        self.update()  # Sofortige GUI-Aktualisierung

    def update_current_song_info(self):
        self.current_song_text.delete('1.0', tk.END)
        if self.current_song_info:
            content = f"Song URL: {self.current_song_info.get('song_url', '')}\n"
            content += f"Playlist URL: {self.current_song_info.get('playlist_url', '')}\n"
            self.current_song_text.insert(tk.END, content)
        self.update()  # Sofortige GUI-Aktualisierung

    def start_scrape_playlists(self):
        if not self.is_scraping:
            threading.Thread(target=self.scrape_playlists_thread).start()
        else:
            messagebox.showinfo("Info", "Ein Scraping-Prozess läuft bereits.")

    def scrape_playlists_thread(self):
        self.is_scraping = True
        self.log("Starte das Scrapen der Playlists...")

        self.init_driver()
        try:
            self.playlists = self.scrape_playlists()
            save_json(self.playlists, SCRAPED_PLAYLISTS_FILE)
            self.log("Playlists wurden erfolgreich gescrapt und gespeichert.")
        finally:
            self.driver.quit()
            self.driver = None
            self.is_scraping = False

    def start_scrape_songs(self):
        if not self.is_scraping:
            self.scraped_playlists = load_json(SCRAPED_PLAYLISTS_FILE)
            if self.scraped_playlists:
                threading.Thread(target=self.scrape_songs_thread).start()
            else:
                messagebox.showwarning("Warnung", "Keine Playlists gefunden. Bitte führen Sie zuerst 'URLs Scrapen' aus.")
        else:
            messagebox.showinfo("Info", "Ein Scraping-Prozess läuft bereits.")

    def scrape_songs_thread(self):
        self.is_scraping = True
        self.log("Starte das Scrapen der Songs...")

        self.init_driver()
        try:
            self.scrape_songs_from_url_list(self.scraped_playlists)
            self.log("Songs wurden erfolgreich gescrapt und gespeichert.")
        finally:
            self.driver.quit()
            self.driver = None
            self.is_scraping = False

    def init_driver(self):
        self.log("Initialisiere Webdriver...")
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.log("Webdriver initialisiert.")

    # Playlists scrapen und Song-Links sammeln
    def scrape_playlists(self):
        playlists = load_json(SCRAPED_PLAYLISTS_FILE)  # Vorhandene Daten laden
        total_songs = 0
        self.log("Öffne die Webseite suno.com...")
        self.driver.get("https://suno.com")
        time.sleep(5)  # Warte, bis die Seite geladen ist

        self.log("Suche nach Playlist-Links auf der Startseite...")
        playlist_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/playlist/')]")
        playlist_urls = list(set([link.get_attribute("href") for link in playlist_links]))  # Duplikate entfernen
        self.log(f"Gefundene Playlist-Links: {len(playlist_urls)}")

        self.playlist_progress['maximum'] = len(playlist_urls)
        self.playlist_progress['value'] = 0

        for playlist_url in playlist_urls:
            self.driver.get(playlist_url)
            time.sleep(5)  # Warte, bis die Playlist-Seite geladen ist

            song_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/song/')]")
            song_urls = list(set([link.get_attribute("href") for link in song_links]))  # Duplikate entfernen

            total_songs += len(song_urls)
            playlists[playlist_url] = {"song_urls": song_urls}

            # Fortschrittsbalken aktualisieren
            self.playlist_progress['value'] += 1
            self.playlist_label.config(text=f"Playlists: {self.playlist_progress['value']}/{len(playlist_urls)}")
            self.log(f"Playlist gescrapt: {playlist_url} mit {len(song_urls)} Songs.")
            self.update()  # Sofortige GUI-Aktualisierung

        self.log(f"Scraping abgeschlossen: {len(playlists)} Playlists und {total_songs} Songs wurden gefunden.")
        self.playlist_progress['value'] = 0
        return playlists

    # Songinformationen scrapen und speichern
    def scrape_songs_from_url_list(self, url_list):
        all_styles = load_json(STYLES_FILE) or []
        song_styles_mapping = load_json(SONG_STYLES_MAPPING_FILE) or {}
        all_meta_tags = load_json(META_TAGS_FILE) or []
        song_meta_mapping = load_json(SONG_META_MAPPING_FILE) or {}

        total_playlists = len(url_list)
        total_songs = sum(len(playlist_data['song_urls']) for playlist_data in url_list.values())

        # Bereits verarbeitete Song-IDs abrufen
        processed_song_ids = get_processed_song_ids()

        self.overall_progress['maximum'] = total_songs
        self.overall_progress['value'] = 0

        self.playlist_progress['maximum'] = total_playlists
        self.playlist_progress['value'] = 0

        for playlist_url, playlist_data in url_list.items():
            songs_in_playlist = playlist_data['song_urls']

            self.playlist_progress['value'] += 1
            self.playlist_label.config(text=f"Playlists: {self.playlist_progress['value']}/{total_playlists}")

            self.song_progress['maximum'] = len(songs_in_playlist)
            self.song_progress['value'] = 0

            for song_url in songs_in_playlist:
                song_id = extract_song_id_from_url(song_url)

                # Aktualisiere current_song_info
                self.current_song_info = {
                    "song_url": song_url,
                    "playlist_url": playlist_url
                }
                self.update_current_song_info()

                # Prüfen, ob der Song bereits bearbeitet wurde
                if song_id in processed_song_ids:
                    self.log(f"Song bereits bearbeitet, überspringe: {song_url}")
                    self.song_progress['value'] += 1
                    self.overall_progress['value'] += 1
                    self.update()  # Sofortige GUI-Aktualisierung
                    continue

                self.log(f"Scrape Song: {song_url}")
                try:
                    song_data = fetch_song_data(self.driver, song_url)
                    song_title = song_data["title"] or f"Unbekannter_Titel_{int(time.time())}"
                    song_id = extract_song_id_from_url(song_url)

                    # Liste der aktualisierten Dateien initialisieren
                    updated_files = []

                    # Bereinigen und Speichern der Song-Daten
                    song_file_name = clean_filename(f"{song_title}_{song_id}") + ".json"
                    song_file_path = os.path.join(SONGS_DIR, song_file_name)
                    save_json(song_data, song_file_path)
                    updated_files.append(song_file_path)

                    # Aktualisiere die Liste der verarbeiteten Song-IDs
                    processed_song_ids.add(song_id)

                    # Aktualisiere Styles
                    new_styles = [style for style in song_data['styles'] if style not in all_styles]
                    if new_styles:
                        all_styles.extend(new_styles)
                        save_json(all_styles, STYLES_FILE)
                        updated_files.append(STYLES_FILE)

                    # Song-Styles-Mapping speichern mit song_url als Schlüssel
                    song_styles_mapping[song_url] = song_data['styles']
                    save_json(song_styles_mapping, SONG_STYLES_MAPPING_FILE)
                    updated_files.append(SONG_STYLES_MAPPING_FILE)

                    # Meta-Tags extrahieren
                    meta_tags = extract_meta_tags(song_data['lyrics'])
                    new_meta_tags = [tag for tag in meta_tags if tag not in all_meta_tags]
                    if new_meta_tags:
                        all_meta_tags.extend(new_meta_tags)
                        save_json(all_meta_tags, META_TAGS_FILE)
                        updated_files.append(META_TAGS_FILE)

                    # Song-Meta-Mapping speichern mit song_url als Schlüssel
                    song_meta_mapping[song_url] = meta_tags
                    save_json(song_meta_mapping, SONG_META_MAPPING_FILE)
                    updated_files.append(SONG_META_MAPPING_FILE)

                    # Aktualisiere last_song_info
                    self.last_song_info = {
                        "song_url": song_url,
                        "title": song_title,
                        "styles": song_data['styles'],
                        "updated_files": updated_files
                    }
                    self.update_last_song_info()

                    self.log(f"Song gespeichert: {song_title}")
                except Exception as e:
                    self.log(f"Fehler beim Abrufen der Song-Daten von {song_url}: {e}")
                finally:
                    # Fortschrittsbalken aktualisieren
                    self.song_progress['value'] += 1
                    self.song_label.config(text=f"Songs in Playlist: {self.song_progress['value']}/{self.song_progress['maximum']}")
                    self.overall_progress['value'] += 1
                    self.overall_label.config(text=f"Gesamtfortschritt: {self.overall_progress['value']}/{self.overall_progress['maximum']}")
                    self.update()  # Sofortige GUI-Aktualisierung

            # Reset des Song-Fortschrittsbalkens nach jeder Playlist
            self.song_progress['value'] = 0

        # Abschließende Updates
        self.overall_progress['value'] = 0
        self.playlist_progress['value'] = 0
        self.song_progress['value'] = 0

# Hauptprogramm
if __name__ == "__main__":
    app = SunoScraperApp()
    app.mainloop()
