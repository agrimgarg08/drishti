-- Initial schema for Yamuna Monitor

-- Sensors
CREATE TABLE IF NOT EXISTS sensors (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    type TEXT DEFAULT 'water',
    last_service TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
);

-- Readings (time-series)
CREATE TABLE IF NOT EXISTS readings (
    id BIGSERIAL PRIMARY KEY,
    sensor_id INTEGER NOT NULL REFERENCES sensors(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    pH DOUBLE PRECISION,
    DO2 DOUBLE PRECISION,
    BOD DOUBLE PRECISION,
    COD DOUBLE PRECISION,
    turbidity DOUBLE PRECISION,
    ammonia DOUBLE PRECISION,
    temperature DOUBLE PRECISION,
    conductivity DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS idx_readings_sensor_ts ON readings (sensor_id, timestamp DESC);

-- Alerts
CREATE TABLE IF NOT EXISTS alerts (
    id BIGSERIAL PRIMARY KEY,
    sensor_id INTEGER NOT NULL REFERENCES sensors(id) ON DELETE CASCADE,
    severity TEXT DEFAULT 'medium',
    message TEXT,
    timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    resolved BOOLEAN DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_alerts_resolved ON alerts (resolved);

-- Issues
CREATE TABLE IF NOT EXISTS issues (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'open',
    created_by TEXT DEFAULT 'anonymous',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
);

-- Useful views or helpers could go here later
