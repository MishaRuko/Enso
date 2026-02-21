from fastapi import FastAPI, HTTPException, Query

from app.ikea_client import get_3d_models, get_product_details, get_stock, search_products
from app.models import (
    FurnitureItem,
    FurnitureRequest,
    ModelFile,
    PipelineResponse,
    SearchResponse,
    StockInfo,
)
from app.pipeline import run_pipeline

app = FastAPI(title="IKEA Furniture API", version="1.0.0")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/search", response_model=SearchResponse)
async def search(query: str, limit: int = Query(default=24, ge=1, le=100)):
    try:
        items = await search_products(query, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"IKEA API error: {e}")
    return SearchResponse(query=query, items=items)


@app.get("/product/{item_code}", response_model=FurnitureItem)
async def product(item_code: str):
    try:
        result = await get_product_details(item_code)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"IKEA API error: {e}")
    if result is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return result


@app.get("/stock/{item_code}", response_model=StockInfo)
async def stock(item_code: str):
    if not item_code.isdigit():
        raise HTTPException(
            status_code=400,
            detail=f"Stock check only supports numeric item codes, got '{item_code}'",
        )
    try:
        return await get_stock(item_code)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"IKEA API error: {e}")


@app.get("/model/{item_code}", response_model=list[ModelFile])
async def model(item_code: str):
    try:
        return await get_3d_models(item_code)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"IKEA API error: {e}")


@app.post("/pipeline", response_model=PipelineResponse)
async def pipeline(request: FurnitureRequest):
    try:
        results = await run_pipeline(request.items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")
    return PipelineResponse(results=results)
