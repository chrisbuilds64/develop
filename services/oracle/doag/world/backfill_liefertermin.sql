-- Backfill: offene Auftraege bekommen ihren Liefertermin nachgetragen (gewuenschtes Lieferdatum, sonst Auftragsdatum + 14 Tage).
-- Abgeschlossene und stornierte Auftraege bleiben leer: ihnen wurde nie ein Termin zugesagt.
UPDATE ov_auftraege
SET    liefertermin = NVL(lieferdatum, auftragsdatum + 14)
WHERE  status IN ('NEU', 'BESTAETIGT', 'IN_LIEFERUNG')
AND    liefertermin IS NULL;
COMMIT;
