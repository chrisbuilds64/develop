--liquibase formatted sql

-- changeset christian:006-create-code-chunks
-- comment: RAG table for PL/SQL vector embeddings — stores chunked source text + embeddings for semantic search
-- runOnChange: false
CREATE TABLE code_chunks (
    id           NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_owner VARCHAR2(128) NOT NULL,
    source_name  VARCHAR2(128) NOT NULL,
    source_type  VARCHAR2(32)  NOT NULL,
    chunk_seq    NUMBER        NOT NULL,
    chunk_text   CLOB          NOT NULL,
    embedding    VECTOR        NOT NULL,
    created_at   TIMESTAMP     DEFAULT SYSTIMESTAMP NOT NULL
);

-- rollback DROP TABLE code_chunks;

-- changeset christian:007-index-code-chunks-owner-name
-- comment: Lookup index for delete/upsert by object identity
-- runOnChange: false
CREATE INDEX idx_code_chunks_obj ON code_chunks (source_owner, source_name, source_type);

-- rollback DROP INDEX idx_code_chunks_obj;
