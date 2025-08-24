import os
from app.core.metrics_tools.rules_llm_tool import LLMRubricScoringTool

def get_metrics_tool(mode: str | None = None):
    """
    Factory: choose tool implementation.
    Priority: request 'mode' > env RULES_MODE > default 'legacy'.
    """
    m = (mode or os.getenv("RULES_MODE", "legacy")).lower().strip()
    if m == "rules_llm":
        print("[FACTORY] -> LLMRubricScoringTool")
        return LLMRubricScoringTool()
    # fallback to legacy class (import late to avoid circular import)
    from app.core.tools import ESGMetricsCalculatorTool
    print("[FACTORY] -> ESGMetricsCalculatorTool (legacy)")
    return ESGMetricsCalculatorTool()
