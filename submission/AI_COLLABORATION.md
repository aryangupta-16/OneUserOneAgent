# AI Collaboration Log

## Tools Used
- **Claude (Anthropic)**: Primary coding agent for implementation
- **Codex-style assistance**: Code generation and review

## How AI Was Used

### Architecture Design
- AI helped analyze the assignment PDF and data pack structure
- Proposed modular architecture with clear separation of concerns
- I reviewed and adjusted the design to ensure it matched the assignment requirements

### Implementation
- AI generated boilerplate code for data loading, state management, and verification
- I reviewed all generated code for correctness, especially:
  - Dialect resolution precedence logic
  - Goal eligibility checks for all 12 goals
  - Injection detection patterns
  - Quiet hours and consent enforcement

### Key Decisions I Made (Not AI)
1. **No real LLM calls**: I chose to build a MockModelProvider instead of using a real LLM, since the assignment says evaluators shouldn't need API keys
2. **Goal trap detection**: I identified G10 (null event) and G11 (non-existent event type) as traps and implemented explicit filtering
3. **Deeplink parsing**: AI initially parsed the dialect from the wrong index in the deeplink URL. I caught this during testing and fixed it
4. **Impact measurement**: I insisted on comparing agent arm vs holdout arm (randomized), not served vs unserved, to avoid the survivorship bias from the pilot report

### What AI Suggested That I Rejected
1. AI suggested using a real LLM for goal selection. I rejected this because:
   - The assignment says to provide a mock mode
   - Evaluators shouldn't need API keys
   - A mock provider that reproduces the exact faults is more testable
2. AI initially suggested comparing served vs unserved for impact. I corrected this to use the randomized arms
3. AI suggested adding more complex ML-based content ranking. I kept it simple with rule-based selection since the assignment emphasizes the decide-act-measure loop, not recommendation accuracy

### Verification Approach
- All AI-generated code was run and tested before submission
- 8 automated tests cover the required scenarios (late/duplicate, conflicting, failure, correction) plus bonus scenarios (injection, goal traps, messaging, holdout)
- Full replay was run end-to-end with the simulator to validate the pipeline
