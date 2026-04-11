# LitGap — Literature Gap Detector

Scans PubMed for topics where primary evidence (RCTs, cohort studies) exists but no systematic review has been published. Flags opportunities for new systematic reviews.

## Quick Start

```bash
pip install -r requirements.txt

# Basic run with default neurosurgery topics
python main.py --no-ai

# Single query
python main.py --query '"awake craniotomy" AND "language outcomes"' --no-ai

# With Claude-powered interpretation
export ANTHROPIC_API_KEY=sk-ant-...
python main.py

# Custom topics from file
python main.py --topics my_topics.txt --output report.txt
```

## Optional: Faster PubMed Access

Get a free NCBI API key at https://www.ncbi.nlm.nih.gov/account/settings/ — raises rate limit from 3 to 10 requests/second.

```bash
export NCBI_API_KEY=your_key_here
```

## Optional: Scheduled Runs

Add a cron job to run weekly and email results:

```bash
# Every Sunday at 8am
0 8 * * 0 cd /path/to/litgap && python main.py --output /tmp/litgap_report.txt && mail -s "LitGap Weekly Report" your@email.com < /tmp/litgap_report.txt
```

Or use GitHub Actions — put the script in a repo and add a workflow that runs on a schedule.

## How It Works

1. Takes a list of PubMed search queries (MeSH terms, keywords)
2. For each topic, counts: RCTs, cohort studies, case reports, systematic reviews, meta-analyses
3. Also counts recent (last 3 years) primary studies
4. Computes a **gap score** — high score = lots of primary evidence, few/no reviews
5. Optionally sends results to Claude API for interpretation and PICO question generation

## Customising Topics

Edit `DEFAULT_TOPICS` in `main.py` or create a text file with one query per line:

```
"spinal cord stimulation" AND "chronic pain"
"robotic surgery" AND "spine" AND outcomes
# Lines starting with # are ignored
```

## Files

- `main.py` — Entry point and CLI
- `pubmed.py` — PubMed E-utilities wrapper and gap scoring logic
- `synthesize.py` — Claude API synthesis layer (falls back to plain report without API key)
