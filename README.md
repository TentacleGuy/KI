# KI Song Scraper & Generator

Dieses Projekt dient zum Scrapen von Songdaten und zur Generierung von Lyrics mithilfe einer KI. Es enthält Tools zur Datenvorbereitung, zum Modelltraining und zur Lyricsgenerierung auf der Grundlage gesammelter Song- und Playlist-Daten.

## Inhaltsverzeichnis

- [Überblick](#überblick)
- [Funktionen](#funktionen)
- [Installation](#installation)
- [Verwendung](#verwendung)
- [Projektstruktur](#projektstruktur)
- [Contributing](#contributing)
- [Lizenz](#lizenz)

## Überblick

Dieses Projekt bietet eine vollständige Pipeline, um Songdaten von Webseiten zu scrapen, die Daten zu verarbeiten und eine KI zu trainieren, die neue Lyrics generieren kann. Das Projekt nutzt Selenium für das Webscraping und TensorFlow für die KI-Modelle.

## Funktionen

- **Scraping**: Playlist- und Songinformationen von Musikwebseiten sammeln.
- **Datenvorbereitung**: Die gescrapten Daten in einem strukturierten Format für das Training einer KI bereitstellen.
- **Modelltraining**: Ein KI-Modell trainieren, das in der Lage ist, neue Songtexte auf Basis der gesammelten Daten zu generieren.
- **Lyricsgenerator**: Generiere neue Songtexte basierend auf vorgegebenen Genres und Stilen.

## Installation

### Voraussetzungen

- Python 3.10 oder höher
- [Selenium WebDriver](https://www.selenium.dev/documentation/webdriver/)
- [TensorFlow](https://www.tensorflow.org/)
- [ChromeDriver](https://sites.google.com/a/chromium.org/chromedriver/downloads)
- Die Python-Pakete in der Datei `requirements.txt`

### Schritte

1. Klone das Repository:
    ```bash
    git clone https://github.com/TentacleGuy/KI.git
    ```

2. Wechsle ins Projektverzeichnis:
    ```bash
    cd KI
    #virtuelle umgebung erstellen und aktivieren
    python -m venv 
    .\.venv\Scripts\activatenenv 

    ```

3. Installiere die benötigten Abhängigkeiten:
    ```bash
    pip install -r requirements.txt
    ```

4. Stelle sicher, dass der `ChromeDriver` installiert und der Pfad in den Umgebungsvariablen korrekt gesetzt ist.

## Verwendung

### 1. Scrapen von Playlists

Starte das Scraping von Playlists mit dem folgenden Befehl:

```bash
python Sunoscraper.py
