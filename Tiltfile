local_resource(
    "kill-ports",
    cmd="lsof -ti:8100,3000 | xargs kill -9 2>/dev/null || true",
    labels=["setup"],
)

local_resource(
    "db-migrate",
    cmd="supabase db push --local",
    deps=["supabase/migrations"],
    resource_deps=["kill-ports"],
    labels=["infra"],
)

local_resource(
    "backend",
    serve_cmd="cd backend && exec uv run --project ../ uvicorn src.main:app --reload --host 0.0.0.0 --port 8100",
    resource_deps=["kill-ports", "db-migrate"],
    links=["http://localhost:8100/health"],
    labels=["app"],
)

local_resource(
    "frontend",
    serve_cmd="cd frontend/designer-next && exec pnpm dev",
    resource_deps=["kill-ports"],
    links=["http://localhost:3000"],
    labels=["app"],
)
