import json
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple

# 规则文件路径（按你的工程层级）
RULES_PATH = Path(__file__).resolve().parents[2] / "data_files" / "rules.json"

_SENTENCE_REGEX = re.compile(r'[^.!?;\n]+[.!?;\n]*', re.UNICODE)

def _compile_kw(kw: str, ignore_case: bool = True) -> re.Pattern:
    # 词边界匹配，兼容连字符/空格变体，如 net zero / net-zero
    # (?<!\w) 和 (?!\w) 避免命中 "Greenwich" 之类
    pattern = r'(?<!\w)' + re.escape(kw).replace(r'\ ', r'[-\s]?') + r'(?!\w)'
    return re.compile(pattern, re.I if ignore_case else 0)

def _compile_rx(rx: str, ignore_case: bool = True) -> re.Pattern:
    return re.compile(rx, re.I if ignore_case else 0)

class RuleEngine:
    def __init__(self, rules_path: Path = RULES_PATH):
        self.rules_path = Path(rules_path)
        if not self.rules_path.exists():
            raise FileNotFoundError(f"Rules file not found: {self.rules_path}")

        with open(self.rules_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        # 统一成内部规则列表：每条 {type, patterns, negations, whitelist, score, meta...}
        self.rules: List[Dict[str, Any]] = []
        if isinstance(raw, list):
            # 新版 schema：规则数组
            for idx, r in enumerate(raw):
                meta = {
                    "id": r.get("id", idx),
                    "name": r.get("name", []),
                    "source": r.get("source", ""),
                    "source_ref": r.get("source_ref", ""),
                    "note": r.get("note", "")
                }
                rr = r.get("rule", {}) or {}
                rtype = rr.get("type")
                ignore_case = bool(rr.get("ignore_case", True))
                neg = r.get("negations", []) or []
                white = r.get("whitelist", []) or []
                score = int(r.get("score", 1))
                if rtype == "keyword":
                    kws = rr.get("keywords", []) or []
                    patterns = [_compile_kw(k, ignore_case) for k in kws if k]
                    if patterns:
                        self.rules.append({
                            "type": "keyword",
                            "patterns": patterns,
                            "negations": neg,
                            "whitelist": white,
                            "score": score,
                            "meta": meta
                        })
                elif rtype == "regex":
                    rx = rr.get("regex", "")
                    if rx:
                        self.rules.append({
                            "type": "regex",
                            "patterns": [_compile_rx(rx, ignore_case)],
                            "negations": neg,
                            "whitelist": white,
                            "score": score,
                            "meta": meta
                        })
        elif isinstance(raw, dict) and ("keywords" in raw or "regex" in raw):
            # 旧版 schema：顶层 keywords/regex/negations/whitelist
            global_neg = raw.get("negations", []) or []
            global_white = raw.get("whitelist", []) or []
            for k in raw.get("keywords", []):
                term = (k.get("term") or "").strip()
                if not term:
                    continue
                self.rules.append({
                    "type": "keyword",
                    "patterns": [_compile_kw(term, True)],
                    "negations": list(global_neg),
                    "whitelist": list(global_white),
                    "score": int(k.get("weight", 1)),
                    "meta": {"id": k.get("id"), "name": ["Legacy", "Keyword"], "source": "", "source_ref": "", "note": k.get("note", "")}
                })
            for r in raw.get("regex", []):
                pat = (r.get("pattern") or "").strip()
                if not pat:
                    continue
                self.rules.append({
                    "type": "regex",
                    "patterns": [_compile_rx(pat, True)],
                    "negations": list(global_neg),
                    "whitelist": list(global_white),
                    "score": int(r.get("weight", 1)),
                    "meta": {"id": r.get("id"), "name": ["Legacy", "Regex"], "source": "", "source_ref": "", "note": r.get("note", "")}
                })
        else:
            raise ValueError("Unsupported rules.json schema. Expect list-of-rules or {keywords, regex, ...}.")

        # 预编译白名单/否定词为简单大小写不敏感搜索
        for r in self.rules:
            r["_neg_patterns"] = [re.compile(re.escape(t), re.I) for t in r.get("negations", []) if t]
            r["_white_patterns"] = [re.compile(re.escape(t), re.I) for t in r.get("whitelist", []) if t]

    def _sentence_iter(self, text: str) -> List[Tuple[str, int, int]]:
        return [(m.group(0), m.start(), m.end()) for m in _SENTENCE_REGEX.finditer(text)]

    @staticmethod
    def _contains_any(s: str, pats: List[re.Pattern]) -> bool:
        return any(p.search(s) for p in pats)

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        返回: {"highlights": [...], "comment": "Matched N patterns."}
        （为兼容性保留最小返回；若需要来源/说明，可在此函数里扩展为返回 details）
        """
        if not text:
            return {"highlights": [], "comment": "No text provided"}

        hits: List[Tuple[int, str]] = []  # (global_start, matched_text)
        sentences = self._sentence_iter(text)

        for sent, s_start, s_end in sentences:
            for rule in self.rules:
                # 句子级白名单/否定词过滤
                if rule["_white_patterns"] and self._contains_any(sent, rule["_white_patterns"]):
                    continue
                if rule["_neg_patterns"] and self._contains_any(sent, rule["_neg_patterns"]):
                    continue

                for pat in rule["patterns"]:
                    for m in pat.finditer(sent):
                        # 记录全局起点，便于去重排序
                        hits.append((s_start + m.start(), m.group(0)))

        # 按出现顺序排序 & 去重（忽略大小写）
        hits.sort(key=lambda x: x[0])
        seen = set()
        highlights: List[str] = []
        for _, h in hits:
            key = h.lower()
            if key not in seen:
                seen.add(key)
                highlights.append(h)

        comment = f"Matched {len(highlights)} patterns."
        return {"highlights": highlights, "comment": comment}
