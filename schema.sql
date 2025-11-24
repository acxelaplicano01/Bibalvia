-- Tabla: Zona
CREATE TABLE "Zona" (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL,
    geopoligono JSONB NOT NULL
);

-- Tabla: Sector
CREATE TABLE "Sector" (
    id SERIAL PRIMARY KEY,
    latitud NUMERIC(10,8) NOT NULL,
    longitud NUMERIC(11,8) NOT NULL,
    nombre_sector VARCHAR(100) UNIQUE,
    CONSTRAINT sector_latitud_check CHECK (latitud >= -90 AND latitud <= 90),
    CONSTRAINT sector_longitud_check CHECK (longitud >= -180 AND longitud <= 180)
);

CREATE INDEX idx_sector_lat_long ON "Sector"(latitud, longitud);

-- Relación ManyToMany: Sector - Zona
CREATE TABLE "Sector_zonas" (
    id SERIAL PRIMARY KEY,
    sector_id INTEGER NOT NULL REFERENCES "Sector"(id) ON DELETE CASCADE,
    zona_id INTEGER NOT NULL REFERENCES "Zona"(id) ON DELETE CASCADE,
    UNIQUE(sector_id, zona_id)
);

-- Tabla: Bivalvo
CREATE TABLE "Bivalvo" (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(100) NOT NULL
);

CREATE INDEX idx_bivalvo_tipo ON "Bivalvo"(tipo);

---------------------------------------------------------
-- Historiales (todas tienen sector_id y marca_tiempo)
---------------------------------------------------------

-- Temperatura
CREATE TABLE "HistorialTemperatura" (
    id SERIAL PRIMARY KEY,
    sector_id INTEGER NOT NULL REFERENCES "Sector"(id) ON DELETE CASCADE,
    valor NUMERIC(5,2) NOT NULL,
    marca_tiempo TIMESTAMP NOT NULL,
    CONSTRAINT temp_val_check CHECK (valor >= -50 AND valor <= 100)
);
CREATE INDEX idx_temp_sector_fecha ON "HistorialTemperatura"(sector_id, marca_tiempo DESC);

-- Oxígeno
CREATE TABLE "HistorialOxigeno" (
    id SERIAL PRIMARY KEY,
    sector_id INTEGER NOT NULL REFERENCES "Sector"(id) ON DELETE CASCADE,
    valor NUMERIC(5,2) NOT NULL,
    marca_tiempo TIMESTAMP NOT NULL,
    CONSTRAINT oxi_val_check CHECK (valor >= -50 AND valor <= 100)
);
CREATE INDEX idx_oxi_sector_fecha ON "HistorialOxigeno"(sector_id, marca_tiempo DESC);

-- Salinidad
CREATE TABLE "HistorialSalinidad" (
    id SERIAL PRIMARY KEY,
    sector_id INTEGER NOT NULL REFERENCES "Sector"(id) ON DELETE CASCADE,
    valor NUMERIC(4,2) NOT NULL,
    marca_tiempo TIMESTAMP NOT NULL
);
CREATE INDEX idx_sal_sector_fecha ON "HistorialSalinidad"(sector_id, marca_tiempo DESC);

-- pH
CREATE TABLE "HistorialPh" (
    id SERIAL PRIMARY KEY,
    sector_id INTEGER NOT NULL REFERENCES "Sector"(id) ON DELETE CASCADE,
    valor NUMERIC(4,2) NOT NULL,
    marca_tiempo TIMESTAMP NOT NULL,
    CONSTRAINT ph_val_check CHECK (valor >= 0 AND valor <= 14)
);
CREATE INDEX idx_ph_sector_fecha ON "HistorialPh"(sector_id, marca_tiempo DESC);

-- Turbidez
CREATE TABLE "HistorialTurbidez" (
    id SERIAL PRIMARY KEY,
    sector_id INTEGER NOT NULL REFERENCES "Sector"(id) ON DELETE CASCADE,
    valor NUMERIC(6,2) NOT NULL,
    marca_tiempo TIMESTAMP NOT NULL
);
CREATE INDEX idx_tur_sector_fecha ON "HistorialTurbidez"(sector_id, marca_tiempo DESC);

-- Humedad
CREATE TABLE "HistorialHumedad" (
    id SERIAL PRIMARY KEY,
    sector_id INTEGER NOT NULL REFERENCES "Sector"(id) ON DELETE CASCADE,
    valor NUMERIC(5,2) NOT NULL,
    marca_tiempo TIMESTAMP NOT NULL,
    CONSTRAINT hum_val_check CHECK (valor >= 0 AND valor <= 100)
);
CREATE INDEX idx_hum_sector_fecha ON "HistorialHumedad"(sector_id, marca_tiempo DESC);

-- Clasificación (Sector + Bivalvo + Fecha únicos)
CREATE TABLE "HistorialClasificacion" (
    id SERIAL PRIMARY KEY,
    sector_id INTEGER NOT NULL REFERENCES "Sector"(id) ON DELETE CASCADE,
    bivalvo_id INTEGER NOT NULL REFERENCES "Bivalvo"(id) ON DELETE CASCADE,
    marca_tiempo TIMESTAMP NOT NULL,
    CONSTRAINT unique_clasificacion UNIQUE(sector_id, bivalvo_id, marca_tiempo)
);
CREATE INDEX idx_clas_sector_fecha ON "HistorialClasificacion"(sector_id, marca_tiempo DESC);
CREATE INDEX idx_clas_bivalvo_fecha ON "HistorialClasificacion"(bivalvo_id, marca_tiempo DESC);
