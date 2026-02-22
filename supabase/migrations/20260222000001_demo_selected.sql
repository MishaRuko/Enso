-- Add demo_selected flag for marking sessions to show in demo view
alter table design_sessions add column if not exists demo_selected boolean not null default false;
