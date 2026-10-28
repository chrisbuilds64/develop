-- P001 · 03/2018 · Statusliste langsam (Ticket 1187): Index auf Auftragsstatus, Index fuer Rechnungen je Auftrag
SET DEFINE OFF
WHENEVER SQLERROR EXIT FAILURE

CREATE INDEX idx_auf_status ON ov_auftraege(status) TABLESPACE sdlc_data;
CREATE INDEX idx_re_aufnr   ON ov_rechnungen(aufnr) TABLESPACE sdlc_data;
