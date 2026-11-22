# Background-Oriented Schlieren mit einer IDS-uEye-Kamera

Bachelorprojekt im Kurs Bildverarbeitung 2.

## Projektziel

Das Projekt untersucht, ob sich aufsteigende warme Luft mit Background-Oriented Schlieren (BOS) sichtbar machen lässt.

Eine Kamera fotografiert ein Punktmuster durch den Untersuchungsbereich. Die Software vergleicht eine Referenzaufnahme mit einer zweiten Aufnahme und schätzt lokale Verschiebungen des Musters.

Die Ergebnisse sind Verschiebungen in Pixeln, keine direkten Messungen von Temperatur oder Luftgeschwindigkeit.

## Aktueller Stand

Am 22.11.2026 geprüft:

- TIFF-/JSON-I/O-Test bestanden.
- Synthetische Schnellvalidierung bestanden.
- Fünf bekannte Verschiebungen mit jeweils 100 % gültigen Vektoren.
- Synthetischer Vektorfehler zwischen etwa 0,010 und 0,045 Pixel RMSE.
- Analyse eines synthetischen Bildpaares erfolgreich.
- Export aller sechs Visualisierungen als PNG erfolgreich.

Die reale Kameraaufnahme und Messungen mit warmer Luft sind noch am Versuchsaufbau zu prüfen.

`scripts/bos_video.py` unterstützt außerdem verlustfreie Bildsequenzen und die anschließende Offline-Verarbeitung zu NPZ-Feldern und einem MP4-Demovideo. Die Serienaufnahme und die erreichbare Bildrate sind noch an der realen Kamera zu prüfen.

## Projektstruktur

```text
configs/base.yaml                 Bildformat für den I/O-Test
scripts/capture.py                Bildpaar mit IDS uEye aufnehmen
scripts/analyze.py                Gespeichertes Bildpaar auswerten
scripts/bos_video.py              Bildsequenz aufnehmen und BOS-Video erzeugen
scripts/validate.py               Synthetische Validierung
scripts/check_io.py               TIFF-/JSON-Speicherung prüfen
scripts/check_correlation.py      Einzelnen synthetischen Fall prüfen
scripts/check_synthetic.py        Synthetische Bilder anzeigen
scripts/visualize.py              Bildpaar und Grauwertdifferenz
scripts/visualize_correaltion.py  Korrelationsfenster, NCC und Subpixel
scripts/visualoze_vectors.py      Vektorfeld über dem Referenzbild
scripts/visualize_quality.py      Qualitätskarten
src/bos/                         Verarbeitung und Datenhaltung
data/raw/                        Kameraaufnahmen
data/checks/                     Synthetische Testdaten
data/processed/                  Berechnete Verschiebungsfelder
results/                         Exportierte Abbildungen und BOS-Videos
logs/                            Ausführungsprotokolle
```

Die Namen `visualize_correaltion.py` und `visualoze_vectors.py` enthalten derzeit Schreibfehler. Die folgenden Befehle verwenden die tatsächlich vorhandenen Dateinamen.

## Umgebung vorbereiten

Alle Befehle im Projektordner ausführen.

Vorhandene Umgebung aktivieren:

```bash
source .venv/bin/activate
export PYTHONPATH="$PWD/src"
```

