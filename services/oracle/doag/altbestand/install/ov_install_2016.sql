-- Erstinstallation Auftragsverwaltung
-- Ausfuehren als Anwendungsschema (SQL*Plus / SQLcl)
SET DEFINE OFF
WHENEVER SQLERROR EXIT FAILURE

-- =============================================================================
-- Auftragsverwaltung (OV) — Erstinstallation
-- Stand 03/2016, Version 1.0. Reihenfolge: dieses Skript, dann patches/ in Nummernfolge.
-- =============================================================================

-- Kunden
CREATE TABLE ov_kunden (
    knr         NUMBER          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR2(100)   NOT NULL,
    email       VARCHAR2(150),
    ort         VARCHAR2(80),
    land        VARCHAR2(3)     DEFAULT 'AUT',
    aktiv       NUMBER(1)       DEFAULT 1 NOT NULL,
    angelegt_am DATE            DEFAULT SYSDATE NOT NULL
) TABLESPACE sdlc_data;

-- Artikel / Produkte
CREATE TABLE ov_artikel (
    anr             NUMBER          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bezeichnung     VARCHAR2(200)   NOT NULL,
    einheit         VARCHAR2(20)    DEFAULT 'STK',
    preis           NUMBER(10,2)    NOT NULL,
    lagerbestand    NUMBER(10)      DEFAULT 0 NOT NULL,
    min_bestand     NUMBER(10)      DEFAULT 5,
    aktiv           NUMBER(1)       DEFAULT 1 NOT NULL
) TABLESPACE sdlc_data;

-- Auftragskopf
CREATE TABLE ov_auftraege (
    aufnr           NUMBER          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    knr             NUMBER          NOT NULL,
    auftragsdatum   DATE            DEFAULT SYSDATE NOT NULL,
    lieferdatum     DATE,
    status          VARCHAR2(20)    DEFAULT 'NEU' NOT NULL,
    gesamt_netto    NUMBER(12,2)    DEFAULT 0,
    mwst_satz       NUMBER(5,2)     DEFAULT 20,
    gesamt_brutto   NUMBER(12,2)    DEFAULT 0,
    anmerkung       VARCHAR2(500),
    angelegt_am     DATE            DEFAULT SYSDATE NOT NULL,
    geaendert_am    DATE,
    CONSTRAINT fk_auf_knr FOREIGN KEY (knr) REFERENCES ov_kunden(knr),
    CONSTRAINT chk_auf_status CHECK (status IN ('NEU','BESTAETIGT','IN_LIEFERUNG','GELIEFERT','STORNIERT'))
) TABLESPACE sdlc_data;

-- Auftragspositionen
CREATE TABLE ov_positionen (
    posnr       NUMBER          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    aufnr       NUMBER          NOT NULL,
    pos         NUMBER(3)       NOT NULL,
    anr         NUMBER          NOT NULL,
    menge       NUMBER(10,3)    NOT NULL,
    einzelpreis NUMBER(10,2)    NOT NULL,
    gesamtpreis NUMBER(12,2)    GENERATED ALWAYS AS (menge * einzelpreis) VIRTUAL,
    CONSTRAINT fk_pos_aufnr FOREIGN KEY (aufnr) REFERENCES ov_auftraege(aufnr),
    CONSTRAINT fk_pos_anr   FOREIGN KEY (anr)   REFERENCES ov_artikel(anr),
    CONSTRAINT uq_pos       UNIQUE (aufnr, pos)
) TABLESPACE sdlc_data;

-- Rechnungen
CREATE TABLE ov_rechnungen (
    renr            NUMBER          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    aufnr           NUMBER          NOT NULL,
    rechnungsdatum  DATE            DEFAULT SYSDATE NOT NULL,
    faellig_am      DATE,
    betrag          NUMBER(12,2)    NOT NULL,
    bezahlt_am      DATE,
    storniert       NUMBER(1)       DEFAULT 0,
    CONSTRAINT fk_re_aufnr FOREIGN KEY (aufnr) REFERENCES ov_auftraege(aufnr)
) TABLESPACE sdlc_data;

