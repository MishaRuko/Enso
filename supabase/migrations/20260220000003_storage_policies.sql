-- Storage bucket + permissive policies for local dev
INSERT INTO storage.buckets (id, name, public)
VALUES ('floorplans', 'floorplans', true)
ON CONFLICT (id) DO NOTHING;

-- Allow anyone to upload to floorplans bucket
CREATE POLICY "Allow public uploads" ON storage.objects
  FOR INSERT TO anon, authenticated
  WITH CHECK (bucket_id = 'floorplans');

-- Allow anyone to read from floorplans bucket
CREATE POLICY "Allow public reads" ON storage.objects
  FOR SELECT TO anon, authenticated
  USING (bucket_id = 'floorplans');