Falls noch keine Umgebung vorhanden ist:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install numpy scipy Pillow PyYAML matplotlib
export PYTHONPATH="$PWD/src"
```

Für Kameraaufnahmen zusätzlich:

```bash
python -m pip install pyueye
```

Für die reale Kamera werden außerdem passende IDS-uEye-Treiber und native Bibliotheken benötigt. `pyueye` allein ersetzt den Kameratreiber nicht.

Für den MP4-Export mit `bos_video.py process` muss zusätzlich `ffmpeg` mit dem Encoder `libx264` verfügbar sein. Prüfen mit:

```bash
ffmpeg -version
ffmpeg -hide_banner -encoders
```

In der Encoderliste muss `libx264` aufgeführt sein.

Es gibt bisher keine Datei mit festgelegten Paketversionen.

## 1. Speicherung und synthetische Validierung

```bash
python scripts/check_io.py
python scripts/validate.py
```

Erwartete Erfolgsmeldungen:

```text
PASS: All pixels and metadata match.
PASS: Quick validation checks.
```

Der Schnelltest verlangt für seine fünf Verschiebungsfälle:

- mindestens 90 % gültige Vektoren;
- höchstens 0,10 Pixel RMSE.

Außerdem werden strukturlose Bilder, mehrdeutige periodische Muster und ausgewählte Verschiebungen am beziehungsweise außerhalb des Suchbereichs geprüft.

`validate.py` speichert ein synthetisches Bildpaar und gibt den Ordner aus:

```text
Demo pair: .../data/checks/bos_validation_...
```

Umfangreichere Parameterstudie:

```bash
python scripts/validate.py --sweep
```

Mit zusätzlichem Rauschen:

```bash
python scripts/validate.py --sweep --noise-std 0.01
```

`0.01` ist die Standardabweichung des Rauschens auf der Grauwertskala von 0 bis 1. `--noise-std` benötigt `--sweep`.

Die Parameterstudie speichert ihre Ergebnisse als `sweep.csv` im erzeugten Testordner.

## 2. Bildpaar analysieren

Den von `validate.py` ausgegebenen Ordner eintragen:

```bash
PAIR="data/checks/bos_validation_DEIN_ORDNER"
```

`DEIN_ORDNER` durch den tatsächlichen Namen ersetzen.

Anschließend:

```bash
python scripts/analyze.py "$PAIR/reference" "$PAIR/moving" --window 40
```

Die Analyse gibt den gespeicherten Feldpfad aus:

```text
Saved field to .../data/processed/bos_pair_.../field.npz
```

Diesen Pfad für die Visualisierungen eintragen:

```bash
FIELD="data/processed/bos_pair_DEIN_ORDNER/field.npz"
```

Auch hier den Platzhalter durch den tatsächlichen Ordnernamen ersetzen.

Zulässige Fenstergrößen sind `32`, `40` und `52` Pixel. Standard ist `40`. Der Rasterabstand beträgt die halbe Fenstergröße.

## 3. Abbildungen exportieren

Ausgabeordner anlegen:

```bash
OUT="results/demo_01"
mkdir -p "$OUT"
```

### Bildpaar und Grauwertdifferenz

```bash
python scripts/visualize.py "$PAIR/reference" "$PAIR/moving" \
  --output "$OUT/01_bilddifferenz.png"
```

Zeigt Referenz, Messbild und die vorzeichenbehaftete Differenz:

```text
ΔI = Messbild − Referenzbild
```

Die Grauwertdifferenz ist keine Verschiebungs- oder Temperaturmessung.

### Korrelationsfenster und NCC-Karte

```bash
python scripts/visualize_correaltion.py \
  "$PAIR/reference" "$PAIR/moving" \
  --window 40 --cell 1 1 --output-dir "$OUT"
```

Erzeugt:

```text
02_korrelationsfenster.png
03_ncc_karte.png
```

`--cell ROW COL` wählt eine Rasterzelle mit nullbasierten Indizes. Ohne `--cell` wird eine Zelle automatisch ausgewählt.

### Subpixelinterpolation

```bash
python scripts/visualize_correaltion.py \
  "$PAIR/reference" "$PAIR/moving" \
  --window 40 --cell 1 1 --subpixel --output-dir "$OUT"
```

Erzeugt:

```text
04_subpixelinterpolation.png
```

Zeigt die NCC-Stützpunkte und bei gültiger Schätzung die parabolische Subpixelverfeinerung.

### Verschiebungsvektoren

```bash
python scripts/visualoze_vectors.py "$PAIR/reference" "$FIELD" \
  --arrow-scale 20 --stride 1 \
  --output "$OUT/05_vektorfeld.png"
```

- `--arrow-scale 20`: Pfeillängen für die Darstellung um Faktor 20 vergrößern.
- `--stride 1`: alle gültigen Rasterpositionen anzeigen.
- `--stride 2`: jede zweite Rasterzeile und Rasterspalte anzeigen.

Die Messwerte bleiben in Pixeln. Das Feld muss zum verwendeten Referenzbild gehören.

### Qualitätskarten

```bash
python scripts/visualize_quality.py "$FIELD" \
  --output "$OUT/06_qualitaet.png"