-- Protokoll (Statusänderungen)
CREATE TABLE ov_protokoll (
    id          NUMBER          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    aufnr       NUMBER,
    aktion      VARCHAR2(50)    NOT NULL,
    alt_status  VARCHAR2(20),
    neu_status  VARCHAR2(20),
    user_name   VARCHAR2(50)    DEFAULT USER,
    ts          TIMESTAMP       DEFAULT SYSTIMESTAMP NOT NULL,
    info        VARCHAR2(500)
) TABLESPACE sdlc_data;

-- Indizes
CREATE INDEX idx_auf_knr     ON ov_auftraege(knr)    TABLESPACE sdlc_data;
CREATE INDEX idx_pos_aufnr   ON ov_positionen(aufnr) TABLESPACE sdlc_data;

COMMIT;

-- =============================================================================
-- PKG_LAGER — Lagerverwaltung
-- Zuständig für: Bestandsprüfung, Reservierung, Freigabe
-- Arbeitet direkt auf ov_artikel.lagerbestand.
-- Reservierungen reduzieren lagerbestand sofort (keine separate Spalte).
-- =============================================================================

CREATE OR REPLACE PACKAGE pkg_lager AS

    -- Prüft ob genügend Bestand für p_menge vorhanden ist.
    FUNCTION bestand_ausreichend(p_anr IN NUMBER, p_menge IN NUMBER) RETURN BOOLEAN;

    -- Reduziert lagerbestand um p_menge (Reservierung bei Auftragsbestätigung).
    PROCEDURE reservieren(p_anr IN NUMBER, p_menge IN NUMBER);

    -- Gibt reservierten Bestand zurück (Stornierung eines bestätigten Auftrags).
    PROCEDURE freigeben(p_anr IN NUMBER, p_menge IN NUMBER);

    -- Gibt aktuellen Lagerbestand zurück.
    FUNCTION get_bestand(p_anr IN NUMBER) RETURN NUMBER;

END pkg_lager;
/

CREATE OR REPLACE PACKAGE BODY pkg_lager AS

    -- -------------------------------------------------------------------------
    FUNCTION get_bestand(p_anr IN NUMBER) RETURN NUMBER IS
        v_bestand NUMBER;
    BEGIN
        SELECT lagerbestand INTO v_bestand
        FROM   ov_artikel
        WHERE  anr = p_anr;
        RETURN v_bestand;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RAISE_APPLICATION_ERROR(-20070, 'Artikel ' || p_anr || ' nicht gefunden');
    END get_bestand;

    -- -------------------------------------------------------------------------
    FUNCTION bestand_ausreichend(p_anr IN NUMBER, p_menge IN NUMBER) RETURN BOOLEAN IS
    BEGIN
        RETURN get_bestand(p_anr) >= p_menge;
    END bestand_ausreichend;

    -- -------------------------------------------------------------------------
    PROCEDURE reservieren(p_anr IN NUMBER, p_menge IN NUMBER) IS
        v_bestand NUMBER;
    BEGIN
        SELECT lagerbestand INTO v_bestand
        FROM   ov_artikel
        WHERE  anr = p_anr
        FOR UPDATE;

        IF v_bestand < p_menge THEN
            RAISE_APPLICATION_ERROR(-20071,
                'Bestand für Artikel ' || p_anr ||
                ' nicht ausreichend. Vorhanden: ' || v_bestand ||
                ', Bedarf: ' || p_menge);
        END IF;

        UPDATE ov_artikel
        SET    lagerbestand = lagerbestand - p_menge
        WHERE  anr = p_anr;
    END reservieren;

    -- -------------------------------------------------------------------------
    PROCEDURE freigeben(p_anr IN NUMBER, p_menge IN NUMBER) IS
    BEGIN
        UPDATE ov_artikel
        SET    lagerbestand = lagerbestand + p_menge
        WHERE  anr = p_anr;

        IF SQL%ROWCOUNT = 0 THEN
            RAISE_APPLICATION_ERROR(-20072, 'Artikel ' || p_anr || ' nicht gefunden');
        END IF;
    END freigeben;

