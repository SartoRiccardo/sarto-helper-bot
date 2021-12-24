-- base tables
DROP TABLE IF EXISTS config;
CREATE TABLE config(
    name VARCHAR(255) NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY (name)
);


-- feeds
DROP TABLE IF EXISTS feeds;
CREATE TABLE feeds(
    id SERIAL,
    owner BIGINT NOT NULL
);


-- reditor
DROP TABLE IF EXISTS rdt_videos;
DROP TABLE IF EXISTS rdt_threads;
CREATE TABLE rdt_threads(
    id VARCHAR(6) NOT NULL,
    date_added DATE NOT NULL,
    chosen BOOLEAN NOT NULL DEFAULT FALSE,
    message BIGINT NOT NULL,
    msg_index INT NOT NULL,
    PRIMARY KEY (id)
);
CREATE TABLE rdt_videos(
    exported BOOLEAN NOT NULL DEFAULT FALSE,
    thumbnail TEXT,
    title TEXT,
    url TEXT,
    thread VARCHAR(6) NOT NULL,
    PRIMARY KEY (thread),
    FOREIGN KEY (thread) REFERENCES rdt_threads(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);
