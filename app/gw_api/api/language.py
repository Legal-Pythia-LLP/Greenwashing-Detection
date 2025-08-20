# app/api/language.py
from fastapi import APIRouter, Response, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class LangBody(BaseModel):
    lang: Optional[str] = None
    language: Optional[str] = None

@router.post("/set-language")
async def set_language(
    request: Request,
    response: Response,
    lang: Optional[str] = None,        # query ?lang=
    language: Optional[str] = None     # query ?language=
):
    body_lang = None
    try:
        data = await request.json()
        if isinstance(data, dict):
            body_lang = data.get("lang") or data.get("language")
    except Exception:
        pass
    if body_lang is None:
        form = await request.form() if request.headers.get("content-type","").startswith("application/x-www-form-urlencoded") else None
        if form:
            body_lang = form.get("lang") or form.get("language")

    chosen = lang or language or body_lang
    if not chosen:
        raise HTTPException(status_code=422, detail="Missing 'lang'/'language' in query, form, or JSON")
    return {"ok": True, "language": chosen}
