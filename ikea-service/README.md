# IKEA Furniture API

Dockerized FastAPI microservice that searches IKEA UK for furniture, fetches 3D models, and caches results in a vector database.

## Quick Start

```bash
# Local dev
cd ikea-service
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in credentials if needed
uvicorn app.main:app --port 8000

# Docker (full stack with Qdrant)
docker compose up --build
```

## API Endpoints

### `GET /search`

Search IKEA UK products by keyword.

| Param   | Type | Default | Description          |
|---------|------|---------|----------------------|
| `query` | str  | required | Search term         |
| `limit` | int  | 24      | Max results (1-100) |

```bash
curl "http://localhost:8000/search?query=sofa&limit=5"
```

### `GET /product/{item_code}`

Get full details for a single product.

```bash
curl http://localhost:8000/product/00263850
```

### `GET /model/{item_code}`

Get 3D model download URLs (GLB and USDZ) for a product.

```bash
curl http://localhost:8000/model/00263850
```

### `GET /stock/{item_code}`

Check stock availability across UK stores. Only works with numeric item codes.

```bash
curl http://localhost:8000/stock/00263850
```

### `POST /pipeline`

The main endpoint for the Enso platform. Takes a list of furniture queries, searches IKEA, fetches 3D models, and caches everything.

```bash
curl -X POST http://localhost:8000/pipeline \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"description": "white bookcase 80cm wide", "category": "bookcase", "dimensions": "80x28x202 cm"},
      {"description": "small wooden desk", "category": "desk"},
      {"description": "floor lamp", "category": "lighting"}
    ]
  }'
```

#### Request Body

```json
{
  "items": [
    {
      "description": "white bookcase 80cm wide",
      "category": "bookcase",
      "dimensions": "80x28x202 cm"
    }
  ]
}
```

| Field         | Type        | Required | Description                                    |
|---------------|-------------|----------|------------------------------------------------|
| `description` | string      | yes      | Natural language description of the furniture  |
| `category`    | string/null | no       | Furniture category (e.g. "sofa", "desk", "bookcase") |
| `dimensions`  | string/null | no       | Desired dimensions (e.g. "80x28x202 cm")       |

#### Response

```json
{
  "results": [
    {
      "query": {
        "description": "white bookcase 80cm wide",
        "category": "bookcase",
        "dimensions": "80x28x202 cm"
      },
      "source": "ikea_api",
      "item": {
        "item_code": "00263850",
        "name": "BILLY",
        "type_name": "Bookcase",
        "description": "BILLY Bookcase, 80x28x202 cm",
        "dimensions": "80x28x202 cm",
        "price": 55.0,
        "currency": "GBP",
        "image_url": "https://www.ikea.com/gb/en/images/...",
        "images": [
          {"url": "...", "alt": "...", "type": "MAIN_PRODUCT_IMAGE"}
        ],
        "buy_url": "https://www.ikea.com/gb/en/p/billy-bookcase-white-00263850/",
        "category": "Bookcases",
        "color": "white",
        "rating": 4.7,
        "rating_count": 249,
        "variants": [
          {
            "item_code": "40477340",
            "color": "black oak effect",
            "price": 70.0,
            "buy_url": "https://www.ikea.com/gb/en/p/..."
          }
        ],
        "model_files": [
          {
            "format": "glb_draco",
            "url": "https://web-api.ikea.com/dimma/assets/...",
            "source_url": "https://web-api.ikea.com/dimma/assets/..."
          }
        ]
      }
    }
  ]
}
```

| Field    | Description                                                    |
|----------|----------------------------------------------------------------|
| `source` | `"cache"` if returned from Qdrant, `"ikea_api"` if freshly fetched |
| `item`   | Full product data including images, variants, and 3D models. `null` if no match found. |

#### Pipeline Flow

1. Embeds the query using `all-MiniLM-L6-v2` sentence transformer
2. Searches Qdrant for a cached match (cosine similarity >= 0.85)
3. On cache hit: returns immediately with `source: "cache"`
4. On cache miss:
   - Searches IKEA API with the description + category
   - Fetches 3D model URLs (GLB) via the Rotera endpoint
   - Uploads GLB to DigitalOcean Spaces (if configured, otherwise uses IKEA CDN URLs)
   - Caches the result in Qdrant
   - Returns with `source: "ikea_api"`

## Environment Variables

| Variable          | Required | Description                          |
|-------------------|----------|--------------------------------------|
| `QDRANT_URL`      | no       | Qdrant server URL. Empty = in-memory |
| `DO_SPACES_KEY`   | no       | DigitalOcean Spaces access key       |
| `DO_SPACES_SECRET`| no       | DigitalOcean Spaces secret key       |
| `DO_SPACES_BUCKET`| no       | DO Spaces bucket name                |
| `DO_SPACES_REGION`| no       | DO Spaces region (e.g. `nyc3`)       |

## Demo

```bash
python demo.py              # runs all endpoints with "bookcase"
python demo.py "standing desk"  # custom search
```
