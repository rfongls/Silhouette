CREATE TABLE IF NOT EXISTS files (
    file_id INTEGER PRIMARY KEY,
    path TEXT UNIQUE,
    last_sha1 TEXT,
    last_mtime REAL,
    commit_sha TEXT
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    file_id INTEGER,
    start_line INT,
    end_line INT,
    FOREIGN KEY(file_id) REFERENCES files(file_id)
);

CREATE TABLE IF NOT EXISTS vectors (
    chunk_id TEXT PRIMARY KEY,
    dim INT,
    data BLOB,
    FOREIGN KEY(chunk_id) REFERENCES chunks(chunk_id)
);

CREATE INDEX IF NOT EXISTS idx_chunks_file_id ON chunks(file_id);
CREATE INDEX IF NOT EXISTS idx_vectors_chunk_id ON vectors(chunk_id);
