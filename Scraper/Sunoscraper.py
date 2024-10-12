import os
import json
import time
import re
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from rich.console import Console, Group
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn, MofNCompleteColumn
from rich.live import Live
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text

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

# Rich Console
console = Console()

# Lade JSON Datei, falls vorhanden
def load_json(file_path):
    """Lädt eine bestehende JSON-Datei, falls vorhanden."""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {}

# Speichern der JSON Datei
def save_json(data, file_path):
    """Speichert die JSON-Datei."""
    with open(file_path, 'w', encoding="utf-8") as file:
        json.dump(data, file, indent=4)
    # Entfernt console.log-Ausgaben, um die Anzeige sauber zu halten

# Bereinige ungültige Zeichen im Dateinamen
def clean_filename(filename):
    """Bereinigt den Dateinamen von ungültigen Zeichen."""
    return re.sub(r'[<>:"/\\|?*]', '', filename)

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
            # Dateinamen ohne Erweiterung
            name = filename[:-5]
            # Song-ID extrahieren (letzter Unterstrich)
            song_id = name.split('_')[-1]
            song_ids.add(song_id)
    return song_ids

# Panels erstellen mit mutable Text Objekten
def create_last_song_panel(last_song_info):
    if not last_song_info['content']:
        return Panel("Keine Informationen zum letzten Song.", title="Letzter Song", border_style="green")
    else:
        return Panel(last_song_info['content'], title="Letzter Song", border_style="green")

def create_current_song_panel(current_song_info):
    if not current_song_info['content']:
        return Panel("Keine Informationen zum aktuellen Song.", title="Aktueller Song", border_style="cyan")
    else:
        return Panel(current_song_info['content'], title="Aktueller Song", border_style="cyan")

# Playlists scrapen und Song-Links sammeln
def scrape_playlists(driver):
    """Scraped die Startseite nach Playlists und deren Songs."""
    playlists = load_json(SCRAPED_PLAYLISTS_FILE)  # Vorhandene Daten laden
    total_songs = 0
    console.log("Öffne die Webseite [blue]suno.com[/blue]...")
    driver.get("https://suno.com")
    time.sleep(5)  # Warte, bis die Seite geladen ist

    console.log("Suche nach Playlist-Links auf der Startseite...")
    playlist_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/playlist/')]")
    playlist_urls = list(set([link.get_attribute("href") for link in playlist_links]))  # Duplikate entfernen
    console.log(f"Gefundene Playlist-Links: {len(playlist_urls)}")

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Playlists scrapen...", total=len(playlist_urls))
        for playlist_url in playlist_urls:
            driver.get(playlist_url)
            time.sleep(5)  # Warte, bis die Playlist-Seite geladen ist

            song_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/song/')]")
            song_urls = list(set([link.get_attribute("href") for link in song_links]))  # Duplikate entfernen

            total_songs += len(song_urls)
            playlists[playlist_url] = {"song_urls": song_urls}

            # Speichere die Playlists
            save_json(playlists, SCRAPED_PLAYLISTS_FILE)
            progress.advance(task)

    console.log(f"\n[green]Scraping abgeschlossen:[/green] {len(playlists)} Playlists und {total_songs} Songs wurden gefunden.\n")

    return playlists

