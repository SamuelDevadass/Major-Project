from fastapi import APIRouter
from fastapi.responses import JSONResponse
from services.company_service import get_companies_list

router = APIRouter(tags=["Companies"])


@router.get("/companies", summary="Get all companies for dropdown")
def get_companies():
    """
    Returns list of { ticker, company_name, sector }.
    Frontend displays company_name, sends ticker to POST /analyze.
    """
    return JSONResponse(content=get_companies_list())