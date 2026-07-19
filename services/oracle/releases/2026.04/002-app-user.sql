--liquibase formatted sql

-- changeset christian:003-create-app-user
-- comment: App user sdlc_app — the only user the Python API connects as (ADR-002)
-- runOnChange: false
CREATE USER sdlc_app IDENTIFIED BY SdlcApp2026;

-- rollback DROP USER sdlc_app CASCADE;

-- changeset christian:004-grant-app-user-session
-- comment: Minimal privilege — login only
-- runOnChange: false
GRANT CREATE SESSION TO sdlc_app;

-- rollback REVOKE CREATE SESSION FROM sdlc_app;

-- changeset christian:005-grant-app-user-dml
-- comment: DML rights on all SDLC tables — extend this changeset as new tables are added
-- runOnChange: false
GRANT SELECT, INSERT, UPDATE, DELETE ON sdlc_demo TO sdlc_app;

-- rollback REVOKE SELECT, INSERT, UPDATE, DELETE ON sdlc_demo FROM sdlc_app;
