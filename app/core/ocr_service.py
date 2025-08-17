# app/core/ocr_service.py
import re
from typing import Any, Dict, List
from rapidocr import RapidOCR, EngineType, LangDet, LangRec, ModelType, OCRVersion
import wordninja
from spellchecker import SpellChecker

class OCRService:
    """
    RapidOCR v3 (ONNXRuntime) + General Cleaning:
    - Recognition language: LATIN (including EN/DE/IT etc.)
    - Cleaning modes:
        mode="smart"  Use wordninja tokenization + mild English spell correction (ASCII English words only) Can be more aggressive, but may "over-correct".
        mode="basic"  Normalize whitespace/punctuation only (safest across languages)  Now set to default. Safer for short slogans / packaging text.
    """
    SAFE_TOKENS = {"H2COCO", "H2COCONUT.COM"}
    SAFE_PATTERNS = [
        re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"),  # email
        re.compile(r"^[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"),                    # domain
        re.compile(r"^@[\w.-]+$"),                                        # handle
        re.compile(r"^(?=.*[0-9-])[A-Z0-9-]{2,}$"),                       # Model/code (must contain numbers/hyphen)
    ]

    def __init__(self, det_lang: str = "MULTI", rec_lang: str = "LATIN") -> None:
        self.engine = RapidOCR(params={
            "Det.engine_type": EngineType.ONNXRUNTIME,
            "Det.lang_type":   getattr(LangDet, det_lang),
            "Det.model_type":  ModelType.MOBILE,
            "Det.ocr_version": OCRVersion.PPOCRV4,
            "Rec.engine_type": EngineType.ONNXRUNTIME,
            "Rec.lang_type":   getattr(LangRec, rec_lang),
            "Rec.model_type":  ModelType.MOBILE,
            "Rec.ocr_version": OCRVersion.PPOCRV5,
        })
        # Only used for English spell correction; DE/IT and other non-ASCII words are left unchanged

        self.spell_en = SpellChecker(language="en")

    #  External Call 
    def read(self, image_path: str, mode: str = "smart") -> Dict[str, Any]:
        r = self.engine(image_path)
        lines: List[str] = list(r.txts or [])
        scores: List[float] = [float(s) for s in (r.scores or [])]
        out: Dict[str, Any] = {
            "elapsed_sec": float(getattr(r, "elapse", 0.0) or 0.0),
            "lines": lines,
            "scores": scores,
            "full_text": "\n".join(lines),
        }
        cleaned = self._clean_lines(lines, mode=mode)
        out["cleaned_lines"] = cleaned
        out["cleaned_text"] = "\n".join(cleaned)
        out["clean_mode"] = mode
        return out

    # Cleaning Implementation
    @staticmethod
    def _basic_normalize(text: str) -> str:
        # Use Unicode letter classes to avoid breaking ä/ö/ü/ß/à/è etc.
        """
        Basic whitespace/punctuation normalization.
        NOTE: Do NOT split alphanumeric tokens anymore
        (we removed A1->A 1, CO2->CO 2 rules) to avoid
        breaking chemical formulas or brand names like H2.
        """
        t = text.strip()
        t = re.sub(r"\s+", " ", t)
        t = t.replace("’", "'").replace("—", "-")
       # Removed: splitting letter+digit → caused "H2" → "H 2"
       # t = re.sub(r"([^\W\d_])(\d)", r"\1 \2", t)  # A1 -> A 1
       # t = re.sub(r"(\d)([^\W\d_])", r"\1 \2", t)  # 1A -> 1 A
        t = re.sub(r"\s+([,.:;!?])", r"\1", t)
        t = re.sub(r"\s*&\s*", " & ", t)
        # Break after domain if followed by letters: .comAB -> .com AB
        t = re.sub(r"(\.[A-Za-z]{2,})(?=[A-Za-z])", r"\1 ", t)
        return t

    def _is_safe_token(self, tok: str) -> bool:
        if tok in self.SAFE_TOKENS:
            return True
        return any(p.match(tok) for p in self.SAFE_PATTERNS)

    def _split_allcaps_token(self, tok: str) -> str:
        # Apply statistical tokenization only for "ASCII ALL-CAPS long words"; skip DE/IT words with umlauts
        if self._is_safe_token(tok):
            return tok
        core = tok.replace("'", "").replace("-", "")
        if tok.isupper() and core.isalpha() and len(core) >= 6 and core.isascii():
            parts = wordninja.split(core.lower())
            if parts and len("".join(parts)) == len(core):
                return " ".join(p.upper() for p in parts)
        return tok

    def _split_token_general(self, tok: str) -> str:
        # Split CamelCase + use wordninja for "ASCII long lowercase runs" (avoid splitting DE/IT umlaut words)
        if self._is_safe_token(tok):
            return tok
        camel = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", tok)
        segs, out = camel.split(), []
        for seg in segs:
            core = seg.replace("'", "").replace("-", "")
            if core.isascii() and core.isalpha() and len(core) >= 8:
                w = wordninja.split(core.lower())
                if w and len("".join(w)) == len(core):
                    if seg.isupper():
                        out.append(" ".join(p.upper() for p in w))
                    else:
                        out.append(" ".join(p.capitalize() for p in w))
                    continue
            out.append(seg)
        return " ".join(out)

    def _smart_space_restore(self, line: str) -> str:
        toks = line.split()
        out = []
        for t in toks:
            m = re.match(r"^([A-Za-zÀ-ÖØ-öø-ÿ&'\-0-9.]+)([.,!?]*)$", t)
            core, punct = (m.group(1), m.group(2)) if m else (t, "")
            core = self._split_allcaps_token(core)
            core = self._split_token_general(core)
            out.append(core + punct)
        s = " ".join(out)
        s = self._basic_normalize(s)
        s = re.sub(r"(\w)-\s+(\w)", r"\1- \2", s)  # plants-\ncom → plants- com
        return s

    def _preserve_case(self, src: str, dst: str) -> str:
        if src.isupper(): return dst.upper()
        if src.istitle(): return dst.capitalize()
        return dst

    def _spell_fix_tokens_en(self, tokens: List[str]) -> List[str]:
        # Apply English spell correction only to "ASCII letters"; leave DE/IT words unchanged
        fixed: List[str] = []
        for tok in tokens:
            if not tok.isascii() or not tok.isalpha() or len(tok) < 3 or self._is_safe_token(tok):
                fixed.append(tok); continue
            # Try …e/…o → …ed (e.g. RECYCLEO → RECYCLED)
            if tok[-1] in {"e","E","o","O"}:
                cand = tok[:-1] + "ed"
                if self.spell_en.known([cand.lower()]):
                    fixed.append(self._preserve_case(tok, cand)); continue
            if tok.lower() in self.spell_en:
                fixed.append(tok); continue
            corr = self.spell_en.correction(tok.lower())
            fixed.append(self._preserve_case(tok, corr) if corr else tok)
        return fixed

    def _join_contractions(self, text: str) -> str:
        # Normalize YOU ' RE → YOU'RE; also general s/re/ve/ll/d/t cases
        return re.sub(r"\b([A-Za-z]+)\s+'\s*(s|re|ve|ll|d|t)\b", r"\1'\2", text, flags=re.IGNORECASE)

    def _clean_lines(self, lines: List[str], mode: str = "basic") -> List[str]:
        # 1) Line-level cleaning
        if mode == "basic":
            cleaned = [self._basic_normalize(x) for x in lines if x and x.strip()]
            return cleaned

        # smart
        lines = [self._smart_space_restore(self._basic_normalize(x)) for x in lines if x and x.strip()]
        para = self._basic_normalize(" ".join(lines))
        para = self._join_contractions(para)

        # 2) Word-level correction (ASCII English only), no effect on DE/IT umlaut words
        tokens = re.findall(r"[^\W\d_]+|\d+|[^\w\s]", para, flags=re.UNICODE)
        tokens = self._spell_fix_tokens_en(tokens)

        # 3) Rebuild sentence: no space before punctuation
        out: List[str] = []
        for i, t in enumerate(tokens):
            if i > 0 and not re.match(r"[,.!?;:)]$", t) and not re.match(r"^[(']", t):
                out.append(" ")
            out.append(t)
        para = self._basic_normalize("".join(out))

        # 4) Mild general fixes
        fixes = [
            (r"\bCAN\s*S\s+CAN\b", "CANS CAN"),
            (r"\bRECYCLE\s*D?\b", "RECYCLED"),
            (r"\bPACKAGING\s+WILL\b", "PACKAGING WILL"),
            (r"\bAMOUNT\s+OF\s+PLASTIC\b", "AMOUNT OF PLASTIC"),
            (r"\bOUR\s+OCEANS\b", "OUR OCEANS"),
        ]
        for pat, rep in fixes:
            para = re.sub(pat, rep, para, flags=re.IGNORECASE)

        # 5) Morphology: <verb> e/o + preposition → <verb>ed + preposition (only if accepted by English dict)
        def verb_ed_fix(m):
            base, prep = m.group(1), m.group(2)
            cand = base + "ed"
            return f"{cand} {prep}" if self.spell_en.known([cand]) else f"{base} {prep}"
        para = re.sub(r"\b([A-Za-z]{3,})\s+[eoEO]\b\s+(from|in|on|by|at|to)\b", verb_ed_fix, para)

        # 6) Sentence segmentation output
        #parts = re.split(r"(?<=[.!?])\s+", para)
        #parts = [self._basic_normalize(p) for p in parts if p.strip()]
        #return parts
        return [para] if para.strip() else []

# In-process singleton (default = smart cleaning; switch to mode=basic in routes to disable enhanced cleaning)
ocr_service = OCRService(det_lang="MULTI", rec_lang="LATIN")
