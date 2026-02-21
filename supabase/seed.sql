-- Create storage buckets required by the application
INSERT INTO storage.buckets (id, name, public)
VALUES ('floorplans', 'floorplans', true)
ON CONFLICT (id) DO NOTHING;
