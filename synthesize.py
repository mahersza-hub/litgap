"""Claude API layer for interpreting and enriching gap analysis results."""

import json
import os
from typing import Optional



def synthesize_gaps(results: list, api_key: Optional[str] = None) -> str:
    """
    Use Claude to interpret gap analysis results and produce
    an actionable research opportunity report.
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return _fallback_report(results)

    client = Anthropic(api_key=key)

    data = []
    for r in results:
        data.append({
            "topic": r.topic,
            "total_studies": r.total,
            "rcts": r.rct,
            "cohort_studies": r.cohort,
            "case_reports": r.case_series,
            "systematic_reviews": r.systematic_review,
            "meta_analyses": r.meta_analysis,
            "recent_rcts_3yr": r.recent_rct,
            "recent_cohort_3yr": r.recent_cohort,
            "gap_score": round(r.gap_score, 1),
            "sample_titles": r.sample_titles[:3],
        })

    prompt = f"""You are a research methodology expert. Analyse these PubMed literature scan results and identify the most promising systematic review opportunities.

DATA:
{json.dumps(data, indent=2)}

For each topic with a gap_score > 0, provide:
1. Whether a systematic review is viable (enough primary studies, likely comparable outcomes?)
2. A suggested PICO-style review question
3. Feasibility notes (estimated study count for inclusion, likely heterogeneity concerns)
4. Priority ranking (high/medium/low) based on gap size and recency of evidence

Be direct. Flag topics where the numbers look promising but a review likely isn't viable (e.g., too heterogeneous, niche populations). Keep it concise."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def _fallback_report(results: list) -> str:
    """Plain text report when no API key is available."""
    lines = ["\n=== LITERATURE GAP REPORT ===\n"]
    for r in sorted(results, key=lambda x: x.gap_score, reverse=True):
        flag = ""
        if r.has_gap:
            flag = " *** STRONG GAP ***"
        elif r.has_weak_gap:
            flag = " * WEAK GAP *"
        
        lines.append(f"Topic: {r.topic}{flag}")
        lines.append(f"  Total: {r.total} | RCTs: {r.rct} | Cohort: {r.cohort} | Case reports: {r.case_series}")
        lines.append(f"  Systematic Reviews: {r.systematic_review} | Meta-analyses: {r.meta_analysis}")
        lines.append(f"  Recent (3yr): {r.recent_rct} RCTs, {r.recent_cohort} cohort")
        lines.append(f"  Gap Score: {r.gap_score:.1f}")
        if r.sample_titles:
            lines.append(f"  Sample titles:")
            for t in r.sample_titles[:3]:
                lines.append(f"    - {t}")
        lines.append("")
    return "\n".join(lines)
