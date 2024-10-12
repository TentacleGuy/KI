import os
import time
import re
import json
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from threading import Lock

SONGS_DIR = "songs"
SCRAPED_PLAYLISTS_FILE = "auto_playlists_and_songs.json"
STYLES_FILE = "all_styles.json"
SONG_STYLES_MAPPING_FILE = "song_styles_mapping.json"
META_TAGS_FILE = "all_meta_tags.json"
SONG_META_MAPPING_FILE = "song_meta_mapping.json"

if not os.path.exists(SONGS_DIR):
    os.makedirs(SONGS_DIR)

file_lock = Lock()

def load_json(file_path):
    """Lädt eine bestehende JSON-Datei, falls vorhanden."""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {}

def save_json(data, file_path):
    """Speichert die JSON-Datei unter Verwendung eines Sperrmechanismus."""
    with file_lock:
        with open(file_path, 'w', encoding="utf-8") as file:
            json.dump(data, file, indent=4)

def init_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def clean_filename(filename):
    filename = re.sub(r'[^A-Za-z0-9 _\-.]', '', filename)
    filename = re.sub(r'\s+', ' ', filename).strip()
    return filename

def extract_meta_tags(lyrics):
    return re.findall(r'\[(.*?)\]', lyrics)

def extract_song_id_from_url(song_url):
    match = re.search(r'/song/([^/]+)', song_url)
    if match:
        return match.group(1)
    return "unbekannte_id"

def get_processed_song_ids():
    song_ids = set()
    for filename in os.listdir(SONGS_DIR):
        if filename.endswith('.json'):
            name = filename[:-5]
            song_id = name.split('_')[-1]
            song_ids.add(song_id)
    return song_ids

def fetch_song_data(driver, song_url):
    driver.get(song_url)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    song_container = soup.find('div', class_='bg-vinylBlack-darker w-full h-full flex flex-col')

    if not song_container:
        return {}

    title_input = song_container.find('input')
    title = title_input['value'] if title_input else None

    genres = [a.get_text(strip=True).replace(",", "").replace(" ", "") for a in song_container.find_all('a', href=lambda href: href and '/style/' in href)]
    genres = genres or ["Keine Genres gefunden"]

    lyrics_textarea = song_container.find('textarea')
    lyrics = lyrics_textarea.get_text(strip=True) if lyrics_textarea else "Keine Lyrics gefunden"

    return {
        "song_url": song_url,
        "title": title,
        "styles": genres,
        "lyrics": lyrics
    }

def scrape_playlists(driver, log, update_progress_playlist):
    playlists = load_json(SCRAPED_PLAYLISTS_FILE)
    total_songs = 0
    log("Öffne die Webseite suno.com...")
    driver.get("https://suno.com")
    time.sleep(5)

    log("Suche nach Playlist-Links auf der Startseite...")
    playlist_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/playlist/')]")
    playlist_urls = list(set([link.get_attribute("href") for link in playlist_links]))
    log(f"Gefundene Playlist-Links: {len(playlist_urls)}")

    for playlist_url in playlist_urls:
        driver.get(playlist_url)
        time.sleep(5)

        song_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/song/')]")
        song_urls = list(set([link.get_attribute("href") for link in song_links]))

        total_songs += len(song_urls)
        playlists[playlist_url] = {"song_urls": song_urls}
        update_progress_playlist()

    log(f"Scraping abgeschlossen: {len(playlists)} Playlists und {total_songs} Songs wurden gefunden.")
    return playlists

def scrape_songs_from_url_list(url_list, driver, log, update_progress_song, update_progress_playlist):
    all_styles = load_json(STYLES_FILE) or []
    song_styles_mapping = load_json(SONG_STYLES_MAPPING_FILE) or {}
    all_meta_tags = load_json(META_TAGS_FILE) or []
    song_meta_mapping = load_json(SONG_META_MAPPING_FILE) or {}

    total_songs = sum(len(playlist_data['song_urls']) for playlist_data in url_list.values())
    processed_song_ids = get_processed_song_ids()

    for playlist_url, playlist_data in url_list.items():
        songs_in_playlist = playlist_data['song_urls']
        update_progress_playlist()

        for song_url in songs_in_playlist:
            song_id = extract_song_id_from_url(song_url)

            if song_id in processed_song_ids:
                log(f"Song bereits bearbeitet, überspringe: {song_url}")
                update_progress_song()
                continue

            log(f"Scrape Song: {song_url}")
            try:
                song_data = fetch_song_data(driver, song_url)
                song_title = song_data["title"] or f"Unbekannter_Titel_{int(time.time())}"
                song_id = extract_song_id_from_url(song_url)

                updated_files = []

                song_file_name = clean_filename(f"{song_title}_{song_id}") + ".json"
                song_file_path = os.path.join(SONGS_DIR, song_file_name)
                save_json(song_data, song_file_path)
                updated_files.append(song_file_path)

                processed_song_ids.add(song_id)

                new_styles = [style for style in song_data['styles'] if style not in all_styles]
                if new_styles:
                    all_styles.extend(new_styles)
                    save_json(all_styles, STYLES_FILE)
                    updated_files.append(STYLES_FILE)

                song_styles_mapping[song_url] = song_data['styles']
                save_json(song_styles_mapping, SONG_STYLES_MAPPING_FILE)
                updated_files.append(SONG_STYLES_MAPPING_FILE)

                meta_tags = extract_meta_tags(song_data['lyrics'])
                new_meta_tags = [tag for tag in meta_tags if tag not in all_meta_tags]
                if new_meta_tags:
                    all_meta_tags.extend(new_meta_tags)
                    save_json(all_meta_tags, META_TAGS_FILE)
                    updated_files.append(META_TAGS_FILE)

                song_meta_mapping[song_url] = meta_tags
                save_json(song_meta_mapping, SONG_META_MAPPING_FILE)
                updated_files.append(SONG_META_MAPPING_FILE)

                log(f"Song gespeichert: {song_title}")
            except Exception as e:
                log(f"Fehler beim Abrufen der Song-Daten von {song_url}: {e}")
            finally:
                update_progress_song()
