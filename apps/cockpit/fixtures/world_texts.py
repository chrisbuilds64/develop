"""The long texts of the two demo worlds, kept apart from the structure. All invented."""

ESSAY = """# The review that reads itself

Last month I let an agent review its own output for a week. It went well, which is the problem.

Every morning the pipeline produced a draft, and every morning the same agent checked the draft against the same rules it had just written it by. The checks passed. The log was green. I read three of the drafts anyway, because reading is the only part of the job I do not trust a tool with, and two of them contained a claim that was simply wrong. Not dangerous, not even embarrassing. Wrong in a way that only someone who had been in the room would notice.

The review had not failed. It had done exactly what it was built to do: confirm that the output was consistent with itself. A check that shares its author with the thing it checks cannot be surprised. It has the same blind spots, the same habits, the same idea of what a good paragraph looks like.

So I changed one thing. The agent still drafts, and a second pass still checks form: length, structure, the rules we wrote down. But the question "is this true" now goes to a person, and the pipeline cannot move the piece forward until that person has written one line into the review file. Not a click. A line, with a name on it.

This costs me about ten minutes per piece. I expected to resent it. Instead the review file became the most useful document in the folder. It shows what the agent got wrong, how often, and in which direction. After three weeks the pattern was obvious: the agent rounds numbers toward the story it is telling. It never invents a figure. It nudges a real one.

None of that would have shown up in a pass rate.

The lesson I take from this is narrow, and I would rather keep it narrow. Automated review is good at consistency and bad at truth, and the two feel identical from the outside. If your pipeline reports that everything passed, ask who wrote the thing that checked it. If the answer is the same system, you have measured agreement, not quality.

What I do now is simple. Form is checked by a machine. Facts are checked by a person. The handover between them is a file, so it can be read later by anyone who wants to know why a piece went out.

It is slower than the green log. It is also the only version of this week I would defend in front of a client.

Next time: what the review file looks like after a hundred pieces, and which of my rules turned out to be decoration.
"""

SCRIPT = """# The arc, spoken

Cold open. Read slowly.

Last week I told you that a pipeline is a promise about order. This week I want to say what happens when the promise is broken, and nobody notices.

Here is the case. A piece of writing moves through five stations: idea, draft, review, image, schedule. Each station has an owner. The trouble starts when a station is skipped because it looked redundant. The draft went straight to the image. The review happened, but in somebody's head.

Nothing breaks. That is the point I want you to hear. Nothing breaks, and so the skipped station never gets blamed. It simply stops existing, one shortcut at a time.

Second part. Why does this happen? Because order is invisible when it works. You do not feel a gate that opens. You only feel one that closes. So people, reasonably, remove the gates that close.

What I did about it is not clever. I made the order visible. Every piece lives in a folder named after its stage. To move forward, it has to physically move. A person, or a clearly named helper, does the move, and the move leaves a line in a log.

Third part, and the one I care about most. The log is not for control. Nobody reads it on a normal day. It is there for the day something goes wrong, so that the question is "where did it leave the road" and not "who did this".

Close. Three things to take away. One: order is a promise, and a promise needs a witness. Two: a skipped station does not fail, it disappears. Three: write the move down, even when nobody asks.

Next week: the helper that forgot, and what it cost.
"""

TELEPROMPTER = """Last week I told you that a pipeline is a promise about order.
This week: what happens when the promise is broken, and nobody notices.

A piece moves through five stations. Idea. Draft. Review. Image. Schedule.
Each station has an owner.
The trouble starts when one is skipped because it looked redundant.

Nothing breaks. Hear that. Nothing breaks.
So the skipped station never gets blamed. It just stops existing.

Order is invisible when it works.
You only feel the gate that closes.
So people remove the gates that close.

My answer is not clever. I made the order visible.
A piece lives in a folder named after its stage.
To move on, it has to move. And the move leaves a line.

The log is not for control.
It is for the day something goes wrong.
So the question is: where did it leave the road, not who did this.

One: order is a promise, and a promise needs a witness.
Two: a skipped station does not fail, it disappears.
Three: write the move down, even when nobody asks.
"""

SHOWNOTES = """The Arc, Spoken - show notes

In this episode: why a skipped review step never shows up as a failure, and what a visible order looks like in practice.

Chapters
00:00 Cold open
02:10 The case: five stations, one shortcut
06:40 Why nobody blames a missing gate
11:25 Making the order visible
15:00 What the log is for
17:30 Three things to take away

Mentioned: the stage folders, the review file, the run log.
"""

