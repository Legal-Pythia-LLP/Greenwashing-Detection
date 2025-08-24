def ensure_unified_metrics_schema(metrics: dict) -> dict:
    if not isinstance(metrics, dict):
        metrics = {}

    # Radar
    radar_in = metrics.get("radar", {}) or {}
    keys = ["vague", "lack_metrics", "misleading", "cherry", "no_3rd"]
    radar = {}
    for k in keys:
        try:
            v = int(round(float(radar_in.get(k, 0))))
        except Exception:
            v = 0
        radar[k] = max(0, min(100, v))
    metrics["radar"] = radar

    # Overall
    try:
        ov = float(metrics.get("overall", 0.0))
    except Exception:
        ov = 0.0
    metrics["overall"] = max(0.0, min(10.0, ov))

    # Breakdown
    metrics["breakdown"] = [
        {"type": "Vague or unsubstantiated claims", "value": float(radar["vague"])},
        {"type": "Lack of specific metrics or targets", "value": float(radar["lack_metrics"])},
        {"type": "Misleading terminology", "value": float(radar["misleading"])},
        {"type": "Cherry-picked data", "value": float(radar["cherry"])},
        {"type": "Absence of third-party verification", "value": float(radar["no_3rd"])},
    ]

    # Overall greenwashing score
    metrics["overall_greenwashing_score"] = {"score": metrics["overall"]}

    # Engine
    metrics.setdefault("engine", "unknown")

    return metrics
