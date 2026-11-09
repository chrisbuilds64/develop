# casefile auf einer Seite

**casefile ist eine Arbeitsliste, deren Punkte Unterlagen tragen und an Toren geprüft werden.**

Alles andere ist Konfiguration. Die Arbeitsliste ist casefile ohne Zusatz, deshalb lernt man es an ihr.

## Jeder Begriff, an einem Todo

| Begriff | In der Arbeitsliste | Was es allgemein ist |
|---|---|---|
| **Akte** | ein Todo, `SYS-147` | ein Ordner mit `meta.json` und Verlauf (`review.md`); die Ordner sind die Wahrheit |
| **Stufe** | Backlog, Nächstes, Läuft, Wartet, Erledigt | der Ordner, in dem die Akte steht; Weiterschieben heißt den Ordner verschieben |
| **Wer ist dran** | der Zuständige | eine Funktion über Akte und Stufe; Oberfläche, Agenten und Kommandozeile fragen dieselbe |
| **Schritt** | „Anfangen", „Erledigt", „Ändern" | ein Zug, ganz oder gar nicht, protokolliert; derselbe Schritt zweimal ändert nichts |
| **Werteliste** | Bereich, Wichtigkeit, Herkunft | die festen Werte, die eine Akte tragen darf, mit Wörtern und Farben |
| **Feld** | Zuständiger, Termin | ein erklärter Wert, den eine Person ändern darf; der Verlauf nennt alt → neu |
| **Unterlage** | eine Skizze, ein Entwurf am Todo | jede Datei im Akten-Ordner, versioniert über den Namen (`entwurf.v2.md`) |
| **Tor** | keins — jedes Mitglied schiebt jeden Punkt | ein Zug, den nur eine Rolle machen darf, mit dem, was vorher da sein muss, bei Bedarf vier Augen |
| **Abhängigkeit** | „wartet auf SYS-136" | eine Akte wartet auf andere, auch in anderen Anwendungen; frei, wenn sie schließen, nie von selbst bewegt |
| **Übergabe** | ans Team teilen, an eine Person delegieren | eine Akte wechselt den Datenpunkt oder eröffnet anderswo eine Akte mit Rückverweis |
| **Datenpunkt** | mein privater Ordner, der Team-Ordner | wo die Akten liegen und wer sie lesen und schreiben darf; der Schutz kommt vom Speicher, nicht vom Bildschirm |
| **Anwendungsinstanz** | „Arbeitsliste" im Team-Workspace | eine Anwendung (reine Konfiguration), an Datenpunkte gebunden; eine Anwendung kann vielfach laufen |
| **Workspace** | ChrisBuilds64 | Datenpunkte, die Anwendungsinstanzen darauf, und die Menschen und Agenten, die dort arbeiten |

## Was die anderen Anwendungen hinzufügen

| Anwendung | Fügt Wörter hinzu | Fügt Pflichtunterlagen hinzu | Fügt Tore hinzu |
|---|---|---|---|
| **PressRoom** (Inhalte) | Idee, Entwurf, Review, veröffentlicht | den Text vor dem Review, die Bilder vor der Freigabe | das Text-Tor des Autors, das Bild-Tor |
| **Shipyard** (Softwareänderungen) | Auftrag, Pull Request, Release | Auftrag, Pull Request, Prüflauf, Release-Nachweis | der Product Owner merged und nimmt jede Stufe ab; nie der Autor |
| **Schadenakte** (Versicherung) | Schaden, Gutachten, Auszahlung | Meldung, Rechnung, Gutachten | vier Augen ab einem Betrag; keine Auszahlung ohne Rechnung |
| **Posteingang** (Mail) | Mail, Regel, Übergabe | die Mail selbst | eine Person bestätigt die Regel, bevor anderswo eine Akte entsteht |

Jede ist die Arbeitsliste plus diese drei Dinge — geschrieben in Konfigurationsdateien, nicht in Code. Das ist der
Anspruch des Systems, und an der Arbeitsliste lässt er sich prüfen: Was eine Domäne braucht und sich nicht in Wörtern,
Pflichtunterlagen und Toren sagen lässt, ist ein fehlender Begriff im Kern — und der kommt in den Kern, für alle
Domänen zugleich.

*Belege: ADR-031 (Arbeitsliste), ADR-032 (was ein Workspace ist), ADR-015 (Domänen als Konfiguration), ADR-013 (die
Dateien sind die Wahrheit). Die Musterwelt „Arbeitsliste" zeigt jede Zeile oben an erfundenen Todos.*
