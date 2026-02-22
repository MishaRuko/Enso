"""IKEA product search, caching, and 3D model pipeline.

Adapted from Charlene's ikea-service microservice into direct function calls
within the backend, eliminating the need for a separate HTTP service.

Usage (from within the backend package):
    from ..tools.ikea.search import search_ikea_products, ikea_results_to_spec_updates

Submodules:
    models      — Pydantic schemas (FurnitureQuery, FurnitureItem, etc.)
    ikea_client — IKEA API wrapper (search, 3D models)
    vector_db   — Qdrant semantic cache
    storage     — DO Spaces GLB upload
    pipeline    — Orchestrator (cache → search → relevance → GLB → cache)
    search      — Adapter between our FurnitureItemSpec and the pipeline
"""
