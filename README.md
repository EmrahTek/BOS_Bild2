# Background-Oriented Schlieren mit einer IDS-uEye-Kamera

Bachelorprojekt im Kurs Bildverarbeitung 2.

## Projektziel

Das Projekt untersucht, ob sich aufsteigende warme Luft mit Background-Oriented Schlieren (BOS) sichtbar machen lässt.

Eine Kamera fotografiert ein A3-Punktmuster durch den Untersuchungsbereich. Warme Luft verändert die Lichtausbreitung. Dadurch erscheinen Teile des Musters gegenüber einer Referenzaufnahme leicht verschoben.

Die Software vergleicht kleine Bildbereiche und schätzt deren Verschiebung in Pixeln. Diese Verschiebungen sind keine direkten Messungen der Luftgeschwindigkeit oder Temperatur.

Zuerst wird der Aufbau mit zwei Bildern ohne eingeschaltete Wärmequelle geprüft. Danach folgt ein Bildpaar aus einer kalten Referenzaufnahme und einer Aufnahme mit warmer Luft.

## Aktueller Prüfstand

Durch vorhandene Protokolle belegt:

- Bild-I/O-Test vom 06.11.2026 bestanden: Pixel und Metadaten stimmen nach dem Speichern und Einlesen überein.
- Synthetischer Schnelltest vom 15.11.2026 bestanden: fünf bekannte Verschiebungen mit jeweils 100 % gültigen Vektoren.
- Die synthetischen Vektorfehler lagen dabei zwischen etwa 0,010 und 0,045 Pixeln.
- Der Schnelltest prüft außerdem die Ablehnung strukturloser Bilder, mehrdeutiger periodischer Muster und ausgewählter Verschiebungen am beziehungsweise außerhalb des Suchbereichs.

Noch nicht durch diese Protokolle belegt:

- Aufnahme mit der realen Kamera.
- Statischer Kameratest ohne Heizung.
- Messung mit warmer Luft.
- Vollständige synthetische Parameterstudie.
- Grafische Darstellung eines realen Verschiebungsfeldes.

Die Analyse speichert bisher Messfelder als NPZ-Dateien. Sie erzeugt noch keine fertigen Wärmebilder, Pfeildiagramme oder Videos.

## Projektstruktur

```text
configs/base.yaml          Bildformat für den I/O-Test
scripts/capture.py         Bildpaar mit IDS uEye aufnehmen
scripts/analyze.py         Gespeichertes Bildpaar auswerten
scripts/validate.py        Synthetische Validierung
scripts/check_io.py        TIFF/JSON-Speicherung prüfen
scripts/check_correlation.py
                           Einzelnen synthetischen Verschiebungsfall ausgeben
scripts/check_synthetic.py Synthetische Bilder anzeigen
src/bos/io.py              Bilddateien und Metadaten
src/bos/synthetic.py       Synthetische Bildpaare
src/bos/correlation.py     Lokale Verschiebungsschätzung
src/bos/metrics.py         Fehler gegenüber bekannten Verschiebungen
```

## Physischer Aufbau

```text
Kamera  →  Untersuchungsbereich mit warmer Luft  →  A3-Punktmuster
```

Die Kamera blickt auf das Muster. Die Wärmequelle steht unterhalb des sichtbaren Untersuchungsbereichs, sodass die warme Luft durch die Sichtlinie zwischen Kamera und Muster aufsteigen kann.

### Vorgeschlagene Startwerte

Diese Werte dienen zum ersten Aufbau und müssen praktisch angepasst werden:

| Größe | Startwert |
|---|---|
| Kamera–Muster-Abstand | etwa 1,5 bis 2 m |
| Abstand der warmen Luft vor dem Muster | etwa 20 bis 40 cm |
| Hintergrund | mattes A3-Blatt mit zufälligen schwarzen Punkten |
| Belichtung | zunächst 5 ms |
| Verstärkung | zunächst 0 |
| Korrelationsfenster | zunächst 40 × 40 Pixel |

Ob das A3-Blatt bei diesem Abstand passend abgebildet wird, hängt vom Objektiv ab. Abstand und Bildausschnitt so einstellen, dass das Muster einen großen Teil des Bildes füllt.

Die Punkte sollen im Kamerabild mehrere Pixel groß und klar erkennbar sein. Als erster Zielbereich können etwa 3 bis 5 Pixel Punktdurchmesser dienen. Entscheidend ist die Abbildung im Kamerabild, nicht allein die gedruckte Punktgröße.

### Vorbereitung

1. Kamera und Muster stabil befestigen.
2. Gleichmäßige Beleuchtung ohne starke Reflexionen herstellen.
3. Auf das Punktmuster fokussieren.
4. Fokus, Blende, Position und Beleuchtung während eines Bildpaares unverändert lassen.
5. Zugluft und Erschütterungen möglichst vermeiden.
6. Eine kleine, standsichere Wärmequelle mit Abstand zum Papier verwenden.

