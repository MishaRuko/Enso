# --- TypeScript / Next.js ---

format-ts:
	cd frontend/designer-next && pnpm format

lint-ts:
	cd frontend/designer-next && pnpm lint

check-ts:
	cd frontend/designer-next && pnpm check

build:
	cd frontend/designer-next && pnpm build

# --- Python ---

format-py:
	uvx ruff format backend/

lint-py:
	uvx ruff check --fix backend/

check-py:
	uvx ruff check backend/

# --- All ---

format: format-ts format-py

lint: lint-ts lint-py

check: check-ts check-py

# --- Infrastructure ---

install:
	uv sync
	cd frontend/designer-next && pnpm install
	git config core.hooksPath .hooks
	$(MAKE) supabase-init

supabase-init:
	@which supabase > /dev/null 2>&1 || (echo "ERROR: supabase CLI not found. Install: brew install supabase/tap/supabase" && exit 1)
	@[ -d supabase ] && echo "supabase already initialized" || supabase init

db-start:
	supabase start

db-stop:
	supabase stop

migrate:
	supabase db push --local

dev:
	tilt up

# Run backend + frontend simultaneously without Tilt or Supabase.
# Ctrl-C stops both processes.
dev-simple:
	bash run.sh

dev-down:
	tilt down
	lsof -ti:8100,3000 | xargs kill -9 2>/dev/null || true

.PHONY: format-ts lint-ts check-ts build format-py lint-py check-py format lint check install dev dev-simple dev-down supabase-init db-start db-stop migrate
