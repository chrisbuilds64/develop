-- P002 · 11/2021 · Mahnwesen Stufe 1: Mahnstufe je Rechnung
SET DEFINE OFF
WHENEVER SQLERROR EXIT FAILURE

ALTER TABLE ov_rechnungen ADD (mahnstufe NUMBER(1) DEFAULT 0 NOT NULL);
