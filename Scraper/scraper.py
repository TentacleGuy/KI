import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from utils import *

# Initialisiere den Webdriver im Headless-Modus
def init_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

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

# Playlists scrapen und Song-Links sammeln
def scrape_playlists(driver, log_func):
    playlists = load_json("auto_playlists_and_songs.json")  # Vorhandene Daten laden
    log_func("Öffne die Webseite suno.com...")
    driver.get("https://suno.com")
    time.sleep(5)  # Warte, bis die Seite geladen ist

    log_func("Suche nach Playlist-Links auf der Startseite...")
    playlist_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/playlist/')]")
    playlist_urls = list(set([link.get_attribute("href") for link in playlist_links]))  # Duplikate entfernen
    log_func(f"Gefundene Playlist-Links: {len(playlist_urls)}")

    for playlist_url in playlist_urls:
        driver.get(playlist_url)
        time.sleep(5)  # Warte, bis die Playlist-Seite geladen ist

        song_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/song/')]")
        song_urls = list(set([link.get_attribute("href") for link in song_links]))  # Duplikate entfernen

        playlists[playlist_url] = {"song_urls": song_urls}
        log_func(f"Playlist gescrapt: {playlist_url} mit {len(song_urls)} Songs.")

    save_json(playlists, "auto_playlists_and_songs.json")
    return playlists

# Songinformationen scrapen und speichern
def scrape_songs(driver, url_list, log_func):
    all_styles = load_json("all_styles.json") or []
    song_styles_mapping = load_json("song_styles_mapping.json") or {}
    processed_song_ids = set()  # Implementiere eine Methode, um verarbeitete Songs zu verfolgen

    for playlist_url, playlist_data in url_list.items():
        for song_url in playlist_data['song_urls']:
            song_id = extract_song_id_from_url(song_url)

            # Prüfen, ob der Song bereits bearbeitet wurde
            if song_id in processed_song_ids:
                log_func(f"Song bereits bearbeitet, überspringe: {song_url}")
                continue

            log_func(f"Scrape Song: {song_url}")
            song_data = fetch_song_data(driver, song_url)
            if not song_data:
                log_func(f"Fehler beim Abrufen von {song_url}")
                continue

            song_title = clean_filename(f"{song_data['title']}_{song_id}") + ".json"
            song_path = f"songs/{song_title}"
            save_json(song_data, song_path)

            # Füge den Song zur Liste der verarbeiteten Songs hinzu
            processed_song_ids.add(song_id)

            # Aktualisiere Styles und Song-Styles-Mapping
            new_styles = [style for style in song_data['styles'] if style not in all_styles]
            if new_styles:
                all_styles.extend(new_styles)
                save_json(all_styles, "all_styles.json")

            song_styles_mapping[song_url] = song_data['styles']
            save_json(song_styles_mapping, "song_styles_mapping.json")

            log_func(f"Song gespeichert: {song_title}")

            return song_data
