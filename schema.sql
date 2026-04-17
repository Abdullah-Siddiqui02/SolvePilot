-- ================================================
--  InterviewIQ – Database Schema
--  Run this file once to set up your MySQL tables.
--  Command:  mysql -u root -p < schema.sql
-- ================================================

CREATE DATABASE IF NOT EXISTS interview_prep1;
USE interview_prep1;


-- ──────────────────────────────────────────────
--  Users Table
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(100)  NOT NULL UNIQUE,
    password    VARCHAR(255)  NOT NULL,           -- stores werkzeug hashed passwords
    created_at  TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);


-- ──────────────────────────────────────────────
--  Questions Table
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS questions (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT           NOT NULL,
    title       VARCHAR(255)  NOT NULL,
    topic       VARCHAR(100)  NOT NULL,
    difficulty  VARCHAR(20)   NOT NULL,           -- Easy / Medium / Hard
    created_at  TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
);