```

Zeigt:

- NCC-Maximum;
- Abstand zum nächstbesten getrennten Korrelationsmaximum;
- gültige und verworfene Rasterzellen.

### Interaktiv anzeigen

Für interaktive Fenster `--output …` beziehungsweise `--output-dir …` weglassen.

Beispiel:

```bash
python scripts/visualize.py "$PAIR/reference" "$PAIR/moving"
```

Interaktive Fenster benötigen eine grafische Umgebung. Der PNG-Export funktioniert ohne Anzeigefenster.

Alle PNG-Dateien werden mit 300 dpi gespeichert. Ausgabeordner müssen bereits existieren. Vorhandene Dateien werden nicht überschrieben; für Wiederholungen neue Ordner oder Dateinamen verwenden.

## 4. Kameraaufnahmen

### Aufbau

```text
Kamera → Untersuchungsbereich mit warmer Luft → Punktmuster
```

Vor der Aufnahme:

1. Kamera und Muster stabil befestigen.
2. Gleichmäßige Beleuchtung herstellen.
3. Auf das Punktmuster fokussieren.
4. Fokus, Position und Beleuchtung während des Bildpaares unverändert lassen.
5. Zugluft und Erschütterungen vermeiden.

Das Aufnahmescript besitzt keine Live-Vorschau. Fokus und Bildausschnitt vorher einstellen und andere Kameraanwendungen schließen.

Das Script setzt 2456 × 2054 Pixel und RGB8 voraus. Die Unterstützung dieser Einstellungen muss am Gerät geprüft werden.

### Statisches Bildpaar ohne Heizung

```bash
python scripts/capture.py data/raw/static_01 \
  --exposure-ms 5 --gain 0
```

- Erste Eingabe: Referenz aufnehmen.
- Aufbau unverändert lassen.
- Zweite Eingabe: Vergleichsbild aufnehmen.

Der Ausgabeordner darf noch nicht existieren.

Auswertung:

```bash
PAIR="data/raw/static_01"
python scripts/analyze.py "$PAIR/reference" "$PAIR/moving" --window 40
```

Erwartet werden viele gültige Vektoren und Verschiebungen nahe null. Ein Median nahe null allein genügt nicht; auch lokale Abweichungen und die räumliche Verteilung prüfen.

### Bildpaar mit warmer Luft

```bash
python scripts/capture.py data/raw/heated_01 \
  --exposure-ms 5 --gain 0 --heated
```

1. Bei ausgeschalteter Wärmequelle die Referenz aufnehmen.
2. Wärmequelle einschalten, ohne Kamera oder Muster zu bewegen.
3. Als ersten Versuch etwa 30 bis 60 Sekunden warten.
4. Vergleichsbild aufnehmen.

`--heated` ändert die Eingabeaufforderung und die Kennzeichnung in `camera.json`. Das Script steuert die Wärmequelle nicht.

Auswertung:

```bash
PAIR="data/raw/heated_01"
python scripts/analyze.py "$PAIR/reference" "$PAIR/moving" --window 40
```

Anschließend `FIELD` auf den neu ausgegebenen NPZ-Pfad setzen und die Visualisierungskommandos verwenden.

Für Wiederholungen neue Aufnahmeordner verwenden. Vor einer neuen kalten Referenz den Aufbau ausreichend abkühlen lassen.

## 5. Kurzes BOS-Demovideo

Der Ablauf besteht aus zwei getrennten Schritten: zuerst verlustfreie Bilder
aufnehmen, danach die Korrelation berechnen und ein Video exportieren. Die
Verarbeitung läuft offline und kann länger dauern als die Aufnahme. Das Script
bietet keine Live-Vorschau oder Echtzeit-BOS-Anzeige.

### Aufnahme vorbereiten

- Kamera und Punktmuster stabil befestigen und auf das Muster fokussieren.
- Beleuchtung, Fokus, Belichtung und Verstärkung für Referenz und Sequenz unverändert lassen.
- Mit 5 ms Belichtung und Verstärkung 0 beginnen; bei zu dunklem Bild zunächst die Beleuchtung verbessern. Die Werte müssen am Aufbau angepasst werden.
- Ausreichend freien Speicher vorsehen: Bei 2456 × 2054 Pixeln und RGB8 benötigt ein Bild etwa 15 MB. 100 Bilder entsprechen etwa 1,5 GB, zusätzlich zur Referenz und den Auswertungsdateien.
- Andere Kameraanwendungen schließen. Die beiden Ausgabeordner der folgenden Befehle dürfen noch nicht existieren.

### Kalte Referenz und warme Sequenz aufnehmen

```bash
python scripts/bos_video.py record data/raw/video_01 \
  --seconds 10 --fps 10 --exposure-ms 5 --gain 0
