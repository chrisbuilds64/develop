-- P004 · 06/2026 · Tabelle fuer die neue APEX-App "Order Overview" (Workshop Juni)
SET DEFINE OFF
WHENEVER SQLERROR EXIT FAILURE

CREATE TABLE auftraege (
    id          NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kunde       VARCHAR2(200)  NOT NULL,
    titel       VARCHAR2(300)  NOT NULL,
    status      VARCHAR2(50)   DEFAULT 'NEU' NOT NULL,
    betrag      NUMBER(10,2),
    erstellt_am TIMESTAMP      DEFAULT SYSTIMESTAMP NOT NULL
);