END pkg_lager;
/

-- =============================================================================
-- PKG_RECHNUNG — Rechnungsverwaltung
-- Zuständig für: Rechnungsanlage, Zahlungserfassung
-- =============================================================================

CREATE OR REPLACE PACKAGE pkg_rechnung AS

    -- Erstellt automatisch eine Rechnung für einen gelieferten Auftrag.
    -- Wird von pkg_auftrag.als_geliefert_markieren aufgerufen.
    PROCEDURE erstelle_rechnung(p_aufnr IN NUMBER);

    -- Markiert eine Rechnung als bezahlt.
    PROCEDURE als_bezahlt_markieren(
        p_renr  IN NUMBER,
        p_datum IN DATE DEFAULT NULL   -- NULL = SYSDATE
    );

    -- Gibt den Bruttobetrag eines Auftrags zurück (für externe Verwendung).
    FUNCTION berechne_gesamt(p_aufnr IN NUMBER) RETURN NUMBER;

END pkg_rechnung;
/

CREATE OR REPLACE PACKAGE BODY pkg_rechnung AS

    -- -------------------------------------------------------------------------
    FUNCTION berechne_gesamt(p_aufnr IN NUMBER) RETURN NUMBER IS
        v_brutto NUMBER;
    BEGIN
        SELECT gesamt_brutto INTO v_brutto
        FROM   ov_auftraege
        WHERE  aufnr = p_aufnr;
        RETURN v_brutto;
    END berechne_gesamt;

    -- -------------------------------------------------------------------------
    PROCEDURE erstelle_rechnung(p_aufnr IN NUMBER) IS
        v_status    VARCHAR2(20);
        v_brutto    NUMBER;
        v_exists    NUMBER;
    BEGIN
        SELECT status, gesamt_brutto INTO v_status, v_brutto
        FROM   ov_auftraege
        WHERE  aufnr = p_aufnr;

        IF v_status != 'GELIEFERT' THEN
            RAISE_APPLICATION_ERROR(-20060,
                'Rechnung nur für GELIEFERT-Aufträge. Aktuell: ' || v_status);
        END IF;

        -- Doppelanlage verhindern
        SELECT COUNT(*) INTO v_exists
        FROM   ov_rechnungen
        WHERE  aufnr = p_aufnr AND storniert = 0;

        IF v_exists > 0 THEN
            RAISE_APPLICATION_ERROR(-20061,
                'Rechnung für Auftrag ' || p_aufnr || ' existiert bereits');
        END IF;

        INSERT INTO ov_rechnungen (aufnr, rechnungsdatum, faellig_am, betrag)
        VALUES (
            p_aufnr,
            SYSDATE,
            ADD_MONTHS(SYSDATE, 1),
            v_brutto
        );

        INSERT INTO ov_protokoll (aufnr, aktion, info)
        VALUES (p_aufnr, 'RECHNUNG_ERSTELLT',
                'Betrag: ' || v_brutto);
    END erstelle_rechnung;

    -- -------------------------------------------------------------------------
    PROCEDURE als_bezahlt_markieren(
        p_renr  IN NUMBER,
        p_datum IN DATE DEFAULT NULL
    ) IS
        v_storniert NUMBER;
        v_bezahlt   DATE;
    BEGIN
        SELECT storniert, bezahlt_am INTO v_storniert, v_bezahlt
        FROM   ov_rechnungen
        WHERE  renr = p_renr
        FOR UPDATE;

        IF v_storniert = 1 THEN
            RAISE_APPLICATION_ERROR(-20062,
                'Rechnung ' || p_renr || ' ist storniert');
        END IF;

        IF v_bezahlt IS NOT NULL THEN
            RAISE_APPLICATION_ERROR(-20063,
                'Rechnung ' || p_renr || ' ist bereits bezahlt am ' || TO_CHAR(v_bezahlt, 'DD.MM.YYYY'));
        END IF;

        UPDATE ov_rechnungen
        SET    bezahlt_am = NVL(p_datum, SYSDATE)
        WHERE  renr = p_renr;
    END als_bezahlt_markieren;

