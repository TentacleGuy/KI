from utils import *
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def init_driver(self):
    self.log("Initialisiere Webdriver...")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
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
