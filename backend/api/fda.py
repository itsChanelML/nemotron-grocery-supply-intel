# backend/api/fda.py
# FDA OpenFDA food enforcement recall proxy
# Powers the Safety Agent with live federal recall data
#
# Free API — no key required for 40 req/min
# Register at open.fda.gov for 240 req/min

import os
import httpx
from fastapi import APIRouter, Query
from datetime import datetime

router = APIRouter()

FDA_BASE    = os.getenv("FDA_API_BASE_URL", "https://api.fda.gov")
FDA_API_KEY = os.getenv("FDA_API_KEY", "")


@router.get("")
async def get_fda_recalls(
    category: str = Query(default="", description="Filter by product keyword"),
    limit: int    = Query(default=10, le=25),
    status: str   = Query(default="ongoing"),
):
    """
    Fetch active food enforcement recalls from OpenFDA.
    Cross-referenced by Safety Agent against incoming BOL lot numbers.
    """
    search = f'status:"{status}"'
    if category:
        search += f'+AND+product_description:"{category}"'

    params = {
        "search": search,
        "limit": limit,
        "sort": "recall_initiation_date:desc",
    }
    if FDA_API_KEY:
        params["api_key"] = FDA_API_KEY

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{FDA_BASE}/food/enforcement.json",
                params=params,
                headers={"User-Agent": "Orchaid/1.0 (nemotron-grocery-supply-intel)"},
            )
            if r.status_code == 404:
                return {"recalls": [], "total": 0, "source": "OpenFDA"}
            r.raise_for_status()
            data = r.json()

    except Exception as e:
        return {"error": str(e), "recalls": [], "source": "OpenFDA"}

    recalls = [
        {
            "recall_number":      rec.get("recall_number"),
            "status":             rec.get("status"),
            "classification":     rec.get("classification"),
            "product":            rec.get("product_description"),
            "reason":             rec.get("reason_for_recall"),
            "vendor":             rec.get("recalling_firm"),
            "distribution":       rec.get("distribution_pattern"),
            "lot_numbers":        rec.get("code_info"),
            "quantity":           rec.get("product_quantity"),
            "recall_date":        rec.get("recall_initiation_date"),
            "termination_date":   rec.get("termination_date_initiated"),
        }
        for rec in data.get("results", [])
    ]

    return {
        "recalls":    recalls,
        "total":      data.get("meta", {}).get("results", {}).get("total", len(recalls)),
        "source":     "OpenFDA — api.fda.gov/food/enforcement",
        "fetched_at": datetime.utcnow().isoformat() + "Z",
    }