GUTACHTEN = """# Gutachten (Entwurf) - Wasserschaden Badezimmer, Mehrfamilienhaus Lindenweg

Aktenzeichen: S-2026-0416 | Versicherungsnehmerin: M. Hartmann (Beispielname) | Schadentag: 03.10.2026

## 1. Auftrag

Die Versicherung hat uns beauftragt, Ursache, Umfang und Höhe eines Leitungswasserschadens im Badezimmer der Wohnung im ersten Obergeschoss zu begutachten. Grundlage sind die Schadenmeldung vom 05.10., das Besichtigungsprotokoll vom 08.10. und die Fotodokumentation.

## 2. Feststellungen vor Ort

Im Badezimmer zeigt sich eine Durchfeuchtung der Wandfläche hinter der Badewanne auf einer Breite von etwa 1,8 Metern. Die Feuchtemessung ergab im unteren Wandbereich Werte zwischen 82 und 96 Digits, im Referenzbereich der Nachbarwand 18 Digits. Der Estrich neben der Wanne ist randnah feucht. Eine Durchfeuchtung der Decke im Erdgeschoss ist sichtbar, aber begrenzt.

Die Silikonfuge am Wannenrand ist auf etwa 60 Zentimetern Länge gerissen und abgelöst. Der Wasserzulauf und die Armatur wiesen bei der Druckprobe keine Undichtigkeit auf.

## 3. Ursache

Nach unserer Einschätzung ist der Schaden auf die defekte Wannenfuge zurückzuführen, durch die über einen längeren Zeitraum Spritzwasser in den Wandaufbau gelangt ist. Ein plötzliches Austreten von Leitungswasser aus einer Rohrleitung konnten wir nicht feststellen.

Dies ist für die Einordnung wesentlich. Bei einem Schaden durch dauerhaft eindringende Feuchtigkeit ist der Versicherungsschutz in der Regel anders zu bewerten als bei einem Rohrbruch. Die abschließende rechtliche Bewertung obliegt dem Versicherer.

## 4. Umfang und Kosten

Zu erneuern sind die Wandfliesen auf etwa 4 Quadratmetern, der Putz dahinter, die Fuge sowie die Abdichtung im Wannenbereich. Der Estrich ist nach Trocknung erneut zu prüfen. Die Trocknung wird mit etwa 14 Tagen veranschlagt.

Die Schadenhöhe schätzen wir auf rund 6.800 Euro brutto. Darin enthalten sind Trocknung, Abdichtung und Fliesenarbeiten. Nicht enthalten sind Maßnahmen an der Decke im Erdgeschoss, die gesondert zu bewerten sind.

## 5. Offene Punkte

Das Alter der Abdichtung ist nicht belegt. Eine Rechnung der letzten Badsanierung liegt nicht vor und wurde angefordert. Bis zum Eingang bleibt die Einschätzung zur Dauer der Durchfeuchtung vorläufig.
"""

BESICHTIGUNG = """# Besichtigungsprotokoll - Hagelschaden Reihenhaus Ostring

Aktenzeichen: S-2026-0306 | Termin: 12.10.2026, 10:15 Uhr | Anwesend: Eigentümer, Gutachter, Fotopartner

## Zugang und Rahmen

Der Eigentümer hat das Objekt geöffnet. Das Wetter am Besichtigungstag war trocken, der Dachbereich war über eine Leiter und per Drohne einsehbar. Das Ereignis liegt nach Angabe des Eigentümers drei Wochen zurück.

## Dach

Die Dachfläche ist mit Betondachsteinen eingedeckt. Auf der Südseite zeigen etwa zwölf Steine Absplitterungen und Risse. Auf der Nordseite fanden wir keine Schäden. Die Dachrinne ist an zwei Stellen eingedellt. Die Dachfenster sind unbeschädigt.

## Fassade und Nebengebäude

An der Südfassade sind Putzabplatzungen von der Größe einer Handfläche an drei Stellen zu sehen. Ob diese vom Hagel stammen, ist nicht sicher, da Frostschäden denkbar sind. Das Gartenhaus hat ein beschädigtes Wellplattendach.

## Innenräume

Im Dachgeschoss gibt es einen Feuchtefleck von etwa 40 mal 30 Zentimetern unter der betroffenen Dachfläche. Die Messung ergab erhöhte Werte, die Dämmung ist angrenzend trocken.

## Fotos

Zur Dokumentation wurden 38 Fotos erstellt, davon 14 vom Dach per Drohne. Die Aufnahmen der Fassade sind noch nachzuholen, da das Licht zu flach war.

## Offene Punkte

Die Herkunft der Putzschäden bleibt zu klären. Ein Angebot des Dachdeckers wurde angefordert. Eine Haftungsfrage gegenüber Dritten stellt sich nach jetzigem Stand nicht.
"""
