-- Buehnenbau: ein Index, den 2022 jemand nachts in PROD angelegt hat. Kein Skript, kein Ticket.
SET DEFINE OFF
WHENEVER SQLERROR EXIT FAILURE

CREATE INDEX idx_auf_liefer ON ov_auftraege(lieferdatum) TABLESPACE sdlc_data;
