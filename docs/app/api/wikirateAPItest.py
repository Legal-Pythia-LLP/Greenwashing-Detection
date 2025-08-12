# from fastapi import APIRouter, File, Form, HTTPException, UploadFile
# from typing import Annotated, Dict, Any
# from app.core.vector_store import embedding_model
# from app.config import WIKIRATE_API_KEY
# from app.core.tools import WikirateClient

# router = APIRouter()

# # 新增：Wikirate API测试端点
# @router.post("/testwikirate")
# async def test_wikirate_connection(company_name: str = Form(...)) -> Dict[str, Any]:
#     """Test Wikirate API connection and data retrieval"""
#     if not WIKIRATE_API_KEY:
#         return {
#             "status": "error",
#             "message": "Wikirate API key not configured"
#         }
    
#     try:
#         wikirate_client = WikirateClient(WIKIRATE_API_KEY)
        
#         # Test company search
#         company_data = wikirate_client.search_company(company_name)
        
#         if company_data:
#             # Test metrics retrieval
#             metrics_data = wikirate_client.get_company_metrics(company_name)
            
#             return {
#                 "status": "success",
#                 "company_found": True,
#                 "company_data": company_data,
#                 "metrics_available": len(metrics_data) if "error" not in metrics_data else 0,
#                 "sample_metrics": list(metrics_data.keys())[:5] if "error" not in metrics_data else []
#             }
#         else:
#             return {
#                 "status": "warning",
#                 "company_found": False,
#                 "message": f"Company '{company_name}' not found in Wikirate database"
#             }
            
#     except Exception as e:
#         return {
#             "status": "error",
#             "message": f"Error testing Wikirate connection: {str(e)}"
#         }

from fastapi import APIRouter, Form
from typing import Dict, Any
from app.config import WIKIRATE_API_KEY
from app.core.tools import WikirateClient

router = APIRouter()

@router.post("/testwikirate")
async def test_wikirate_connection(company_name: str = Form(...)) -> Dict[str, Any]:
    """Test Wikirate API connection and company metrics retrieval"""
    if not WIKIRATE_API_KEY:
        return {
            "status": "error",
            "message": "Wikirate API key not configured"
        }

    try:
        wikirate_client = WikirateClient(WIKIRATE_API_KEY)

        # ✅ 測試搜尋公司
        company_data = wikirate_client.search_company(company_name)

        if not company_data:
            return {
                "status": "not_found",
                "message": f"Company '{company_name}' not found in Wikirate"
            }

        # ✅ 測試抓指標（使用你 canvas 內的新版 get_company_metrics）
        metrics_data = wikirate_client.get_company_metrics(company_name)

        if "error" in metrics_data:
            return {
                "status": "partial_success",
                "message": f"Company found, but error fetching metrics: {metrics_data['error']}",
                "company_data": company_data
            }

        return {
            "status": "success",
            "company_found": True,
            "company_data": company_data,
            "metrics_count": len(metrics_data),
            "sample_metrics": list(metrics_data.keys())[:5]
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Exception during test: {str(e)}"
        }
