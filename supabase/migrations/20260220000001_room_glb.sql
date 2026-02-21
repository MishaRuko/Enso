-- Add room GLB URL column for Trellis-generated room 3D model
alter table design_sessions add column if not exists room_glb_url text;
