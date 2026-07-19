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