# Songinformationen scrapen und speichern
def scrape_songs_from_url_list(url_list, driver):
    """Durchsucht die URLs nach Songs und speichert die Songinformationen."""
    all_styles = load_json(STYLES_FILE) or []
    song_styles_mapping = load_json(SONG_STYLES_MAPPING_FILE) or {}
    all_meta_tags = load_json(META_TAGS_FILE) or []
    song_meta_mapping = load_json(SONG_META_MAPPING_FILE) or {}

    total_playlists = len(url_list)
    total_songs = sum(len(playlist_data['song_urls']) for playlist_data in url_list.values())

    # Bereits verarbeitete Song-IDs abrufen
    processed_song_ids = get_processed_song_ids()

    # Variablen für Panels mit mutable Text Objekten
    last_song_info = {'content': Text()}
    current_song_info = {'content': Text()}

    # Fortschrittsbalken erstellen
    overall_progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )

    playlist_progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )

    song_progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )

    # Initiale Panels
    last_song_panel = create_last_song_panel(last_song_info)
    current_song_panel = create_current_song_panel(current_song_info)

    progress_group = Group(
        Columns(
            [
                last_song_panel,
                current_song_panel
            ]
        ),
        Panel(overall_progress, title="Gesamtfortschritt"),
        Panel(playlist_progress, title="Playlists"),
        Panel(song_progress, title="Songs in Playlist")
    )

    with Live(progress_group, console=console, refresh_per_second=5) as live:
        overall_task = overall_progress.add_task("Gesamtfortschritt", total=total_songs)
        playlist_task = playlist_progress.add_task("Playlists", total=total_playlists)

        for playlist_url, playlist_data in url_list.items():
            # Update Playlist-Fortschritt
            playlist_progress.update(playlist_task, advance=1, description=f"[blue]Playlist: {playlist_url}")
            songs_in_playlist = playlist_data['song_urls']
            song_task = song_progress.add_task("Songs in Playlist", total=len(songs_in_playlist))

            for song_url in songs_in_playlist:
                song_id = extract_song_id_from_url(song_url)

                # Prüfen, ob der Song bereits bearbeitet wurde
                if song_id in processed_song_ids:
                    # Fortschrittsbalken aktualisieren
                    song_progress.advance(song_task)
                    overall_progress.advance(overall_task)
                    continue

                # Aktualisiere current_song_info
                current_song_info['content'] = Text()
                current_song_info['content'].append(f"[bold]Song URL:[/bold] {song_url}\n")
                current_song_info['content'].append(f"[bold]Playlist URL:[/bold] {playlist_url}\n")

                # Aktualisiere das aktuelle Song-Panel
                current_song_panel = create_current_song_panel(current_song_info)

                # Aktualisiere die Panels im progress_group
                progress_group = Group(
                    Columns(
                        [
                            last_song_panel,
                            current_song_panel
                        ]
                    ),
                    Panel(overall_progress, title="Gesamtfortschritt"),
                    Panel(playlist_progress, title="Playlists"),
                    Panel(song_progress, title="Songs in Playlist")
                )

                live.update(progress_group)

                song_progress.update(song_task, description=f"[cyan]Song ID: {song_id}[/cyan]")
                try:
                    song_data = fetch_song_data(driver, song_url)
                    song_title = song_data["title"] or f"Unbekannter_Titel_{int(time.time())}"
                    song_id = extract_song_id_from_url(song_url)

                    # Bereinigen und Speichern der Song-Daten
                    song_file_name = clean_filename(f"{song_title}_{song_id}") + ".json"
                    song_file_path = os.path.join(SONGS_DIR, song_file_name)
                    save_json(song_data, song_file_path)

                    # Aktualisiere die Liste der verarbeiteten Song-IDs
                    processed_song_ids.add(song_id)

                    # Aktualisiere Styles
                    new_styles = [style for style in song_data['styles'] if style not in all_styles]
                    if new_styles:
                        all_styles.extend(new_styles)
                        save_json(all_styles, STYLES_FILE)

                    # Song-Styles-Mapping speichern mit song_url als Schlüssel
                    song_styles_mapping[song_url] = song_data['styles']
                    save_json(song_styles_mapping, SONG_STYLES_MAPPING_FILE)

                    # Meta-Tags extrahieren
                    meta_tags = extract_meta_tags(song_data['lyrics'])
                    new_meta_tags = [tag for tag in meta_tags if tag not in all_meta_tags]
                    if new_meta_tags:
                        all_meta_tags.extend(new_meta_tags)
                        save_json(all_meta_tags, META_TAGS_FILE)

                    # Song-Meta-Mapping speichern mit song_url als Schlüssel
                    song_meta_mapping[song_url] = meta_tags
                    save_json(song_meta_mapping, SONG_META_MAPPING_FILE)

                    # Fortschrittsbalken aktualisieren
                    song_progress.advance(song_task)
                    overall_progress.advance(overall_task)

                    # Aktualisiere last_song_info
                    last_song_info['content'] = Text()
                    last_song_info['content'].append(f"[bold]URL:[/bold] {song_url}\n")
                    last_song_info['content'].append(f"[bold]Titel:[/bold] {song_title}\n")
                    last_song_info['content'].append("[bold]Aktualisierte Dateien:[/bold]\n")
                    last_song_info['content'].append(f"- {song_file_path}\n")
                    last_song_info['content'].append(f"- {STYLES_FILE}\n")
                    last_song_info['content'].append(f"- {SONG_STYLES_MAPPING_FILE}\n")
                    last_song_info['content'].append(f"- {META_TAGS_FILE}\n")
                    last_song_info['content'].append(f"- {SONG_META_MAPPING_FILE}\n")

                    # Aktualisiere das letzte Song-Panel
                    last_song_panel = create_last_song_panel(last_song_info)

                    # Aktualisiere die Panels im progress_group
                    progress_group = Group(
                        Columns(
                            [
                                last_song_panel,
                                current_song_panel
                            ]
                        ),
                        Panel(overall_progress, title="Gesamtfortschritt"),
                        Panel(playlist_progress, title="Playlists"),
                        Panel(song_progress, title="Songs in Playlist")
                    )

                    live.update(progress_group)

                except Exception as e:
                    # Fortschrittsbalken aktualisieren
                    song_progress.advance(song_task)
                    overall_progress.advance(overall_task)

            # Entferne den Song-Task nach Abschluss der Playlist
            song_progress.remove_task(song_task)

        # Entferne den Playlist-Task nach Abschluss aller Playlists
        playlist_progress.remove_task(playlist_task)

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

# Hauptmenü
def main_menu():
    console.print("[bold]Wählen Sie eine Option (1, 2, B):[/bold]")
    console.print("1. URLs Scrapen")
    console.print("2. Songs scrapen")
    console.print("B. Beenden")
    return input("Ihre Wahl: ")

# Hauptfunktion
def main():
    # ChromeDriver Setup
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    while True:
        choice = main_menu()
        if choice == "1":
            playlists = scrape_playlists(driver)
            save_json(playlists, SCRAPED_PLAYLISTS_FILE)
        elif choice == "2":
            scraped_playlists = load_json(SCRAPED_PLAYLISTS_FILE)
            scrape_songs_from_url_list(scraped_playlists, driver)
        elif choice == "B":
            console.print("[bold red]Beenden...[/bold red]")
            break
        else:
            console.print("[red]Ungültige Auswahl. Bitte wählen Sie 1, 2 oder B.[/red]")

    driver.quit()

if __name__ == "__main__":
    main()
