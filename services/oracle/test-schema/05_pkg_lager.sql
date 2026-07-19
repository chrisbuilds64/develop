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
