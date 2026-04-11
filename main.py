#!/usr/bin/env python3
"""
LitGap — Literature Gap Detector

Scans PubMed for topics where primary evidence (RCTs, cohort studies)
exists but no systematic review has been published. Flags opportunities
for systematic reviews.

Usage:
    python main.py                          # Run with default neurosurgery topics
    python main.py --topics topics.txt      # Run with custom topic list (one per line)
    python main.py --query "spinal cord stimulation AND chronic pain"  # Single query
    python main.py --output report.txt      # Save report to file

Environment:
    NCBI_API_KEY        Optional. Raises PubMed rate limit from 3 to 10 req/sec.
    ANTHROPIC_API_KEY   Optional. Enables Claude-powered gap interpretation.
"""

import argparse
import os
import sys
from datetime import datetime

from pubmed import scan_topics, count_studies
from synthesize import synthesize_gaps, _fallback_report


# Default topics to scan — neurosurgery / neuroscience focused
DEFAULT_TOPICS = [
    # Minimally invasive neurosurgery
    '"endoscopic surgery"[MeSH] AND "intracerebral hemorrhage"[MeSH]',
    '"tubular retractor" AND brain AND surgery',
    '"awake craniotomy" AND "language mapping"',
    '"colloid cyst" AND "third ventricle" AND management',
    # Spine
    '"short segment fixation" AND "metastatic spine"',
    '"full-endoscopic" AND "intradural" AND spine',
    '"minimally invasive" AND "lumbar fusion" AND outcomes',
    # Functional / technology
    '"deep brain stimulation" AND "disorders of consciousness"',
    '"brain-computer interface" AND "motor recovery"',
    '"intraoperative MRI" AND glioma AND resection',
    # Neuro + AI
    '"artificial intelligence" AND "neurosurgery" AND "decision making"',
    '"large language model" AND "clinical guidelines" AND surgery',
]


def main():
    parser = argparse.ArgumentParser(description="LitGap — Literature Gap Detector")
    parser.add_argument("--topics", type=str, help="Path to text file with topics (one per line)")
    parser.add_argument("--query", type=str, help="Single PubMed query to analyse")
    parser.add_argument("--output", type=str, help="Save report to file")
    parser.add_argument("--no-ai", action="store_true", help="Skip Claude synthesis, plain report only")
    args = parser.parse_args()

    # Determine topics
    if args.query:
        topics = [args.query]
    elif args.topics:
        with open(args.topics) as f:
            topics = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    else:
        topics = DEFAULT_TOPICS

    ncbi_key = os.environ.get("NCBI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    print(f"\n{'='*60}")
    print(f"  LitGap — Literature Gap Detector")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Scanning {len(topics)} topics...")
    if ncbi_key:
        print(f"  NCBI API key: configured (10 req/sec)")
    else:
        print(f"  NCBI API key: not set (3 req/sec — slower)")
    print(f"{'='*60}\n")

    # Scan
    results = scan_topics(topics, api_key=ncbi_key)

    # Report
    if not args.no_ai and anthropic_key:
        print("\nGenerating Claude-powered analysis...\n")
        report = synthesize_gaps(results, api_key=anthropic_key)
    else:
        report = _fallback_report(results)

    print(report)

    # Save
    if args.output:
        with open(args.output, "w") as f:
            f.write(f"LitGap Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"Topics scanned: {len(topics)}\n\n")
            f.write(report)
        print(f"\nReport saved to {args.output}")

    # Summary
    gaps = [r for r in results if r.has_gap]
    weak = [r for r in results if r.has_weak_gap and not r.has_gap]
    print(f"\n{'='*60}")
    print(f"  SUMMARY: {len(gaps)} strong gaps, {len(weak)} weak gaps out of {len(results)} topics")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
