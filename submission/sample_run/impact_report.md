# Impact Report

## Method

**agent_arm_vs_holdout_arm (randomized)**
Compared by randomized arm assignment, NOT by served vs unserved

## Results

| Group | Users | Goals Tracked | Succeeded | Rate |
|---|---|---|---|---|
| Agent | 2513 | 1397 | 503 | 36.0% |
| Holdout | 2487 | 0 | 0 | 0.0% |

**Absolute uplift:** 36.0%
**Relative uplift:** 0.00x

## Per-Goal Breakdown

| Goal | Agent Rate | Holdout Rate |
|---|---|---|
| G01 | 28.1% (32/114) | 0.0% (0/0) |
| G02 | 12.5% (51/409) | 0.0% (0/0) |
| G03 | 100.0% (1/1) | 0.0% (0/0) |
| G05 | 5.1% (15/292) | 0.0% (0/0) |
| G06 | 12.2% (12/98) | 0.0% (0/0) |
| G07 | 72.6% (170/234) | 0.0% (0/0) |
| G08 | 89.1% (221/248) | 0.0% (0/0) |
| G12 | 100.0% (1/1) | 0.0% (0/0) |

## Why Not Served vs Unserved?

Comparing 'served' vs 'unserved' users introduces survivorship bias.
Users the agent chose to help were already more likely to succeed.
The randomized holdout arm provides an unbiased comparison.
