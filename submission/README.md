# One User, One Agent

A per-viewer AI agent for an OTT platform that decides, acts, and measures — built for the Agentic AI Engineering assignment.

## Quick Start

### Prerequisites
- Python 3.9+ (no external dependencies — stdlib only)
- Optional: `pip install openai` for real LLM integration

### Using Real LLM (Optional)
```bash
pip install openai
export OPENAI_API_KEY="your-key-here"
export OPENAI_MODEL="gpt-4o-mini"  # or gpt-4o, gpt-3.5-turbo, etc.
```
If no API key is set, the system automatically falls back to the mock provider.

### Setup
```bash
cd submission
```

### Run the Replay
```bash
python3 -m src.main replay --pack "../docs/one_user_one_agent_pack 2" --out sample_run
```

### Run the Simulator
```bash
python3 "../docs/one_user_one_agent_pack 2/simulator/simulate_outcomes.py" \
  --pack "../docs/one_user_one_agent_pack 2" \
  --actions sample_run/actions.jsonl \
  --out sample_run/sim
```

### Judge Outcomes and Compute Impact
```bash
python3 -m src.main judge --pack "../docs/one_user_one_agent_pack 2" \
  --decisions sample_run/decisions.jsonl \
  --outcomes-events sample_run/sim/outcome_events.jsonl \
  --out sample_run
```

### Run Tests
```bash
python3 tests/test_late_duplicate_trigger.py
python3 tests/test_conflicting_source.py
python3 tests/test_tool_failure.py
python3 tests/test_corrected_goal_rule.py
python3 tests/test_injection_detection.py
python3 tests/test_goal_traps.py
python3 tests/test_messaging_policy.py
python3 tests/test_holdout_isolation.py
```

## Output Files

| File | Description |
|---|---|
| `sample_run/decisions.jsonl` | Every decision made by the agent |
| `sample_run/actions.jsonl` | Every action published (input to simulator) |
| `sample_run/outcomes.jsonl` | Goal outcome judgments |
| `sample_run/latency_report.json` | Decision latency statistics |
| `sample_run/impact_report.md` | Agent vs holdout impact analysis |
| `sample_run/final_report.md` | Summary report |
| `sample_run/viewer_state/*.json` | Per-viewer state snapshots |

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system design.
