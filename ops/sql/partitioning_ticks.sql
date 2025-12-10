-- Declarative partitioning template for tick data
-- Adjust table/column names to your schema (example: ticks table with created_at timestamp)

-- Parent table (must already exist). Example:
-- CREATE TABLE IF NOT EXISTS ticks (
--   id BIGSERIAL PRIMARY KEY,
--   created_at TIMESTAMPTZ NOT NULL,
--   instrument_token BIGINT NOT NULL,
--   ltp NUMERIC,
--   volume BIGINT,
--   payload JSONB
-- ) PARTITION BY RANGE (created_at);

-- Create monthly partitions for 2025
DO $$
DECLARE
    m INT;
    start_date DATE;
    end_date DATE;
    part_name TEXT;
BEGIN
    FOR m IN 1..12 LOOP
        start_date := make_date(2025, m, 1);
        end_date := (start_date + INTERVAL '1 month')::date;
        part_name := format('ticks_%s', to_char(start_date, 'YYYY_MM'));
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF ticks FOR VALUES FROM (%L) TO (%L);',
            part_name, start_date, end_date
        );
        EXECUTE format('CREATE INDEX IF NOT EXISTS %I_on_token ON %I (instrument_token);', part_name || '_token', part_name);
    END LOOP;
END $$;

-- Example retention/archival step: detach old partitions and move to cold storage
-- ALTER TABLE ticks DETACH PARTITION ticks_2024_12;
