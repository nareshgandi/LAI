-- Week 1 Session 1 PostgreSQL lab: roles and sample data.
-- Runs automatically inside bankdb on the container's first start.
-- Lab-only passwords. Never reuse them anywhere real.

-- 1. The application that will cause the incident
CREATE ROLE app_user LOGIN PASSWORD 'app_pw';

-- 2. The agent's eyes: can SEE everything, can CHANGE nothing
CREATE ROLE agent_ro LOGIN PASSWORD 'agent_ro_pw';
GRANT pg_monitor TO agent_ro;                                        -- full pg_stat_activity, pg_locks
ALTER ROLE agent_ro SET default_transaction_read_only = on;          -- no writes, ever
ALTER ROLE agent_ro SET statement_timeout = '5s';                    -- a diagnostic query never hangs
ALTER ROLE agent_ro SET lock_timeout = '1s';                         -- never queue behind the incident
ALTER ROLE agent_ro SET idle_in_transaction_session_timeout = '30s'; -- never become the incident

-- 3. The agent's hands: separate role, used ONLY after the guard and a human approve
CREATE ROLE agent_exec LOGIN PASSWORD 'agent_exec_pw';
GRANT pg_signal_backend TO agent_exec;   -- may cancel/terminate non-superuser backends; nothing else
ALTER ROLE agent_exec SET statement_timeout = '5s';

-- 4. Sample data
CREATE TABLE accounts (
    id      int PRIMARY KEY,
    owner   text          NOT NULL,
    balance numeric(12,2) NOT NULL
);
INSERT INTO accounts SELECT g, 'customer_' || g, 10000 FROM generate_series(1, 100) g;
ALTER TABLE accounts OWNER TO app_user;