END pkg_rechnung;
/

-- =============================================================================
-- PKG_AUFTRAG — Auftragsverwaltung
-- Zuständig für: Anlegen, Bestätigen, Stornieren, Statusabfragen
-- =============================================================================

CREATE OR REPLACE PACKAGE pkg_auftrag AS

    -- Legt einen neuen Auftrag ohne Positionen an und gibt die AUFNR zurück.
    -- Positionen müssen danach über add_position hinzugefügt werden.
    FUNCTION create_auftrag(
        p_knr       IN ov_auftraege.knr%TYPE,
        p_lieferdatum IN DATE DEFAULT NULL,
        p_anmerkung IN VARCHAR2 DEFAULT NULL
    ) RETURN NUMBER;

    -- Fügt eine Position zu einem bestehenden Auftrag hinzu.
    -- Auftrag muss im Status NEU sein, Lagerbestand wird nicht geprüft.
    PROCEDURE add_position(
        p_aufnr     IN NUMBER,
        p_anr       IN NUMBER,
        p_menge     IN NUMBER,
        p_preis     IN NUMBER DEFAULT NULL   -- NULL = aktueller Artikelpreis
    );

    -- Bestätigt einen Auftrag: prüft Lagerbestand über pkg_lager,
    -- aktualisiert Gesamtbeträge, setzt Status auf BESTAETIGT.
    PROCEDURE bestaetigen(p_aufnr IN NUMBER);

    -- Setzt einen Auftrag auf IN_LIEFERUNG.
    -- Nur möglich wenn Status = BESTAETIGT.
    PROCEDURE in_lieferung_setzen(p_aufnr IN NUMBER);

    -- Markiert Auftrag als geliefert und erstellt automatisch Rechnung.
    PROCEDURE als_geliefert_markieren(p_aufnr IN NUMBER);

    -- Storniert einen Auftrag. Nur möglich solange nicht IN_LIEFERUNG oder GELIEFERT.
    -- Gibt reservierten Lagerbestand frei.
    PROCEDURE stornieren(p_aufnr IN NUMBER, p_grund IN VARCHAR2 DEFAULT NULL);

    -- Berechnet und schreibt Netto/Brutto auf den Auftragskopf.
    PROCEDURE update_gesamtbetrag(p_aufnr IN NUMBER);

END pkg_auftrag;
/

