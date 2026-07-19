-- =============================================================================
-- Auftragsverwaltung (OV) — DDL
-- Schema: SDLC_APP / ENTW PDB
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
CREATE INDEX idx_auf_status  ON ov_auftraege(status) TABLESPACE sdlc_data;
CREATE INDEX idx_pos_aufnr   ON ov_positionen(aufnr) TABLESPACE sdlc_data;
CREATE INDEX idx_re_aufnr    ON ov_rechnungen(aufnr) TABLESPACE sdlc_data;

COMMIT;
