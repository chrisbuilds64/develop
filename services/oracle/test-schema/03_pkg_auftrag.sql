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
