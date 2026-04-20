import re
from datetime import datetime, timezone

# Weights for a simple rule-based scorer
CONFLICT_WEIGHTS = {
    'war': -3.0,
    'attack': -2.0,
    'riot': -2.0,
    'protest': -1.0,
}
PEACE_WEIGHTS = {
    'peace': 3.0,
    'agreement': 2.0,
    'growth': 2.0,
    'development': 1.0,
}

def _score_from_text(text: str) -> float:
    t = (text or "").lower()
    score = 5.0
    # conflict signals
    for w, wv in CONFLICT_WEIGHTS.items():
        if w in t:
            score += wv
    # peace signals
    for w, wv in PEACE_WEIGHTS.items():
        if w in t:
            score += wv
    # recency boost placeholder (will be applied by caller with pubDate)
    return max(0.0, min(10.0, score))

def classify(title: str, description: str, pubDate=None):
    text = (title or "") + " " + (description or "")
    score = _score_from_text(text)
    # recency boost: newer = higher score
    if pubDate:
        try:
            if isinstance(pubDate, str):
                dt = datetime.fromisoformat(pubDate.replace('Z', '+00:00'))
            else:
                dt = pubDate
            age = (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds()
            if age < 3600:
                score = min(10.0, score + 2.0)
            elif age < 21600:
                score = min(10.0, score + 1.0)
        except Exception:
            pass
    category = "NEUTRAL"
    color = "#888888"
    cls = "neutral"
    if score >= 6.5:
        category = "PEACE"
        color = "#1D9E75"
        cls = "peace"
    elif score < 4.0:
        category = "CONFLICT"
        color = "#E24B4A"
        cls = "conflict"
    else:
        category = "NEUTRAL"
        color = "#888888"
        cls = "neutral"
    return {
        'score': round(score, 1),
        'category': category,
        'color': color,
        'cls': cls
    }
