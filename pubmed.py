"""PubMed E-utilities wrapper for literature gap detection."""

import requests
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# PubMed publication type filters
FILTERS = {
    "rct": "Randomized Controlled Trial[pt]",
    "cohort": "(Observational Study[pt] OR Cohort Studies[mh])",
    "case_series": "Case Reports[pt]",
    "meta_analysis": "Meta-Analysis[pt]",
    "systematic_review": "Systematic Review[pt]",
}


@dataclass
class StudyCounts:
    topic: str
    query_used: str
    total: int = 0
    rct: int = 0
    cohort: int = 0
    case_series: int = 0
    meta_analysis: int = 0
    systematic_review: int = 0
    recent_rct: int = 0  # last 3 years
    recent_cohort: int = 0
    sample_titles: list = field(default_factory=list)

    @property
    def primary_evidence(self) -> int:
        return self.rct + self.cohort

    @property
    def has_gap(self) -> bool:
        """Gap = primary evidence exists but no systematic review."""
        return self.primary_evidence >= 5 and self.systematic_review == 0

    @property
    def has_weak_gap(self) -> bool:
        """Weak gap = few reviews relative to primary evidence."""
        if self.primary_evidence < 3:
            return False
        return self.systematic_review <= 1 and self.primary_evidence >= 8

    @property
    def gap_score(self) -> float:
        """Higher = more promising gap. Weights RCTs heavily."""
        if self.systematic_review >= 3:
            return 0.0
        primary = self.rct * 3 + self.cohort * 1.5 + self.case_series * 0.3
        review_penalty = self.systematic_review * 15 + self.meta_analysis * 15
        recency_bonus = (self.recent_rct * 4 + self.recent_cohort * 2)
        return max(0, primary + recency_bonus - review_penalty)


def _esearch_count(query: str, api_key: Optional[str] = None) -> int:
    """Return the count of results for a PubMed query."""
    params = {
        "db": "pubmed",
        "term": query,
        "rettype": "count",
        "retmode": "json",
    }
    if api_key:
        params["api_key"] = api_key
    resp = requests.get(f"{BASE_URL}/esearch.fcgi", params=params, timeout=15)
    resp.raise_for_status()
    return int(resp.json()["esearchresult"]["count"])


def _esearch_ids(query: str, retmax: int = 5, api_key: Optional[str] = None) -> list:
    """Return PMIDs for a query."""
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": retmax,
        "retmode": "json",
        "sort": "date",
    }
    if api_key:
        params["api_key"] = api_key
    resp = requests.get(f"{BASE_URL}/esearch.fcgi", params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()["esearchresult"].get("idlist", [])


def _efetch_titles(pmids: list, api_key: Optional[str] = None) -> list:
    """Fetch article titles for a list of PMIDs."""
    if not pmids:
        return []
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
    }
    if api_key:
        params["api_key"] = api_key
    resp = requests.get(f"{BASE_URL}/efetch.fcgi", params=params, timeout=15)
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    titles = []
    for article in root.findall(".//ArticleTitle"):
        if article.text:
            titles.append(article.text)
    return titles


def count_studies(topic: str, api_key: Optional[str] = None, delay: float = 0.35) -> StudyCounts:
    """
    Count studies by type for a given topic query.
    
    Args:
        topic: PubMed search query (MeSH terms, keywords, etc.)
        api_key: Optional NCBI API key (raises rate limit to 10/sec)
        delay: Delay between requests to respect rate limits
    """
    counts = StudyCounts(topic=topic, query_used=topic)

    # Total
    counts.total = _esearch_count(topic, api_key)
    time.sleep(delay)

    # By study type
    for study_type, filter_str in FILTERS.items():
        query = f"({topic}) AND {filter_str}"
        setattr(counts, study_type, _esearch_count(query, api_key))
        time.sleep(delay)

    # Recent primary studies (last 3 years)
    recent_filter = 'AND ("2023"[PDAT] : "2026"[PDAT])'
    counts.recent_rct = _esearch_count(
        f'({topic}) AND {FILTERS["rct"]} {recent_filter}', api_key
    )
    time.sleep(delay)
    counts.recent_cohort = _esearch_count(
        f'({topic}) AND {FILTERS["cohort"]} {recent_filter}', api_key
    )
    time.sleep(delay)

    # Sample recent titles for context
    recent_ids = _esearch_ids(f"({topic}) AND (Randomized Controlled Trial[pt] OR Observational Study[pt])", 5, api_key)
    time.sleep(delay)
    counts.sample_titles = _efetch_titles(recent_ids, api_key)

    return counts


def scan_topics(topics, api_key=None):
    """Scan multiple topics and return sorted by gap score."""
    results = []
    for topic in topics:
        try:
            counts = count_studies(topic, api_key)
            results.append(counts)
            print(f"  ✓ {topic}: {counts.primary_evidence} primary, {counts.systematic_review} SR, score={counts.gap_score:.1f}")
        except Exception as e:
            print(f"  ✗ {topic}: {e}")
    results.sort(key=lambda x: x.gap_score, reverse=True)
    return results
