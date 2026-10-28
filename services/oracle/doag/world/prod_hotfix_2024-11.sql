-- Buehnenbau: Hotfix, am 14.11.2024 direkt in PROD eingespielt. Liegt in keiner Datei des Altbestands.
SET DEFINE OFF
WHENEVER SQLERROR EXIT FAILURE

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
        v_aktiv   NUMBER;
    BEGIN
        SELECT lagerbestand, aktiv INTO v_bestand, v_aktiv
        FROM   ov_artikel
        WHERE  anr = p_anr
        FOR UPDATE;

        -- HOTFIX 2024-11-14: inaktive Artikel wurden reserviert (Stoerung 2291)
        IF v_aktiv = 0 THEN
            RAISE_APPLICATION_ERROR(-20073, 'Artikel ' || p_anr || ' ist nicht mehr aktiv');
        END IF;

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