Eine Wärmequelle ohne Lüfter erleichtert den ersten Versuch, weil weniger mechanische Bewegung und zusätzliche Luftströmung entstehen.

Das Aufnahmescript besitzt keine Live-Vorschau. Bildausschnitt und Fokus daher vorab mit einer geeigneten Kameraansicht einstellen. Eine andere Kameraanwendung vor dem Start des Scripts schließen.

## Linux-Umgebung

Alle folgenden Befehle werden im Projektordner ausgeführt.

### Vorhandene virtuelle Umgebung verwenden

```bash
source .venv/bin/activate
export PYTHONPATH="$PWD/src"
```

Der Python-Pfad ist erforderlich, damit die Scripte das Paket `bos` unter `src/` finden.

### Neue Umgebung anlegen, falls erforderlich

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install numpy scipy Pillow PyYAML matplotlib pyueye
export PYTHONPATH="$PWD/src"
```

Dies sind die aus den Imports abgeleiteten Python-Abhängigkeiten. Im Projekt ist bisher keine Datei mit festgelegten Paketversionen vorhanden.

Für die reale Kamera wird zusätzlich eine zur Kamera passende IDS-uEye-Treiberinstallation mit nativen Bibliotheken benötigt. Das Python-Paket `pyueye` allein ersetzt den Kameratreiber nicht. Die konkrete Treibereinrichtung wurde hier noch nicht geprüft.

Das Aufnahmescript setzt 2456 × 2054 Pixel und RGB8 voraus. Ob die verwendete Kamera diese Einstellungen unterstützt, muss am Gerät geprüft werden.

## Synthetische Validierung

Zunächst die Bildspeicherung prüfen:

```bash
python scripts/check_io.py
```

Erwartete Erfolgsmeldung:

```text
PASS: All pixels and metadata match.
```

Danach die Verschiebungsschätzung prüfen:

```bash
python scripts/validate.py
```

Erwartete Erfolgsmeldung:

```text
PASS: Quick validation checks.
```

Der Schnelltest verlangt für seine fünf Verschiebungsfälle mindestens 90 % gültige Vektoren und höchstens 0,10 Pixel RMSE.

RMSE beschreibt hier den quadratischen Mittelwert des zweidimensionalen Verschiebungsfehlers mit anschließender Wurzel. Die Einheit ist Pixel. Kleine Werte bedeuten, dass die geschätzten Verschiebungen nahe an den bekannten Vorgaben liegen.

Zusätzlich wird ein synthetisches Bildpaar unter `data/checks/bos_validation_…/` gespeichert. Der vollständige Ordnername erscheint im Terminal.

Eine umfangreichere Studie starten:

```bash
python scripts/validate.py --sweep
```

Optional mit zusätzlichem Bildrauschen:

```bash
python scripts/validate.py --sweep --noise-std 0.01
```

`0.01` bezeichnet die Standardabweichung des hinzugefügten Rauschens auf der Grauwertskala von 0 bis 1.

Die Parameterstudie vergleicht mehrere Verschiebungen, Zufallsinitialisierungen, zwei Erzeugungsverfahren und Fenstergrößen von 32, 40 und 52 Pixeln. Ihre Ergebnisse stehen in `sweep.csv`.

## Versuch 1: Zwei Aufnahmen ohne Heizung

Dieser Versuch bestimmt die Grundabweichung des Aufbaus.

1. Wärmequelle ausgeschaltet und Aufbau möglichst im thermischen Gleichgewicht lassen.
2. Kamera, Muster und Beleuchtung vorbereiten.
3. Aufnahme starten:

```bash
python scripts/capture.py data/raw/static_01 --exposure-ms 5 --gain 0
```

4. Bei der ersten Aufforderung Enter drücken: Referenzaufnahme.
5. Den Aufbau unverändert lassen, beispielsweise 5 bis 10 Sekunden warten.
6. Bei der zweiten Aufforderung Enter drücken: Vergleichsaufnahme.

Der Ausgabeordner darf vor dem Start noch nicht existieren. Für Wiederholungen neue Namen wie `static_02` verwenden.

Anschließend auswerten:

```bash
python scripts/analyze.py data/raw/static_01/reference data/raw/static_01/moving --window 40
```

Erwartung:

- Viele gültige Vektoren.
- Median von u und v jeweils nahe 0 Pixel.
- Kleine lokale Verschiebungen durch Bildrauschen und verbleibende Instabilität sind möglich.

Es gibt bisher keinen am realen Aufbau bestätigten Grenzwert für „nahe 0“. Deshalb mehrere statische Bildpaare aufnehmen und die Ergebnisse vergleichen.

Ein Median nahe 0 allein genügt nicht: Lokale Fehler können sich gegenseitig aufheben. Auch der Anteil gültiger Vektoren und die räumliche Verteilung müssen betrachtet werden.

Bei deutlicher gemeinsamer Verschiebung zunächst Kamerabewegung, Musterbewegung, Fokusänderungen und Beleuchtung prüfen.

## Versuch 2: Referenz ohne Heizung, Vergleich mit warmer Luft

Für dieses Bildpaar bleibt die Kamera durchgehend an derselben Position. Belichtung und Verstärkung bleiben gleich.

1. Aufbau nach vorheriger Erwärmung ausreichend abkühlen lassen.
2. Wärmequelle bereits an ihrer vorgesehenen Position aufstellen und ausgeschaltet lassen.
3. Aufnahme starten:

```bash
python scripts/capture.py data/raw/heated_01 --exposure-ms 5 --gain 0 --heated
```

4. Bei ausgeschalteter Wärmequelle Enter drücken: kalte Referenzaufnahme.
5. Wärmequelle einschalten, ohne Kamera oder Muster zu berühren.
6. Als ersten Versuch etwa 30 bis 60 Sekunden warten. Diese Wartezeit ist ein Startwert und hängt von der Wärmequelle ab.
7. Wenn die warme Luft durch den Untersuchungsbereich aufsteigt, erneut Enter drücken: beheizte Vergleichsaufnahme.

`--heated` ändert die Aufforderung für die zweite Aufnahme und die Kennzeichnung in `camera.json`. Das Script steuert die Wärmequelle nicht.

Auswertung:

```bash
python scripts/analyze.py data/raw/heated_01/reference data/raw/heated_01/moving --window 40
```

Danach mit den statischen Ergebnissen vergleichen. Gesucht werden örtlich begrenzte Veränderungen im Bereich oberhalb der Wärmequelle.

Für eine weitere Aufnahme ein neues Bildpaar in einem neuen Ordner erstellen. Vor einer neuen kalten Referenz den Aufbau wieder abkühlen lassen.

## Ausgabedateien verstehen

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
- `frame.json`: Bildform, Datentyp, Farbformat, Quelle und Zeitstempel.
- `camera.json`: Testart, angeforderte Belichtung, vom SDK zurückgegebene Belichtung und angeforderte Verstärkung.

Die Zeitstempel stammen von der Rechneruhr unmittelbar nach der Aufnahme. Sie sind keine Kamera-Hardwarezeitstempel.

### Verschiebungsfeld

Die Analyse nennt im Terminal den erzeugten Pfad:

```text
data/processed/bos_pair_…/field.npz
```

| Feld | Bedeutung |
|---|---|
| `x_px`, `y_px` | Mittelpunkte der Fenster im Referenzbild, in Pixeln |
| `u_px` | Horizontale Verschiebung; positiv nach rechts |
| `v_px` | Vertikale Verschiebung; positiv nach unten |
| `magnitude_px` | Länge des Verschiebungsvektors, in Pixeln |
| `ncc_peak` | Stärke der besten normierten Korrelation |
| `peak_margin` | Abstand zum nächstbesten getrennten Korrelationsmaximum |
| `valid` | Kennzeichnung gültiger Verschiebungsmessungen |

Beispiel: `u_px = 1` und `v_px = -0.5` bedeuten, dass das Muster gegenüber der Referenz um 1 Pixel nach rechts und 0,5 Pixel nach oben verschoben erscheint.

Ungültige Verschiebungen sind `NaN`. Sie dürfen nicht als Nullbewegung interpretiert werden.

Der Standard-Suchradius beträgt 4 Pixel. Treffer genau am Suchrand werden verworfen, weil dort keine vollständige Subpixelverfeinerung möglich ist.

Die Analyse erlaubt:

```text
--window 32
--window 40
--window 52
```

Größere Fenster verwenden mehr Musterinformation, mitteln aber über einen größeren Bildbereich. Für den ersten Vergleich bei 40 Pixeln bleiben.

### Protokolle

- `logs/io_check.log`
- `logs/validate.log`
- `logs/capture.log`
- `logs/analyze.log`

Die Protokolle werden bei weiteren Läufen ergänzt. Beim Vergleichen auf Zeitstempel achten und den jeweiligen Rohdatenordner dem ausgegebenen Ergebnisordner zuordnen.

## Bekannte Einschränkungen

- Die Hardwarefunktion ist noch am realen Gerät zu bestätigen.
- Eine grafische Darstellung des Verschiebungsfeldes fehlt bisher.
- Es gibt keine Umrechnung in Temperatur, Dichte oder Luftgeschwindigkeit.
- In `src/bos/io.py` enthält `channel_order` aktuell den Wert `" RGB"` mit einem führenden Leerzeichen. Projektintern stimmen Schreiben und Lesen überein. Eine Korrektur auf `"RGB"` muss auch bei bereits vorhandenen Metadaten berücksichtigt werden.