import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import json
import random
from data_preparation import prepare_data
from constants import *
import threading
from datasets import load_dataset
from training import *
from generate import *
from transformers import AutoModelForCausalLM, MODEL_MAPPING
import requests


class SongGeneratorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Song KI Steuerzentrale")
        self.create_widgets()
        self.load_random_json_file()  # Lädt eine zufällige JSON-Datei beim Start
        training_manager = TrainingManager(log_training_message=None, root=self)

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
        # Rahmen für die drei Buttons nebeneinander
        button_frame = tk.Frame(parent)
        button_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        button_frame.columnconfigure(0, weight=1)  # Erste Spalte (33%)
        button_frame.columnconfigure(1, weight=1)  # Zweite Spalte (33%)
        button_frame.columnconfigure(2, weight=1)  # Dritte Spalte (33%)

        # Buttons: Zufällige Datei, Manuelle Datei und Daten vorbereiten
        reload_random_button = ttk.Button(button_frame, text="Zufällige Datei neu laden", command=self.load_random_json_file)
        reload_random_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        manual_select_button = ttk.Button(button_frame, text="Manuelle Datei auswählen", command=self.select_manual_json_file)
        manual_select_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        start_button = ttk.Button(button_frame, text="Daten vorbereiten", command=self.start_data_preparation)
        start_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        # JSON Key Felder für Trainingsdaten
        self.json_keys_frame = tk.Frame(parent)
        self.json_keys_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        self.create_key_selection_fields(self.json_keys_frame)

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
        self.skipped_lyrics_label = ttk.Label(progress_frame, text="keine Lyrics oder Metatags: 0")
        self.skipped_lyrics_label.pack()

        self.skipped_lyrics_bar = ttk.Progressbar(progress_frame, orient='horizontal', mode='determinate')
        self.skipped_lyrics_bar.pack(fill=tk.X, pady=5)

        # Ausgabefeld für Logs und Errors
        prep_log_frame = tk.Frame(parent)
        prep_log_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        self.prep_log_text = tk.Text(prep_log_frame, height=5, wrap=tk.WORD)
        self.prep_log_text.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        prep_log_frame.columnconfigure(0, weight=1)
        prep_log_frame.rowconfigure(0, weight=1)

    # Trainings-Tab
    def create_training_tab(self, parent):
        # Training settings frame
        settings_frame = ttk.LabelFrame(parent, text="Training Settings")
        settings_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        settings_frame.columnconfigure(1, weight=1)  # This makes the second column expandable

        # Model selection
        ttk.Label(settings_frame, text="Model:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.training_model_var = tk.StringVar()
        self.training_model_dropdown = ttk.Combobox(settings_frame, textvariable=self.training_model_var, state="readonly")
        self.training_model_dropdown.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.training_model_dropdown.bind("<<ComboboxSelected>>", self.on_model_select)
        self.update_model_list()

        # Create input fields for all training settings
        self.epochs_var = tk.IntVar(value=DEFAULT_EPOCHS)
        self.lr_var = tk.DoubleVar(value=DEFAULT_LEARNING_RATE)
        self.batch_size_var = tk.IntVar(value=DEFAULT_BATCH_SIZE)
        self.max_length_var = tk.IntVar(value=DEFAULT_MAX_LENGTH)
        self.warmup_steps_var = tk.IntVar(value=DEFAULT_WARMUP_STEPS)
        self.weight_decay_var = tk.DoubleVar(value=DEFAULT_WEIGHT_DECAY)
        self.grad_accum_steps_var = tk.IntVar(value=DEFAULT_GRADIENT_ACCUMULATION_STEPS)

        settings = [
            ("Epochs", self.epochs_var, DEFAULT_EPOCHS),
            ("Learning Rate", self.lr_var, DEFAULT_LEARNING_RATE),
            ("Batch Size", self.batch_size_var, DEFAULT_BATCH_SIZE),
            ("Max Length", self.max_length_var, DEFAULT_MAX_LENGTH),
            ("Warmup Steps", self.warmup_steps_var, DEFAULT_WARMUP_STEPS),
            ("Weight Decay", self.weight_decay_var, DEFAULT_WEIGHT_DECAY),
            ("Gradient Accumulation Steps", self.grad_accum_steps_var, DEFAULT_GRADIENT_ACCUMULATION_STEPS)
        ]

        for i, (label, var, default) in enumerate(settings, start=1):
            ttk.Label(settings_frame, text=label).grid(row=i, column=0, sticky="w", padx=5, pady=2)
            var.set(default)
            ttk.Entry(settings_frame, textvariable=var).grid(row=i, column=1, sticky="ew", padx=5, pady=2)

        parent.columnconfigure(0, weight=1)

        #Training control frame
        control_frame = ttk.LabelFrame(parent, text="Training Control")
        control_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        self.start_button = ttk.Button(control_frame, text="Start Training", command=self.start_training)
        self.start_button.grid(row=0, column=0, padx=5, pady=5)

        self.stop_button = ttk.Button(control_frame, text="Stop Training", command=self.stop_training, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=5, pady=5)

        # Progress frame
        progress_frame = ttk.LabelFrame(parent, text="Training Progress")
        progress_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        self.status_label.grid(row=1, column=0, sticky="w", padx=5, pady=5)

        # Resource usage frame
        resource_frame = ttk.LabelFrame(parent, text="Resource Usage")
        resource_frame.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")

        self.resource_var = tk.StringVar()
        self.resource_label = ttk.Label(resource_frame, textvariable=self.resource_var)
        self.resource_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)

        # Analysis frame
        analysis_frame = ttk.LabelFrame(parent, text="Training Analysis")
        analysis_frame.grid(row=0, column=1, rowspan=4, padx=10, pady=10, sticky="nsew")

        self.loss_plot = ttk.Label(analysis_frame)
        self.loss_plot.grid(row=0, column=0, padx=5, pady=5)

        self.lr_plot = ttk.Label(analysis_frame)
        self.lr_plot.grid(row=1, column=0, padx=5, pady=5)

        self.gradient_plot = ttk.Label(analysis_frame)
        self.gradient_plot.grid(row=2, column=0, padx=5, pady=5)

        # Log frame
        log_frame = ttk.LabelFrame(parent, text="Training Log")
        log_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

        self.log_text = tk.Text(log_frame, height=10, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky="nsew")

        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        log_scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=log_scrollbar.set)

        # Configure grid weights
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        for i in range(5):
            parent.rowconfigure(i, weight=1)

        # Bind the log function
        log_training_message(self.log_training_message)

    def get_available_models(self):
        local_models =          ['---local----------']
        transformer_models =    ['---transformers---']
        hf_models =             ['---huggingface----']
        
        # Fetch local models
        models_dir = os.path.join(os.getcwd(), 'models')
        if os.path.exists(models_dir):
            local_models.extend([d for d in os.listdir(models_dir) if os.path.isdir(os.path.join(models_dir, d))])
        
        # Fetch Hugging Face models
        try:
            response = requests.get("https://huggingface.co/api/models?filter=text-generation")
            if response.status_code == 200:
                hf_models.extend([model['id'] for model in response.json()[:200]])  # Limit to top 200 models
        except Exception as e:
            print(f"Error fetching Hugging Face models: {e}")
        
         # Dynamically load transformer models
        transformer_models.extend(MODEL_MAPPING._model_mapping.keys())
        
        return local_models + hf_models + transformer_models

    def load_or_download_model(self, model_name):
        models_dir = os.path.join(os.getcwd(), 'models')
        model_path = os.path.join(models_dir, model_name)
        
        try:
            # Versuche zuerst, das Modell direkt aus der Transformers-Bibliothek zu laden
            model = AutoModelForCausalLM.from_pretrained(model_name)
            print(f"Modell {model_name} erfolgreich aus der Transformers-Bibliothek geladen.")
            return model
        except:
            # Wenn das nicht klappt, versuche es aus dem lokalen Verzeichnis zu laden oder herunterzuladen
            if os.path.exists(model_path):
                print(f"Lade Modell {model_name} aus lokalem Verzeichnis.")
                return AutoModelForCausalLM.from_pretrained(model_path)
            else:
                print(f"Lade Modell {model_name} herunter und speichere es lokal.")
                model = AutoModelForCausalLM.from_pretrained(model_name)
                model.save_pretrained(model_path)
                return model

    def start_training(self):
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")

        model_name = self.training_model_var.get().strip()
    
        print(f"Ausgewähltes Modell: {model_name}")  # Debugging-Ausgabe

        if model_name in ['---local----------', '---transformers---', '---huggingface----']:
            messagebox.showerror("Error", "Please select a valid model")
            return
        
        model = self.load_or_download_model(model_name)
        
        hyperparams = {
            "epochs": self.epochs_var.get(),
            "learning_rate": self.lr_var.get(),
            "batch_size": self.batch_size_var.get(),
            "max_length": self.max_length_var.get(),
            "warmup_steps": self.warmup_steps_var.get(),
            "weight_decay": self.weight_decay_var.get(),
            "gradient_accumulation_steps": self.grad_accum_steps_var.get()
        }
        
        training_manager.start_training(
            model,
            self.log_text,
            self.progress_var,
            self.status_var,
            self.resource_var,
            self.loss_plot,
            **hyperparams
        )

    def stop_training(self):
        training_manager.stop_training()
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")

    def on_model_select(self, event):
        if self.training_model_dropdown.current() == -1:
            self.training_model_dropdown.current(0)  # Select the first item if none is selected
        selected_model = self.training_model_dropdown.get()
        print(f"Neu ausgewähltes Modell: {selected_model}")
        self.training_model_var.set(selected_model)
        
    def update_model_list(self):
        models = self.get_available_models()
        self.training_model_dropdown['values'] = models
        if models:
            self.training_model_dropdown.set(models[0])
        print("Selected model:", self.training_model_var.get())  # Debug output

    def update_loss_plot(self, image_path):
        img = tk.PhotoImage(file=image_path)
        self.loss_plot.config(image=img)
        self.loss_plot.image = img  # Halte eine Referenz
    
    def create_loss_plot(self):
        self.loss_plot = tk.Label(self.training_frame)
        self.loss_plot.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
    # Lyricsgenerator-Tab
    def create_generation_tab(self, parent):
        generation_frame = tk.Frame(parent)
        generation_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        # Model selection dropdown
        tk.Label(generation_frame, text="Model:").grid(row=0, column=0, sticky="w")
        self.model_var = tk.StringVar()
        self.model_dropdown = ttk.Combobox(generation_frame, textvariable=self.model_var)
        self.load_model_paths()
        self.model_dropdown.grid(row=0, column=1, sticky="ew")

        # Song title input
        tk.Label(generation_frame, text="Song Title:").grid(row=1, column=0, sticky="w")
        self.title_entry = tk.Entry(generation_frame)
        self.title_entry.grid(row=1, column=1, sticky="ew")

        # Style/Metatags input
        tk.Label(generation_frame, text="Style/Metatags:").grid(row=2, column=0, sticky="w")
        self.style_entry = tk.Entry(generation_frame)
        self.style_entry.grid(row=2, column=1, sticky="ew")

        # Prompt input
        tk.Label(generation_frame, text="Prompt:").grid(row=3, column=0, sticky="w")
        self.prompt_entry = tk.Text(generation_frame, height=3)
        self.prompt_entry.grid(row=3, column=1, sticky="ew")

        # Generate button
        generate_button = ttk.Button(generation_frame, text="Generate Lyrics", command=lambda: start_lyrics_generation(self))
        generate_button.grid(row=4, column=0, columnspan=2, pady=10, sticky="ew")

        # Log output
        self.log_text = tk.Text(generation_frame, height=10, wrap=tk.WORD)
        self.log_text.grid(row=5, column=0, columnspan=2, sticky="nsew")

        # Configure grid
        generation_frame.columnconfigure(1, weight=1)
        generation_frame.rowconfigure(5, weight=1)

    def load_model_paths(self):
        model_folder = "results"
        if os.path.exists(model_folder):
            model_dirs = [d for d in os.listdir(model_folder) if os.path.isdir(os.path.join(model_folder, d))]
            self.model_dropdown['values'] = model_dirs
        else:
            self.model_dropdown['values'] = []

    def generate_lyrics(self):
        model = self.model_var.get()
        title = self.title_entry.get()
        style = self.style_entry.get()
        prompt = self.prompt_entry.get("1.0", tk.END).strip()

        self.log_text.delete("1.0", tk.END)
        self.log_text.insert(tk.END, f"Generating lyrics with:\nModel: {model}\nTitle: {title}\nStyle: {style}\nPrompt: {prompt}\n\n")
        
        # Here you would call your actual lyrics generation function
        # For now, we'll just log a placeholder message
        self.log_text.insert(tk.END, "Lyrics generation not implemented yet.")

    def log_message(self, message):
        """Fügt eine Log-Nachricht in das Log-Textfeld ein."""
        self.log(self.log_text, message)

    def log(self, log_text_widget, message):
        log_text_widget.insert(tk.END, f"{message}\n")
        log_text_widget.see(tk.END)

    def log_training_message(self, log_text_widget, message):
        log_text_widget.insert(tk.END, f"{message}\n")
        log_text_widget.see(tk.END)

    def update_prompt_text(self, lyrics):
        """Aktualisiert das Prompt-Textfeld mit den generierten Lyrics."""
        self.prompt_text.after(0, self.prompt_text.delete, "1.0", tk.END)  # Löscht alten Text
        self.prompt_text.after(0, self.prompt_text.insert, tk.END, lyrics)  # Fügt neue Lyrics ein
        self.prompt_text.after(0, self.prompt_text.yview_moveto, 1)  # Scrollt automatisch nach unten
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
            self.progress_label.config(text=f"Neue Songs {processed} von {total}")

            # Fortschritt der übersprungenen Songs (bereits vorhanden)
            self.skipped_existing_bar['value'] = int((skipped_existing / total) * 100)
            self.skipped_existing_label.config(text=f"bereits vorhanden: {skipped_existing}")

            # Fortschritt der übersprungenen Songs (keine Lyrics)
            self.skipped_lyrics_bar['value'] = int((skipped_lyrics / total) * 100)
            self.skipped_lyrics_label.config(text=f"keine Lyrics oder Metatags: {skipped_lyrics}")

            self.update_idletasks()

        if title_key and lyrics_key and styles_key and metatags_key and (language_key or detect_language):
            try:
                # Wrapper für die Log-Nachrichten der Datenvorbereitung
                def log_preparation_message(message):
                    self.log(self.prep_log_text, message)

                processed, total = prepare_data(
                    song_folder, title_key, lyrics_key, styles_key, metatags_key, language_key, detect_language, update_progress, log_preparation_message
                )
                if total > 0:
                    log_preparation_message(f"Verarbeitung abgeschlossen. {processed} von {total} Songs bearbeitet.")
                else:
                    log_preparation_message("Keine Songs zum Bearbeiten gefunden.")
            except Exception as e:
                log_preparation_message(f"Fehler bei der Datenvorbereitung: {e}")
        else:
            self.log(self.prep_log_text, "Fehler: Bitte alle Felder ausfüllen.")
    # Daten aus einer zufälligen JSON-Datei laden und die Keys anzeigen
    def load_random_json_file(self):
        self.log(self.prep_log_text, f"Lade Songs aus dem Verzeichnis: {SONGS_DIR}")
        folder = SONGS_DIR  # Verwende den Ordner aus constants.py
        if os.path.isdir(folder):
            json_files = [f for f in os.listdir(folder) if f.endswith('.json')]
            if json_files:
                random_file = random.choice(json_files)
                file_path = os.path.join(folder, random_file)
                self.log(self.prep_log_text, f"Zufällige Datei geladen: {random_file}")
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    self.update_key_selection(data)
            else:
                self.log(self.prep_log_text, "Keine JSON-Dateien im Ordner gefunden.")
        else:
            self.log(self.prep_log_text, f"Ordner {folder} nicht gefunden.")

    def select_manual_json_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON-Dateien", "*.json"), ("Alle Dateien", "*.*")])
        if file_path:
            self.log(self.prep_log_text, f"Manuelle Datei ausgewählt: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                self.update_key_selection(data)
        else:
            self.log(self.prep_log_text, "Keine Datei ausgewählt.")

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

            # Sprach-Key überprüfen
            language_selected = self.auto_select_key(self.language_key, keys, EXPECTED_KEYS["language"])

            # Wenn kein Sprach-Tag gefunden wurde, aktiviere automatische Spracherkennung
            if not language_selected:
                self.detect_language_var.set(1)  # Setze den Haken bei "Sprache automatisch erkennen"
                self.language_key.set('')  # Entferne den gewählten Wert, falls vorhanden
                self.language_key.config(state='disabled')
            else:
                self.detect_language_var.set(0)  # Entferne den Haken bei "Sprache automatisch erkennen"
                self.language_key.config(state='normal')

            self.log(self.prep_log_text, "Keys erfolgreich geladen und (wenn möglich) vorausgewählt.")
        except Exception as e:
            self.log(self.prep_log_text, f"Fehler beim Laden der Keys: {e}")

    def auto_select_key(self, combobox, keys, expected_keywords):
        """Wählt den ersten passenden Key aus der Liste der erwarteten Keys aus"""
        for key in keys:
            for expected in expected_keywords:
                if expected.lower() in key.lower():
                    combobox.set(key)
                    return True  # Sobald wir einen Treffer finden, hören wir auf
        return False  # Kein Treffer gefunden

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
