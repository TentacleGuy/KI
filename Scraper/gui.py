import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading  # Für das parallele Ausführen der Scraping-Funktionen
from threading import Lock  # Für den Sperrmechanismus
from scraping import *
from utils import *

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

    def start_scrape_songs(self):
        if not self.is_scraping:
            self.scraped_playlists = load_json(SCRAPED_PLAYLISTS_FILE)
            if self.scraped_playlists:
                threading.Thread(target=self.scrape_songs_thread).start()
            else:
                messagebox.showwarning("Warnung", "Keine Playlists gefunden. Bitte führen Sie zuerst 'URLs Scrapen' aus.")
        else:
            messagebox.showinfo("Info", "Ein Scraping-Prozess läuft bereits.")
