-- Add columns required by Gurobi placement pipeline
ALTER TABLE design_sessions ADD COLUMN IF NOT EXISTS grid_data jsonb;
ALTER TABLE design_sessions ADD COLUMN IF NOT EXISTS furniture_specs jsonb;
ALTER TABLE design_sessions ADD COLUMN IF NOT EXISTS search_queries jsonb;