```

1. Wärmequelle ausgeschaltet lassen und Enter für die kalte Referenz drücken.
2. Wärmequelle einschalten, ohne Kamera oder Muster zu berühren.
3. Wenn die warme Luft im Untersuchungsbereich sichtbar gemacht werden soll, Enter für die Serienaufnahme drücken.
4. Das Script nimmt ungefähr 10 Sekunden lang Einzelbilder auf und speichert sie direkt als unkomprimierte TIFF-Dateien mit JSON-Metadaten.

`--fps 10` ist eine Zielrate für wiederholte Einzelaufnahmen, keine garantierte
Kamera-Framerate. Aufnahme, Bildübertragung und Dateispeicherung begrenzen den
Durchsatz. Die gemessene mittlere Bildrate wird am Ende ausgegeben. Wird die
Zielrate deutlich unterschritten, erscheint eine Warnung. Bei Bedarf die Zielrate
reduzieren; die Rohbilder werden dadurch nicht stärker komprimiert.

`sequence.json` enthält die tatsächlichen Zeitabstände aus einer monotonen
Rechneruhr unmittelbar nach jeder Aufnahme. Die UTC-Zeitstempel in `frame.json`
stammen ebenfalls vom Host, nicht von der Kamera-Hardware. Bei einem Abbruch
bleiben vorhandene Bilder erhalten; eine als unvollständig markierte Sequenz
wird von `process` abgelehnt.

### Sequenz auswerten und MP4 erzeugen

```bash
python scripts/bos_video.py process \
  data/raw/video_01 results/video_01 \
  --window 40 --component u --limit-px 1 --fps 10
```

Jeder warme Frame wird mit derselben kalten Referenz korreliert. Die Auswertung
vergleicht nicht zwei aufeinanderfolgende warme Frames. Für jeden aufgenommenen
Frame entsteht eine NPZ-Datei mit Verschiebungen, Qualitätswerten,
Gültigkeitsmaske und `time_s` als Aufnahmezeit relativ zum Sequenzstart.

Das Video zeigt links das Rohbild und rechts das berechnete BOS-Raster in
Graustufen. Ungültige Rasterzellen werden maskiert.

| Option | Bedeutung |
|---|---|
| `--window 40` | Korrelationsfenster in Pixeln; erlaubt: 32, 40, 52. Rasterabstand: halbe Fenstergröße. |
| `--component u` | Horizontale Verschiebung; `v` wählt die vertikale Verschiebung. |
| `--limit-px 1` | Feste Grauwertskala von −1 bis +1 Pixel für das gesamte Video. |
| `--fps 10` | Bildrate des exportierten Videos; unabhängig von der Aufnahme-Zielrate. |

Die feste Skala verhindert, dass jeder Frame automatisch einen anderen Kontrast
erhält. Werte außerhalb der Skala werden nur in der Darstellung gesättigt; die
NPZ-Messwerte bleiben erhalten. Das Bild zeigt Muster-Verschiebungen, keine
Temperatur oder Luftgeschwindigkeit. Die räumliche Auflösung der BOS-Darstellung
entspricht dem Korrelationsraster, nicht der vollen Kameraauflösung.

Der Export berücksichtigt die aufgezeichneten Zeiten und hält das letzte Bild
bis zum nächsten Messzeitpunkt. Vor dem ersten Messzeitpunkt wird das erste Bild
gezeigt. Die Videolänge wird auf ganze Ausgabe-Frames aufgerundet. Eine höhere
Ausgabe-FPS erzeugt keine zusätzlichen Messungen oder interpolierten Strömungen.

Die MP4-Kompression betrifft nur das Präsentationsvideo. Rohbilder und
Korrelationsrechnung verwenden die verlustfreien TIFF-Dateien.

### Dateien der Videomessung

```text
data/raw/video_01/
├── reference/
│   ├── frame.tif
│   └── frame.json
├── frames/
│   ├── 000000/
│   │   ├── frame.tif
│   │   └── frame.json
│   └── ...
└── sequence.json

