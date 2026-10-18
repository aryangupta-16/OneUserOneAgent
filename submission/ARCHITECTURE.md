# Architecture

## System Overview

The system implements a per-viewer AI agent with a decide-act-measure loop:

```
Trigger (app_open) -> Viewer State -> Goal Selection -> Intervention Choice -> Verification -> Action/No-Action
```

## Components

### 1. Data Layer (`src/data/`)
- **loader.py**: `DataPack` class loads all CSV/JSON/JSONL files into indexed structures
- **events.py**: Event loading with deduplication by event_id, user indexing
- **catalogue.py**: Title catalogue with availability checks and injection sanitization

### 2. State Layer (`src/state/`)
- **viewer_state.py**: `ViewerState` dataclass tracks per-viewer facts, events, goals, decisions, actions with full provenance. `ViewerStateManager` manages all viewer states.
- **fact_resolver.py**: Resolves conflicts between data sources (app_dialect vs profile vs deeplink) with explicit precedence rules

### 3. Goals Layer (`src/goals/`)
- **goal_registry.py**: Loads 12 goals, detects traps (G10 has null event, G11 has non-existent event type)
- **eligibility.py**: Checks eligibility for each goal against viewer state
- **goal_judge.py**: Judges goal outcomes from simulator events

### 4. Agent Layer (`src/agent/`)
- **decision_engine.py**: Core decide-act-verify loop. For each trigger: resolves dialect, selects goal, chooses intervention, verifies, outputs decision
- **goal_selector.py**: Ranks eligible goals by business priority
- **intervention_builder.py**: Builds home_page, push, whatsapp, or in_app_message actions
- **content_picker.py**: Selects titles by dialect, availability, and injection-free descriptions

### 5. Verification Layer (`src/verify/`)
- **verifier.py**: Independent checks that can disagree with the decision step: eligibility, dialect match, consent, quiet hours, frequency caps, content availability, injection detection, holdout isolation

### 6. Model Layer (`src/model/`)
- **provider.py**: `ModelProvider` protocol interface
- **mock_provider.py**: Reproduces all 5 faults from model_faults.jsonl (unsupported_claim, malformed_output, timeout). Returns safe defaults for other calls. No real LLM needed.

### 7. Replay Layer (`src/replay/`)
- **harness.py**: Merges triggers + live_events + control_events by deliver_at time, processes in order
- **control_handler.py**: Handles title withdrawals, goal rule corrections, dependency failures
- **latency_tracker.py**: Tracks per-decision latency with p95/p99 reporting

### 8. Measurement Layer (`src/measure/`)
- **outcome_judge.py**: Judges each goal as succeeded/failed/inconclusive from simulator events
- **impact_report.py**: Compares agent arm vs holdout arm (randomized), NOT served vs unserved

## Key Design Decisions

### Dialect Resolution Precedence
1. `app_dialect` from current event (strongest)
2. Deeplink dialect (strong, can be stale)
3. Previous event dialect (medium)
4. Profile preferred_dialect (weakest, day-stale)
All conflicts recorded in decision output.

### Goal Trap Handling
- **G10**: `event: null` — no measurable signal exists. Marked non-measurable, never selected.
- **G11**: `tv_app_open` — event type doesn't exist in stream. Marked non-measurable.
- **G03 correction**: Mid-replay rule change from `app_open` to `play_started`. Applied retroactively to all open G03 goals.

### Injection Detection
Catalogue T0002 contains a prompt injection in its description. The system:
- Strips injection patterns from descriptions before use
- Detects and logs injections for auditability
- Never treats data text as instructions (messaging policy rule 6)

### Honest Impact Measurement
The pilot report compared "served" vs "all others" (survivorship bias). We compare **agent arm vs holdout arm** from `replay/arms.csv` — the randomized groups.

### Do Nothing Is Valid
The agent chooses "no action" when: no goal is eligible, evidence is insufficient, viewer is in holdout, all interventions violate policy, or model fails with no safe fallback.

## Trust Boundaries

- **Data is not instruction**: Text in catalogue descriptions, search queries, deeplinks is content, never commands
- **Model output is not evidence**: The verifier independently checks all model claims
- **Holdout is sacred**: Holdout users receive zero actions, verified independently
- **Generated text is not approval**: Verification checks run independently of the decision step
