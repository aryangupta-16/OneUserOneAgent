# Known Limitations

## Intentionally Incomplete

### 1. No Real LLM Integration
The system uses a `MockModelProvider` that reproduces faults from `model_faults.jsonl` and returns safe defaults. A real LLM integration (OpenAI, Anthropic, etc.) could be swapped in via the `ModelProvider` protocol but was not implemented to avoid requiring API keys for evaluators.

### 2. Simplified Content Ranking
Title selection uses rule-based filtering (dialect match, availability, injection-free) rather than ML-based ranking. The assignment emphasizes the decide-act-measure loop over recommendation accuracy.

### 3. Limited Goal Outcome Judgment
The goal judge handles the most common success conditions but may not cover all edge cases for every goal type. Specifically:
- G07 (resume_series) uses simplified series tracking
- G09 (weekly_habit) counts play days but doesn't fully validate the 3-distinct-days condition against all possible event orderings

### 4. No Real-Time Streaming
The replay processes events in batch (sorted by deliver_at) rather than true real-time streaming. Latency is measured as processing time per decision, not wall-clock delivery time.

### 5. Holdout Impact Measurement
The impact report currently only measures outcomes for agent-arm users (those who received decisions). Holdout users' organic outcomes from the simulator are not yet fully integrated into the comparison. This would require tracking holdout user goals separately from decisions.

### 6. No UI
As stated in the assignment: "A working decide, act and measure loop matters more than a polished user interface." There is no web UI or dashboard.

### 7. Single-Threaded Replay
The replay harness processes triggers sequentially. It does not simulate concurrent processing of 1000+ triggers per minute, though the architecture supports it (each decision is independent per viewer).

### 8. Profile Snapshot Staleness
The system uses the day-stale profile snapshot for initial state but updates from events during replay. It does not re-fetch the profile mid-replay.

## What Would Be Done With More Time
1. Real LLM integration with proper prompt engineering for goal selection
2. More sophisticated content ranking using viewer engagement history
3. Proper A/B statistical analysis with confidence intervals for impact reporting
4. Concurrent replay processing with thread-safe viewer state
5. Web dashboard for viewing decisions, actions, and outcomes in real-time
6. More comprehensive goal outcome judgment for all edge cases