results/video_01/
├── fields/
│   ├── 000000.npz
│   └── ...
├── processing.json
└── bos.mp4
```

`sequence.json` dokumentiert die Kameraeinstellungen, Aufnahmezeiten und den
Abschlussstatus. `processing.json` dokumentiert Referenzpfad, Fenstergröße,
Rasterabstand und Darstellungsparameter. Die Video-Kommandos schreiben ihren
Fortschritt ins Terminal; sie erzeugen keine eigene Logdatei.

Für Wiederholungen neue Namen wie `video_02` verwenden. Vor einer neuen kalten
Referenz den Aufbau ausreichend abkühlen lassen.

## Ausgabedaten

### Rohdaten

```text
data/raw/static_01/
├── camera.json
├── reference/
│   ├── frame.tif
│   └── frame.json
└── moving/
    ├── frame.tif
    └── frame.json
```

- `frame.tif`: unkomprimiertes RGB8-Bild.
- `frame.json`: Bildformat, Quelle und Zeitstempel.
- `camera.json`: Aufnahmeart und Kameraeinstellungen.

Die Zeitstempel stammen von der Rechneruhr, nicht von Kamera-Hardwarezeitstempeln.

### Verschiebungsfeld

```text
data/processed/bos_pair_.../field.npz
```

| Feld | Bedeutung |
|---|---|
| `x_px`, `y_px` | Fenstermittelpunkte im Referenzbild |
| `u_px` | Horizontale Verschiebung; positiv nach rechts |
| `v_px` | Vertikale Verschiebung; positiv nach unten |
| `magnitude_px` | Länge des Verschiebungsvektors |
| `ncc_peak` | Bestes normiertes Korrelationsmaximum |
| `peak_margin` | Abstand zum nächstbesten getrennten Maximum |
| `valid` | Gültigkeitsmaske |

Alle Koordinaten und Verschiebungen sind in Pixeln angegeben.

Ungültige Verschiebungen sind `NaN` und dürfen nicht als Nullbewegung interpretiert werden.

Der Standard-Suchradius beträgt 4 Pixel. Treffer genau am Suchrand werden verworfen.

### Protokolle

```text
logs/io_check.log
logs/validate.log
logs/capture.log
logs/analyze.log
```

Die Dateien werden bei weiteren Läufen ergänzt. Beim Vergleichen auf Zeitstempel und die ausgegebenen Datenpfade achten.

## Hilfe zu den Befehlen

```bash
python scripts/capture.py --help
python scripts/bos_video.py record --help
python scripts/bos_video.py process --help
python scripts/analyze.py --help
python scripts/validate.py --help
python scripts/visualize.py --help
python scripts/visualize_correaltion.py --help
python scripts/visualoze_vectors.py --help
python scripts/visualize_quality.py --help
```

## Bekannte Einschränkungen

- Die Hardwarefunktion muss noch am realen Gerät bestätigt werden.
- Eine vollständige synthetische Parameterstudie wurde hier nicht ausgeführt.
- Es gibt keine Umrechnung in Temperatur, Dichte oder Luftgeschwindigkeit.
- BOS-Videos werden offline erzeugt; Echtzeitverarbeitung und Live-Vorschau sind nicht implementiert.
- Die Serienaufnahme und die erreichbare Aufnahme-FPS müssen an der realen Kamera geprüft werden.
- `channel_order` ist im aktuellen Code `"RGB"`. Ältere Metadaten mit `" RGB"` und führendem Leerzeichen werden abgelehnt. Für synthetische Versuche mit `validate.py` ein neues Bildpaar erzeugen. Vor einer Migration vorhandener Messdaten eine Sicherung anlegen.