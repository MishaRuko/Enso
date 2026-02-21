-- Add miro_board_url column for generated mood board links
alter table design_sessions add column if not exists miro_board_url text;
