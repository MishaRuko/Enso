-- Design sessions: one per user consultation
create table if not exists design_sessions (
  id text primary key,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  status text not null default 'pending',  -- pending, consulting, processing, complete
  client_name text,
  client_email text,
  preferences jsonb not null default '{}'::jsonb,  -- style, budget, colors, lifestyle
  floorplan_url text,
  room_data jsonb,  -- Gemini-parsed room dimensions JSON
  furniture_list jsonb not null default '[]'::jsonb,  -- selected furniture items
  placements jsonb,  -- Gemini-generated placement coordinates
  total_price numeric(10,2),
  payment_link text,
  payment_status text default 'unpaid'
);

-- Pipeline jobs: one per pipeline execution
create table if not exists design_jobs (
  id text primary key,
  session_id text not null references design_sessions(id) on delete cascade,
  created_at timestamptz not null default now(),
  completed_at timestamptz,
  status text not null default 'pending',  -- pending, running, completed, failed
  phase text not null default 'init',  -- floorplan, furniture_search, model_gen, placement, render
  trace jsonb not null default '[]'::jsonb,
  result jsonb
);

-- Furniture catalog: cached furniture data from scraped retailers
create table if not exists furniture_items (
  id text primary key,
  session_id text references design_sessions(id) on delete cascade,
  retailer text not null,  -- ikea, wayfair, zarahome
  name text not null,
  price numeric(10,2),
  currency text default 'EUR',
  dimensions jsonb,  -- { width_cm, depth_cm, height_cm }
  image_url text,
  product_url text,
  glb_url text,  -- 3D model URL (if available)
  category text,  -- sofa, table, lamp, etc.
  selected boolean default false,
  created_at timestamptz not null default now()
);

-- 3D models: generated or sourced GLB files
create table if not exists models_3d (
  id text primary key,
  furniture_item_id text references furniture_items(id) on delete cascade,
  source text not null,  -- ikea_glb, sketchfab, poly_pizza, trellis, hunyuan
  glb_storage_path text,  -- path in Supabase Storage
  glb_url text,
  generation_cost numeric(6,4),
  created_at timestamptz not null default now()
);

-- Indexes
create index if not exists design_jobs_session_idx on design_jobs (session_id);
create index if not exists design_jobs_status_idx on design_jobs (status);
create index if not exists furniture_items_session_idx on furniture_items (session_id);
create index if not exists furniture_items_selected_idx on furniture_items (session_id, selected);
