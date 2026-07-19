--liquibase formatted sql

-- changeset christian:001-create-demo-table
-- comment: Initial demo table — proves the Liquibase pipeline works end-to-end
-- runOnChange: false
CREATE TABLE sdlc_demo (
    id          NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR2(100)   NOT NULL,
    description VARCHAR2(500),
    created_at  TIMESTAMP       DEFAULT SYSTIMESTAMP NOT NULL
);

-- rollback DROP TABLE sdlc_demo;

-- changeset christian:002-seed-demo-data
-- comment: Seed one row to verify SELECT works after deploy
-- runOnChange: false
INSERT INTO sdlc_demo (name, description)
VALUES ('Hello from Liquibase', 'First changeset applied via SQLcl — SDLC reference stack');

-- rollback DELETE FROM sdlc_demo WHERE name = 'Hello from Liquibase';