CREATE OR REPLACE PACKAGE BODY pkg_auftrag AS

    -- Interne Hilfsprozedur: Statusänderung protokollieren
    PROCEDURE log_status(
        p_aufnr     IN NUMBER,
        p_alt       IN VARCHAR2,
        p_neu       IN VARCHAR2,
        p_info      IN VARCHAR2 DEFAULT NULL
    ) IS
    BEGIN
        INSERT INTO ov_protokoll (aufnr, aktion, alt_status, neu_status, info)
        VALUES (p_aufnr, 'STATUS_AENDERUNG', p_alt, p_neu, p_info);
    END log_status;

    -- -------------------------------------------------------------------------
    FUNCTION create_auftrag(
        p_knr         IN ov_auftraege.knr%TYPE,
        p_lieferdatum IN DATE DEFAULT NULL,
        p_anmerkung   IN VARCHAR2 DEFAULT NULL
    ) RETURN NUMBER IS
        v_knr_ok    NUMBER;
        v_aufnr     NUMBER;
    BEGIN
        -- Kunde muss existieren und aktiv sein
        SELECT COUNT(*) INTO v_knr_ok
        FROM   ov_kunden
        WHERE  knr = p_knr AND aktiv = 1;

        IF v_knr_ok = 0 THEN
            RAISE_APPLICATION_ERROR(-20001, 'Kunde ' || p_knr || ' nicht gefunden oder inaktiv');
        END IF;

        INSERT INTO ov_auftraege (knr, lieferdatum, status, anmerkung)
        VALUES (p_knr, p_lieferdatum, 'NEU', p_anmerkung)
        RETURNING aufnr INTO v_aufnr;

        INSERT INTO ov_protokoll (aufnr, aktion, neu_status, info)
        VALUES (v_aufnr, 'ANLAGE', 'NEU', 'Auftrag angelegt für KNR ' || p_knr);

        RETURN v_aufnr;
    END create_auftrag;

    -- -------------------------------------------------------------------------
    PROCEDURE add_position(
        p_aufnr IN NUMBER,
        p_anr   IN NUMBER,
        p_menge IN NUMBER,
        p_preis IN NUMBER DEFAULT NULL
    ) IS
        v_status    VARCHAR2(20);
        v_preis     NUMBER;
        v_max_pos   NUMBER;
    BEGIN
        -- Auftrag muss im Status NEU sein
        SELECT status INTO v_status
        FROM   ov_auftraege
        WHERE  aufnr = p_aufnr
        FOR UPDATE;

        IF v_status != 'NEU' THEN
            RAISE_APPLICATION_ERROR(-20010,
                'Positionen können nur bei Status NEU hinzugefügt werden. Aktuell: ' || v_status);
        END IF;

        -- Preis: Parameter oder aktueller Listenpreis
        IF p_preis IS NOT NULL THEN
            v_preis := p_preis;
        ELSE
            SELECT preis INTO v_preis FROM ov_artikel WHERE anr = p_anr;
        END IF;

        -- Nächste Positionsnummer
        SELECT NVL(MAX(pos), 0) + 10 INTO v_max_pos
        FROM   ov_positionen
        WHERE  aufnr = p_aufnr;

        INSERT INTO ov_positionen (aufnr, pos, anr, menge, einzelpreis)
        VALUES (p_aufnr, v_max_pos, p_anr, p_menge, v_preis);

        -- Gesamtbetrag direkt aktualisieren
        update_gesamtbetrag(p_aufnr);
    END add_position;

    -- -------------------------------------------------------------------------
    PROCEDURE update_gesamtbetrag(p_aufnr IN NUMBER) IS
        v_netto     NUMBER;
        v_mwst      NUMBER;
    BEGIN
        SELECT NVL(SUM(menge * einzelpreis), 0)
        INTO   v_netto
        FROM   ov_positionen
        WHERE  aufnr = p_aufnr;

        SELECT mwst_satz INTO v_mwst
        FROM   ov_auftraege WHERE aufnr = p_aufnr;

        UPDATE ov_auftraege
        SET    gesamt_netto  = v_netto,
               gesamt_brutto = ROUND(v_netto * (1 + v_mwst / 100), 2),
               geaendert_am  = SYSDATE
        WHERE  aufnr = p_aufnr;
    END update_gesamtbetrag;

    -- -------------------------------------------------------------------------
    PROCEDURE bestaetigen(p_aufnr IN NUMBER) IS
        v_status    VARCHAR2(20);
        v_netto     NUMBER;

        -- Cursor über alle Positionen dieses Auftrags
        CURSOR c_pos IS
            SELECT p.anr, p.menge, a.bezeichnung
            FROM   ov_positionen p
            JOIN   ov_artikel a ON a.anr = p.anr
            WHERE  p.aufnr = p_aufnr;
    BEGIN
        SELECT status, gesamt_netto INTO v_status, v_netto
        FROM   ov_auftraege
        WHERE  aufnr = p_aufnr
        FOR UPDATE;

        IF v_status != 'NEU' THEN
            RAISE_APPLICATION_ERROR(-20020,
                'Bestätigung nur bei Status NEU möglich. Aktuell: ' || v_status);
        END IF;

        IF v_netto = 0 THEN
            RAISE_APPLICATION_ERROR(-20021,
                'Auftrag ' || p_aufnr || ' hat keine Positionen oder Gesamtbetrag = 0');
        END IF;

        -- Lagerbestand für jede Position prüfen und reservieren
        FOR r IN c_pos LOOP
            IF NOT pkg_lager.bestand_ausreichend(r.anr, r.menge) THEN
                RAISE_APPLICATION_ERROR(-20022,
                    'Nicht genug Bestand für Artikel: ' || r.bezeichnung ||
                    ' (ANR=' || r.anr || ', Bedarf=' || r.menge || ')');
            END IF;
            pkg_lager.reservieren(r.anr, r.menge);
        END LOOP;

        UPDATE ov_auftraege
        SET    status = 'BESTAETIGT', geaendert_am = SYSDATE
        WHERE  aufnr = p_aufnr;

        log_status(p_aufnr, 'NEU', 'BESTAETIGT', 'Auftrag bestätigt, Lagerbestand reserviert');
    END bestaetigen;

    -- -------------------------------------------------------------------------
    PROCEDURE in_lieferung_setzen(p_aufnr IN NUMBER) IS
        v_status VARCHAR2(20);
    BEGIN
        SELECT status INTO v_status
        FROM   ov_auftraege WHERE aufnr = p_aufnr FOR UPDATE;

        IF v_status != 'BESTAETIGT' THEN
            RAISE_APPLICATION_ERROR(-20030,
                'IN_LIEFERUNG nur von BESTAETIGT möglich. Aktuell: ' || v_status);
        END IF;

        UPDATE ov_auftraege
        SET status = 'IN_LIEFERUNG', geaendert_am = SYSDATE
        WHERE aufnr = p_aufnr;

        log_status(p_aufnr, 'BESTAETIGT', 'IN_LIEFERUNG');
    END in_lieferung_setzen;

    -- -------------------------------------------------------------------------
    PROCEDURE als_geliefert_markieren(p_aufnr IN NUMBER) IS
        v_status VARCHAR2(20);
    BEGIN
        SELECT status INTO v_status
        FROM   ov_auftraege WHERE aufnr = p_aufnr FOR UPDATE;

        IF v_status != 'IN_LIEFERUNG' THEN
            RAISE_APPLICATION_ERROR(-20040,
                'GELIEFERT nur von IN_LIEFERUNG möglich. Aktuell: ' || v_status);
        END IF;

        UPDATE ov_auftraege
        SET status = 'GELIEFERT', geaendert_am = SYSDATE
        WHERE aufnr = p_aufnr;

        log_status(p_aufnr, 'IN_LIEFERUNG', 'GELIEFERT', 'Lieferung bestätigt');

        -- Rechnung automatisch erstellen
        pkg_rechnung.erstelle_rechnung(p_aufnr);
    END als_geliefert_markieren;

    -- -------------------------------------------------------------------------
    PROCEDURE stornieren(p_aufnr IN NUMBER, p_grund IN VARCHAR2 DEFAULT NULL) IS
        v_status VARCHAR2(20);

        CURSOR c_pos IS
            SELECT anr, menge FROM ov_positionen WHERE aufnr = p_aufnr;
    BEGIN
        SELECT status INTO v_status
        FROM   ov_auftraege WHERE aufnr = p_aufnr FOR UPDATE;

        IF v_status IN ('IN_LIEFERUNG', 'GELIEFERT', 'STORNIERT') THEN
            RAISE_APPLICATION_ERROR(-20050,
                'Stornierung nicht möglich bei Status: ' || v_status);
        END IF;

        -- Reservierten Lagerbestand freigeben (nur wenn bereits bestätigt)
        IF v_status = 'BESTAETIGT' THEN
            FOR r IN c_pos LOOP
                pkg_lager.freigeben(r.anr, r.menge);
            END LOOP;
        END IF;

        UPDATE ov_auftraege
        SET status = 'STORNIERT', geaendert_am = SYSDATE
        WHERE aufnr = p_aufnr;

        log_status(p_aufnr, v_status, 'STORNIERT',
                   NVL(p_grund, 'Stornierung ohne Begründung'));
    END stornieren;

END pkg_auftrag;
/

-- =============================================================================
-- Stammdaten: Kunden und Artikel
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
COMMIT;
