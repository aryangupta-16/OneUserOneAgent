"""CLI entry point for the agent system."""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.loader import DataPack
from src.replay.harness import ReplayHarness
from src.measure.outcome_judge import judge_outcomes, save_outcomes
from src.measure.impact_report import compute_impact, write_impact_report
from src.output.writer import write_text


def main():
    parser = argparse.ArgumentParser(description="One User, One Agent")
    sub = parser.add_subparsers(dest="command")
    rp = sub.add_parser("replay", help="Run the replay")
    rp.add_argument("--pack", required=True)
    rp.add_argument("--out", default="sample_run")
    jp = sub.add_parser("judge", help="Judge outcomes after simulator")
    jp.add_argument("--pack", required=True)
    jp.add_argument("--decisions", default="sample_run/decisions.jsonl")
    jp.add_argument("--outcomes-events", default="sample_run/sim/outcome_events.jsonl")
    jp.add_argument("--out", default="sample_run")
    args = parser.parse_args()
    if args.command == "replay":
        run_replay(args.pack, args.out)
    elif args.command == "judge":
        run_judge(args.pack, args.decisions, args.outcomes_events, args.out)
    else:
        parser.print_help()


def run_replay(pack_path, out_dir):
    print(f"Loading data pack from {pack_path}...")
    pack = DataPack(pack_path).load()
    print(f"  Events: {len(pack.all_events)}, Users: {len(pack.events_by_user)}")
    print(f"  Titles: {len(pack.catalogue)}, Goals: {len(pack.goals)}")
    print(f"  Triggers: {len(pack.triggers)}")
    agent_ct = sum(1 for a in pack.arms.values() if a == "agent")
    holdout_ct = sum(1 for a in pack.arms.values() if a == "holdout")
    print(f"  Arms: agent={agent_ct}, holdout={holdout_ct}")
    print("\nRunning replay...")
    harness = ReplayHarness(pack)
    harness.run()
    print(f"  Decisions: {len(harness.all_decisions)}, Actions: {len(harness.all_actions)}")
    os.makedirs(out_dir, exist_ok=True)
    harness.save_outputs(out_dir)
    report = harness.latency.report()
    print(f"\nLatency: median={report.get('median_ms',0)}ms, p95={report.get('p95_ms',0)}ms, max={report.get('max_ms',0)}ms")
    print(f"  Within budget: {report.get('within_budget',0)}/{report.get('total_decisions',0)}")
    _write_final_report(harness, out_dir)
    print(f"\nOutputs saved to {out_dir}/")
    print(f"Next: python simulator/simulate_outcomes.py --pack {pack_path} --actions {out_dir}/actions.jsonl --out {out_dir}/sim")


def run_judge(pack_path, decisions_path, outcomes_events_path, out_dir):
    pack = DataPack(pack_path).load()
    decisions = []
    with open(decisions_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                decisions.append(json.loads(line))
    outcome_events = []
    if os.path.exists(outcomes_events_path):
        with open(outcomes_events_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    outcome_events.append(json.loads(line))
    outcomes = judge_outcomes(decisions, outcome_events, pack)
    save_outcomes(outcomes, os.path.join(out_dir, "outcomes.jsonl"))
    succeeded = sum(1 for o in outcomes if o.get("status") == "succeeded")
    print(f"Outcomes: {len(outcomes)} ({succeeded} succeeded)")
    impact = compute_impact(decisions, outcomes, pack)
    write_impact_report(impact, os.path.join(out_dir, "impact_report.md"))
    print(f"Agent rate: {impact['agent_arm']['rate']:.1%}, Holdout: {impact['holdout_arm']['rate']:.1%}")
    print(f"Uplift: {impact['uplift_absolute']:.1%} ({impact['uplift_relative']:.2f}x)")


def _write_final_report(harness, out_dir):
    decisions = harness.all_decisions
    actions = harness.all_actions
    lat = harness.latency.report()
    action_counts = {}
    for a in actions:
        t = a.get("type", "unknown")
        action_counts[t] = action_counts.get(t, 0) + 1
    no_act = sum(1 for d in decisions if d.get("status") == "NO_ACTION")
    pub = sum(1 for d in decisions if d.get("status") == "PUBLISHED")
    lines = ["# Final Report", "", "## Summary", "",
             f"- **Total decisions:** {len(decisions)}",
             f"- **Actions published:** {pub}",
             f"- **No-action decisions:** {no_act}",
             f"- **Total actions:** {len(actions)}", "",
             "## Action Breakdown", "", "| Type | Count |", "|---|---|"]
    for t, c in sorted(action_counts.items()):
        lines.append(f"| {t} | {c} |")
    lines.extend(["", "## Latency", "",
                  f"- Median: {lat.get('median_ms',0)}ms",
                  f"- P95: {lat.get('p95_ms',0)}ms",
                  f"- Max: {lat.get('max_ms',0)}ms",
                  f"- Within 60s budget: {lat.get('within_budget',0)}/{lat.get('total_decisions',0)}",
                  "", "## Control Events Handled", ""])
    for c in harness.control.corrections_applied:
        lines.append(f"- Goal correction: {c['goal_id']} at {c['at']}")
    if harness.control.withdrawn_titles:
        lines.append(f"- Titles withdrawn: {', '.join(harness.control.withdrawn_titles)}")
    write_text("\n".join(lines) + "\n", os.path.join(out_dir, "final_report.md"))


if __name__ == "__main__":
    main()

