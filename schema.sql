CREATE DATABASE IF NOT EXISTS interview_prep1;
USE interview_prep1;


CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(100)  NOT NULL UNIQUE,
    password    VARCHAR(255)  NOT NULL,
    created_at  TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS questions (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT           NOT NULL,
    title       VARCHAR(255)  NOT NULL,
    topic       VARCHAR(100)  NOT NULL,
    difficulty  VARCHAR(20)   NOT NULL,           
    created_at  TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS global_problems (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    platform            VARCHAR(50)   NOT NULL,           
    platform_problem_id VARCHAR(100)  NOT NULL,           
    title               VARCHAR(255)  NOT NULL,
    difficulty          VARCHAR(50),                      
    tags                VARCHAR(255),                     
    url                 VARCHAR(555)  NOT NULL,
    description         TEXT,                             
    created_at          TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(platform, platform_problem_id)
);

-- User Submissions Table (To track code executions)

CREATE TABLE IF NOT EXISTS user_submissions (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    user_id             INT           NOT NULL,
    problem_id          INT,                              
    language            VARCHAR(50)   NOT NULL,
    code                TEXT          NOT NULL,
    status              VARCHAR(50)   NOT NULL,           
    execution_time_ms   FLOAT,
    memory_kb           FLOAT,
    created_at          TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (problem_id) REFERENCES global_problems(id) ON DELETE SET NULL
);

-- User Collection Table (To track problems added by user from the bank)
CREATE TABLE IF NOT EXISTS user_collection (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT           NOT NULL,
    problem_id  INT           NOT NULL,
    status      VARCHAR(20)   DEFAULT 'added', -- 'added' or 'solved'
    created_at  TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (problem_id) REFERENCES global_problems(id) ON DELETE CASCADE,
    UNIQUE(user_id, problem_id)
);
