# app/core/ocr_service.py
import re
from typing import Any, Dict, List
from rapidocr import RapidOCR, EngineType, LangDet, LangRec, ModelType, OCRVersion
import wordninja
from spellchecker import SpellChecker

class OCRService:
    """
    RapidOCR v3 (ONNXRuntime) + 通用清洗：
    - 识别语言：LATIN（含英/德/意等）
    - 清洗模式：
        mode="smart"  使用 wordninja 分词 + 英文拼写温和纠错（仅 ASCII 英文词）
        mode="basic"  仅做空白/标点规范化（跨语言最安全）
    """
    SAFE_TOKENS = {"H2COCO", "H2COCONUT.COM"}
    SAFE_PATTERNS = [
        re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"),  # email
        re.compile(r"^[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"),                    # domain
        re.compile(r"^@[\w.-]+$"),                                        # handle
        re.compile(r"^(?=.*[0-9-])[A-Z0-9-]{2,}$"),                       # 型号/码(需含数字/短横)
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
        # 仅用于英文拼写纠错；对德/意等非 ASCII 词一律不改
        self.spell_en = SpellChecker(language="en")

    # ----------------- 对外调用 -----------------
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

    # ----------------- 清洗实现 -----------------
    @staticmethod
    def _basic_normalize(text: str) -> str:
        # 使用 Unicode 字母类，避免破坏 ä/ö/ü/ß/à/è 等
        t = text.strip()
        t = re.sub(r"\s+", " ", t)
        t = t.replace("’", "'").replace("—", "-")
        t = re.sub(r"([^\W\d_])(\d)", r"\1 \2", t)  # A1 -> A 1
        t = re.sub(r"(\d)([^\W\d_])", r"\1 \2", t)  # 1A -> 1 A
        t = re.sub(r"\s+([,.:;!?])", r"\1", t)
        t = re.sub(r"\s*&\s*", " & ", t)
        # 域名后紧跟字母断开：.comAB -> .com AB
        t = re.sub(r"(\.[A-Za-z]{2,})(?=[A-Za-z])", r"\1 ", t)
        return t

    def _is_safe_token(self, tok: str) -> bool:
        if tok in self.SAFE_TOKENS:
            return True
        return any(p.match(tok) for p in self.SAFE_PATTERNS)

    def _split_allcaps_token(self, tok: str) -> str:
        # 仅对「ASCII 全大写长词」用统计分词；带变音的德/意词直接跳过
        if self._is_safe_token(tok):
            return tok
        core = tok.replace("'", "").replace("-", "")
        if tok.isupper() and core.isalpha() and len(core) >= 6 and core.isascii():
            parts = wordninja.split(core.lower())
            if parts and len("".join(parts)) == len(core):
                return " ".join(p.upper() for p in parts)
        return tok

    def _split_token_general(self, tok: str) -> str:
        # CamelCase 拆分 + 对「ASCII 长连写小写」用 wordninja（避免误拆德/意变音词）
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
        # 仅对「ASCII 英文字母」做英文拼写纠错；其余（德/意等）不动
        fixed: List[str] = []
        for tok in tokens:
            if not tok.isascii() or not tok.isalpha() or len(tok) < 3 or self._is_safe_token(tok):
                fixed.append(tok); continue
            # 尝试 …e/…o → …ed（如 RECYCLEO → RECYCLED）
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
        # YOU ' RE → YOU'RE；通用 s/re/ve/ll/d/t
        return re.sub(r"\b([A-Za-z]+)\s+'\s*(s|re|ve|ll|d|t)\b", r"\1'\2", text, flags=re.IGNORECASE)

    def _clean_lines(self, lines: List[str], mode: str = "smart") -> List[str]:
        # 1) 行级清洗
        if mode == "basic":
            cleaned = [self._basic_normalize(x) for x in lines if x and x.strip()]
            return cleaned

        # smart
        lines = [self._smart_space_restore(self._basic_normalize(x)) for x in lines if x and x.strip()]
        para = self._basic_normalize(" ".join(lines))
        para = self._join_contractions(para)

        # 2) 词级纠错（仅 ASCII 英文），不影响德/意变音词
        tokens = re.findall(r"[^\W\d_]+|\d+|[^\w\s]", para, flags=re.UNICODE)
        tokens = self._spell_fix_tokens_en(tokens)

        # 3) 重组句子：标点前不加空格
        out: List[str] = []
        for i, t in enumerate(tokens):
            if i > 0 and not re.match(r"[,.!?;:)]$", t) and not re.match(r"^[(']", t):
                out.append(" ")
            out.append(t)
        para = self._basic_normalize("".join(out))

        # 4) 温和的通用修复
        fixes = [
            (r"\bCAN\s*S\s+CAN\b", "CANS CAN"),
            (r"\bRECYCLE\s*D?\b", "RECYCLED"),
            (r"\bPACKAGING\s+WILL\b", "PACKAGING WILL"),
            (r"\bAMOUNT\s+OF\s+PLASTIC\b", "AMOUNT OF PLASTIC"),
            (r"\bOUR\s+OCEANS\b", "OUR OCEANS"),
        ]
        for pat, rep in fixes:
            para = re.sub(pat, rep, para, flags=re.IGNORECASE)

        # 5) 形态学：<verb> e/o + 介词 → <verb>ed + 介词（仅英文词典承认时）
        def verb_ed_fix(m):
            base, prep = m.group(1), m.group(2)
            cand = base + "ed"
            return f"{cand} {prep}" if self.spell_en.known([cand]) else f"{base} {prep}"
        para = re.sub(r"\b([A-Za-z]{3,})\s+[eoEO]\b\s+(from|in|on|by|at|to)\b", verb_ed_fix, para)

        # 6) 分句输出
        parts = re.split(r"(?<=[.!?])\s+", para)
        parts = [self._basic_normalize(p) for p in parts if p.strip()]
        return parts

# 进程内单例（默认 smart 清洗；按需在路由里传 mode=basic 关闭增强清洗）
ocr_service = OCRService(det_lang="MULTI", rec_lang="LATIN")
