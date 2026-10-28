-- P003 · 05/2023 · UID-Nummer fuer Geschaeftskunden (Anforderung Buchhaltung)
SET DEFINE OFF
WHENEVER SQLERROR EXIT FAILURE

ALTER TABLE ov_kunden ADD (uid_nr VARCHAR2(20));
COMMENT ON COLUMN ov_kunden.uid_nr IS 'Umsatzsteuer-Identifikationsnummer';
