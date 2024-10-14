import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import json
import random
from data_preparation import prepare_data
from constants import *
import threading

class SongGeneratorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Song KI Steuerzentrale")
        self.create_widgets()
        self.load_random_json_file()  # Lädt eine zufällige JSON-Datei beim Start

    def create_widgets(self):
        # Tabbed Notebook für die drei Bereiche
        notebook = ttk.Notebook(self)
        notebook.pack(expand=True, fill="both")

        # Tabs für die drei Hauptbereiche
        tab_preparation = ttk.Frame(notebook)
        tab_training = ttk.Frame(notebook)
        tab_generation = ttk.Frame(notebook)

        notebook.add(tab_preparation, text="Datenvorbereitung")
        notebook.add(tab_training, text="Training")
        notebook.add(tab_generation, text="Lyricsgenerator")

        # Inhalte der einzelnen Tabs
        self.create_preparation_tab(tab_preparation)
        self.create_training_tab(tab_training)
        self.create_generation_tab(tab_generation)

    # Datenvorbereitungs-Tab
    def create_preparation_tab(self, parent):
       # Fortschrittsbalken-Rahmen (Anpassung)
        progress_frame = tk.Frame(parent)
        progress_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        # Gesamtfortschritt
        self.progress_label = ttk.Label(progress_frame, text="Song 0 von 0")
        self.progress_label.pack()

        self.progress_bar = ttk.Progressbar(progress_frame, orient='horizontal', mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=5)

        # Fortschrittsbalken für bereits vorhandene Songs (übersprungen)
        self.skipped_existing_label = ttk.Label(progress_frame, text="bereits vorhanden: 0")
        self.skipped_existing_label.pack()

        self.skipped_existing_bar = ttk.Progressbar(progress_frame, orient='horizontal', mode='determinate')
        self.skipped_existing_bar.pack(fill=tk.X, pady=5)

        # Fortschrittsbalken für fehlende Lyrics (übersprungen)
        self.skipped_lyrics_label = ttk.Label(progress_frame, text="keine Lyrics: 0")
        self.skipped_lyrics_label.pack()

        self.skipped_lyrics_bar = ttk.Progressbar(progress_frame, orient='horizontal', mode='determinate')
        self.skipped_lyrics_bar.pack(fill=tk.X, pady=5)

        # JSON Key Felder für Trainingsdaten
        self.json_keys_frame = tk.Frame(parent)
        self.json_keys_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        self.create_key_selection_fields(self.json_keys_frame)

        # Button zum Starten der Datenvorbereitung
        start_button = ttk.Button(parent, text="Daten vorbereiten", command=self.start_data_preparation)
        start_button.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        # Ausgabefeld für Logs und Errors
        log_frame = tk.Frame(parent)
        log_frame.grid(row=4, column=0, padx=10, pady=10, sticky="ew")

        self.log_text = tk.Text(log_frame, height=5, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

    # Key-Auswahl-Felder für Trainingsdaten erstellen
    def create_key_selection_fields(self, parent):
        # Setze den Grid-Manager mit 3 Spalten für je zwei Felder übereinander
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.columnconfigure(2, weight=1)

        # Erste Spalte (Titel Key und Styles Key)
        tk.Label(parent, text="Titel Key:").grid(row=0, column=0, sticky="w")
        self.title_key = ttk.Combobox(parent)
        self.title_key.grid(row=1, column=0, sticky="ew")

        tk.Label(parent, text="Styles Key:").grid(row=2, column=0, sticky="w")
        self.styles_key = ttk.Combobox(parent)
        self.styles_key.grid(row=3, column=0, sticky="ew")

        # Zweite Spalte (Lyrics Key und Metatags Key)
        tk.Label(parent, text="Lyrics Key:").grid(row=0, column=1, sticky="w")
        self.lyrics_key = ttk.Combobox(parent)
        self.lyrics_key.grid(row=1, column=1, sticky="ew")

        tk.Label(parent, text="Metatags Key:").grid(row=2, column=1, sticky="w")
        self.metatags_key = ttk.Combobox(parent)
        self.metatags_key.grid(row=3, column=1, sticky="ew")

        # Dritte Spalte (Sprache Key und Automatische Erkennung)
        tk.Label(parent, text="Sprache Key:").grid(row=0, column=2, sticky="w")
        self.language_key = ttk.Combobox(parent)
        self.language_key.grid(row=1, column=2, sticky="ew")

        self.detect_language_var = tk.IntVar()
        detect_checkbox = ttk.Checkbutton(parent, text="Sprache automatisch erkennen", variable=self.detect_language_var, command=self.toggle_language_key)
        detect_checkbox.grid(row=2, column=2, sticky="w")
    
    def toggle_language_key(self):
        # Deaktiviert das Sprachfeld, wenn die automatische Spracherkennung aktiviert ist
        if self.detect_language_var.get():
            self.language_key.set('')  # Entfernt den gewählten Wert, falls vorhanden
            self.language_key.config(state='disabled')
        else:
            self.language_key.config(state='normal')

    def start_data_preparation(self):
        # Hole den Song-Ordner aus der constants.py
        song_folder = SONGS_DIR
        title_key = self.title_key.get()
        lyrics_key = self.lyrics_key.get()
        styles_key = self.styles_key.get()
        metatags_key = self.metatags_key.get()
        language_key = self.language_key.get() if not self.detect_language_var.get() else None
        detect_language = bool(self.detect_language_var.get())

        # Callback für den Fortschritt
        def update_progress(processed, total, skipped_existing, skipped_lyrics):
            # Fortschritt für die gesamten Songs
            self.progress_bar['value'] = int((processed / total) * 100)
            self.progress_label.config(text=f"Song {processed} von {total}")

            # Fortschritt der übersprungenen Songs (bereits vorhanden)
            self.skipped_existing_bar['value'] = int((skipped_existing / total) * 100)
            self.skipped_existing_label.config(text=f"Übersprungene Songs (bereits vorhanden): {skipped_existing}")

            # Fortschritt der übersprungenen Songs (keine Lyrics)
            self.skipped_lyrics_bar['value'] = int((skipped_lyrics / total) * 100)
            self.skipped_lyrics_label.config(text=f"Übersprungene Songs (keine Lyrics): {skipped_lyrics}")

            self.update_idletasks()

        if title_key and lyrics_key and styles_key and metatags_key and (language_key or detect_language):
            try:
                processed, total = prepare_data(
                    song_folder, title_key, lyrics_key, styles_key, metatags_key, language_key, detect_language, update_progress, self.log
                )
                if total > 0:
                    messagebox.showinfo("Datenvorbereitung", f"Verarbeitung abgeschlossen. {processed} von {total} Songs bearbeitet.")
                else:
                    self.log("Keine Songs zum Bearbeiten gefunden.")
            except Exception as e:
                self.log(f"Fehler bei der Datenvorbereitung: {e}")
        else:
            self.log("Fehler: Bitte alle Felder ausfüllen.")

    def log(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)

    # Daten aus einer zufälligen JSON-Datei laden und die Keys anzeigen
    def load_random_json_file(self):
        self.log(f"Lade Songs aus dem Verzeichnis: {SONGS_DIR}")
        folder = SONGS_DIR  # Verwende den Ordner aus constants.py
        if os.path.isdir(folder):
            json_files = [f for f in os.listdir(folder) if f.endswith('.json')]
            if json_files:
                random_file = random.choice(json_files)
                file_path = os.path.join(folder, random_file)
                self.log(f"Zufällige Datei geladen: {random_file}")
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    self.update_key_selection(data)
            else:
                self.log("Keine JSON-Dateien im Ordner gefunden.")
        else:
            self.log(f"Ordner {folder} nicht gefunden.")

    def update_key_selection(self, data):
        try:
            keys = list(data.keys())
            self.title_key['values'] = keys
            self.lyrics_key['values'] = keys
            self.styles_key['values'] = keys
            self.metatags_key['values'] = keys
            self.language_key['values'] = keys

            # Automatische Auswahl basierend auf den erwarteten Keys aus der constants.py
            self.auto_select_key(self.title_key, keys, EXPECTED_KEYS["title"])
            self.auto_select_key(self.lyrics_key, keys, EXPECTED_KEYS["lyrics"])
            self.auto_select_key(self.styles_key, keys, EXPECTED_KEYS["styles"])
            self.auto_select_key(self.metatags_key, keys, EXPECTED_KEYS["metatags"])
            self.auto_select_key(self.language_key, keys, EXPECTED_KEYS["language"])

            self.log("Keys erfolgreich geladen und (wenn möglich) vorausgewählt.")
        except Exception as e:
            self.log(f"Fehler beim Laden der Keys: {e}")

    def auto_select_key(self, combobox, keys, expected_keywords):
        for key in keys:
            for expected in expected_keywords:
                if expected.lower() in key.lower():
                    combobox.set(key)
                    return  # Sobald wir einen Treffer finden, hören wir auf


    # Trainings-Tab
    def create_training_tab(self, parent):
        # Modell aus Ordner auswählen
        model_frame = tk.Frame(parent)
        model_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.model_path = tk.StringVar()
        model_label = tk.Label(model_frame, text="Modell für Training:")
        model_label.grid(row=0, column=0, sticky="w")
        model_button = ttk.Button(model_frame, text="Modell auswählen", command=self.select_model)
        model_button.grid(row=0, column=1, sticky="ew")
        model_entry = tk.Entry(model_frame, textvariable=self.model_path, width=50)
        model_entry.grid(row=0, column=2, sticky="ew")

        # Trainingsstart-Button
        start_training_button = ttk.Button(parent, text="Training starten", command=self.start_training)
        start_training_button.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

    # Lyricsgenerator-Tab
    def create_generation_tab(self, parent):
        # Modell für die Generierung auswählen
        model_frame = tk.Frame(parent)
        model_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.generation_model_path = tk.StringVar()
        gen_model_label = tk.Label(model_frame, text="Modell für Generierung:")
        gen_model_label.grid(row=0, column=0, sticky="w")
        gen_model_button = ttk.Button(model_frame, text="Modell auswählen", command=self.select_generation_model)
        gen_model_button.grid(row=0, column=1, sticky="ew")
        gen_model_entry = tk.Entry(model_frame, textvariable=self.generation_model_path, width=50)
        gen_model_entry.grid(row=0, column=2, sticky="ew")

        # Eingabefelder für Titel und Genre
        input_frame = tk.Frame(parent)
        input_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        self.title_label = tk.Label(input_frame, text="Titel:")
        self.title_label.grid(row=0, column=0, sticky="w")
        self.title_entry = tk.Entry(input_frame)
        self.title_entry.grid(row=0, column=1, sticky="ew")

        self.genre_label = tk.Label(input_frame, text="Style/Genre:")
        self.genre_label.grid(row=1, column=0, sticky="w")
        self.genre_entry = tk.Entry(input_frame)
        self.genre_entry.grid(row=1, column=1, sticky="ew")

        input_frame.columnconfigure(1, weight=1)

        # Textfeld für den generierten Prompt
        self.prompt_label = tk.Label(parent, text="Generierter Prompt:")
        self.prompt_label.grid(row=2, column=0, sticky="w", padx=10)

        self.prompt_text = tk.Text(parent, wrap=tk.WORD, height=10)
        self.prompt_text.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")

        # Button zum Kopieren des generierten Lyrics-Felds
        copy_button = ttk.Button(parent, text="Lyrics kopieren", command=self.copy_lyrics_to_clipboard)
        copy_button.grid(row=4, column=0, padx=5, pady=5, sticky="ew")

    # Funktion zum Auswählen eines Trainingsmodells
    def select_model(self):
        model_path = filedialog.askopenfilename(filetypes=[("Modell-Dateien", "*.model"), ("Alle Dateien", "*.*")])
        if model_path:
            self.model_path.set(model_path)

    # Funktion zum Auswählen eines Modells für die Lyricsgenerierung
    def select_generation_model(self):
        gen_model_path = filedialog.askopenfilename(filetypes=[("Modell-Dateien", "*.model"), ("Alle Dateien", "*.*")])
        if gen_model_path:
            self.generation_model_path.set(gen_model_path)

    # Training starten
    def start_training(self):
        model_path = self.model_path.get()
        if model_path:
            # Hier kannst du dein Training starten
            messagebox.showinfo("Training", f"Training mit Modell {model_path} gestartet.")
        else:
            messagebox.showerror("Fehler", "Bitte wähle ein Modell aus!")

    # Lyrics in die Zwischenablage kopieren
    def copy_lyrics_to_clipboard(self):
        lyrics = self.prompt_text.get("1.0", tk.END)
        self.clipboard_clear()
        self.clipboard_append(lyrics)
        messagebox.showinfo("Info", "Lyrics in die Zwischenablage kopiert")

# Anwendung starten
if __name__ == "__main__":
    app = SongGeneratorApp()
    app.mainloop()
