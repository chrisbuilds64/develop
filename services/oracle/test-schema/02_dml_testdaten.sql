-- =============================================================================
-- Auftragsverwaltung — Testdaten
-- =============================================================================

-- Kunden
INSERT INTO ov_kunden (name, email, ort, land) VALUES ('Mayer GmbH', 'bestellung@mayer.at', 'Wien', 'AUT');
INSERT INTO ov_kunden (name, email, ort, land) VALUES ('Technik AG', 'einkauf@technik-ag.de', 'München', 'DEU');
INSERT INTO ov_kunden (name, email, ort, land) VALUES ('Bau Huber', 'info@bau-huber.at', 'Linz', 'AUT');
INSERT INTO ov_kunden (name, email, ort, land) VALUES ('Handel Schweiz', 'order@handel-ch.ch', 'Zürich', 'CHE');
INSERT INTO ov_kunden (name, email, ort, land) VALUES ('Muster KG', NULL, 'Graz', 'AUT');

-- Artikel
INSERT INTO ov_artikel (bezeichnung, einheit, preis, lagerbestand, min_bestand) VALUES ('Schraube M8x20',   'STK',   0.35,  5000, 200);
INSERT INTO ov_artikel (bezeichnung, einheit, preis, lagerbestand, min_bestand) VALUES ('Stahlrohr DN50',   'M',    12.90,   300,  20);
INSERT INTO ov_artikel (bezeichnung, einheit, preis, lagerbestand, min_bestand) VALUES ('Hydraulikpumpe X1','STK', 890.00,    15,   2);
INSERT INTO ov_artikel (bezeichnung, einheit, preis, lagerbestand, min_bestand) VALUES ('Dichtungskit A',   'SET',  45.50,   200,  10);
INSERT INTO ov_artikel (bezeichnung, einheit, preis, lagerbestand, min_bestand) VALUES ('Motoröl 5W40 1L',  'L',     8.90,  1200, 100);
INSERT INTO ov_artikel (bezeichnung, einheit, preis, lagerbestand, min_bestand) VALUES ('Schweißdraht 1mm', 'KG',   18.00,   400,  50);
INSERT INTO ov_artikel (bezeichnung, einheit, preis, lagerbestand, min_bestand) VALUES ('Kugellager 6205',  'STK',   6.75,   800,  30);
INSERT INTO ov_artikel (bezeichnung, einheit, preis, lagerbestand, min_bestand) VALUES ('Steuermodul SM3',  'STK', 420.00,     4,   1);

-- Aufträge (manuell mit bekannten KNR)
INSERT INTO ov_auftraege (knr, auftragsdatum, lieferdatum, status, anmerkung)
VALUES (1, DATE '2026-04-10', DATE '2026-04-20', 'GELIEFERT', 'Lieferung pünktlich');

INSERT INTO ov_auftraege (knr, auftragsdatum, lieferdatum, status)
VALUES (2, DATE '2026-04-15', DATE '2026-04-30', 'BESTAETIGT');

INSERT INTO ov_auftraege (knr, auftragsdatum, status, anmerkung)
VALUES (1, DATE '2026-05-02', 'NEU', 'Eilauftrag — bitte bevorzugt bearbeiten');

INSERT INTO ov_auftraege (knr, auftragsdatum, status)
VALUES (3, DATE '2026-05-10', 'STORNIERT');

INSERT INTO ov_auftraege (knr, auftragsdatum, status)
VALUES (4, DATE '2026-05-12', 'IN_LIEFERUNG');

-- Positionen Auftrag 1
INSERT INTO ov_positionen (aufnr, pos, anr, menge, einzelpreis) VALUES (1, 1, 1, 500,  0.35);
INSERT INTO ov_positionen (aufnr, pos, anr, menge, einzelpreis) VALUES (1, 2, 4,   3, 45.50);
INSERT INTO ov_positionen (aufnr, pos, anr, menge, einzelpreis) VALUES (1, 3, 7,  10,  6.75);

-- Positionen Auftrag 2
INSERT INTO ov_positionen (aufnr, pos, anr, menge, einzelpreis) VALUES (2, 1, 3,  2, 890.00);
INSERT INTO ov_positionen (aufnr, pos, anr, menge, einzelpreis) VALUES (2, 2, 8,  1, 420.00);

-- Positionen Auftrag 3 (Eilauftrag)
INSERT INTO ov_positionen (aufnr, pos, anr, menge, einzelpreis) VALUES (3, 1, 5, 50,   8.90);
INSERT INTO ov_positionen (aufnr, pos, anr, menge, einzelpreis) VALUES (3, 2, 6, 20,  18.00);

-- Positionen Auftrag 4 (storniert — keine Positionen gelöscht, historisch)
INSERT INTO ov_positionen (aufnr, pos, anr, menge, einzelpreis) VALUES (4, 1, 2, 10,  12.90);

-- Positionen Auftrag 5
INSERT INTO ov_positionen (aufnr, pos, anr, menge, einzelpreis) VALUES (5, 1, 1, 200,  0.35);
INSERT INTO ov_positionen (aufnr, pos, anr, menge, einzelpreis) VALUES (5, 2, 7,  20,  6.75);
INSERT INTO ov_positionen (aufnr, pos, anr, menge, einzelpreis) VALUES (5, 3, 4,   5, 45.50);

-- Nettobetrag auf Aufträgen aktualisieren
UPDATE ov_auftraege a SET
    gesamt_netto   = (SELECT NVL(SUM(menge * einzelpreis), 0) FROM ov_positionen WHERE aufnr = a.aufnr),
    gesamt_brutto  = (SELECT NVL(SUM(menge * einzelpreis), 0) FROM ov_positionen WHERE aufnr = a.aufnr) * (1 + a.mwst_satz / 100);

-- Rechnung für gelieferten Auftrag
INSERT INTO ov_rechnungen (aufnr, rechnungsdatum, faellig_am, betrag, bezahlt_am)
VALUES (1, DATE '2026-04-21', DATE '2026-05-21',
        (SELECT gesamt_brutto FROM ov_auftraege WHERE aufnr = 1),
        DATE '2026-05-05');

-- Protokolleinträge
INSERT INTO ov_protokoll (aufnr, aktion, alt_status, neu_status, info)
VALUES (1, 'STATUS_AENDERUNG', 'NEU', 'BESTAETIGT', 'Auftragsbestätigung verschickt');
INSERT INTO ov_protokoll (aufnr, aktion, alt_status, neu_status, info)
VALUES (1, 'STATUS_AENDERUNG', 'BESTAETIGT', 'IN_LIEFERUNG', 'Ware versendet, Tracking: AT123456');
INSERT INTO ov_protokoll (aufnr, aktion, alt_status, neu_status, info)
VALUES (1, 'STATUS_AENDERUNG', 'IN_LIEFERUNG', 'GELIEFERT', 'Empfangsbestätigung erhalten');
INSERT INTO ov_protokoll (aufnr, aktion, alt_status, neu_status, info)
VALUES (4, 'STATUS_AENDERUNG', 'NEU', 'STORNIERT', 'Kunde hat storniert — Artikel nicht lieferbar');

COMMIT;
