# AId-VO Comparison Methodology: With AI vs Without AI

This document defines how the side-by-side comparison between the
**baseline (AI off)** campaign and the **AId-VO (AI on)** campaign is
performed, what each metric means, and what the generated report contains.

> **Note on results:** this repository ships the *measurement machinery*, not
> fabricated numbers. Every value in `results/comparison/comparison_report.md`
> is computed from the actual recorded simulation runs produced on the user's
> machine. No illustrative or hand-written result values are included anywhere
> in the repository.

---

## 1. Campaign design (fair comparison)

| Aspect | Baseline (AI off) | AId-VO (AI on) |
|---|---|---|
| Interface | same `SimRunner`, same transcript parsing | identical |
| Tests | round-robin (or random) over the regression suite | chosen per run by the policy |
| Seeds | drawn from the same seed pool (`--seed-base`, same bucket count) | chosen per run by the policy |
| Clock profile | pinned to the default (`clock_profile_index: 0`) | steered per run (`+WCLK_HALF_NS/+RCLK_HALF_NS`) |
| Runs / goal | same `--runs`, same `--goal` | same |
| Machine / tool | same host, same QuestaSim, same compile | same |
| Records | `results/baseline/history.json` | `results/ai/history.json` |

Both campaigns stop early when the coverage goal is reached, so
*runs-to-goal* and *time-to-goal* are directly comparable.

Reproduction recipe:

```bash
python -m aidvo.cli baseline -c config/aidvo_config.yaml --runs 40 --seed-base 1000
python -m aidvo.cli train    -c config/aidvo_config.yaml --algo ppo --timesteps 2000
python -m aidvo.cli rollout  -c config/aidvo_config.yaml --model models/ppo/final \
                             --runs 40 --seed-base 1000 --goal 95
python -m aidvo.cli compare  --baseline results/baseline --ai results/ai \
                             -o results/comparison
```

For repeated experiments, vary `--seed-base` per repetition and keep the
algorithm/seed pairing documented in `results/`.

---

## 2. Metric definitions

| Metric | Definition |
|---|---|
| Final best coverage | highest cumulative scalar coverage reached by the campaign |
| Runs to goal | number of the first run whose best coverage ≥ goal (`n/a` if never) |
| Wall time to goal | summed wall-clock seconds of all runs up to runs-to-goal |
| Total simulation wall time | summed wall-clock seconds of every run |
| Total simulated time | summed simulated `ns` reported by the simulator |
| AI decision overhead | summed policy inference time (`decision_time_s`) - measured separately to demonstrate zero delay *inside* simulated time |
| Average best coverage/run | mean of the best-coverage-per-run trajectory |
| AUC (coverage vs runs) | trapezoidal area under the best-coverage trajectory, normalized by runs - a run-count-quality measure independent of the goal |
| Coverage per run | final best coverage / number of runs |
| Coverage per minute | final best coverage / (total wall time in minutes) |
| UVM errors/warnings | totals across all runs (sanity: a steering policy must not trade quality for errors) |
| Valid runs | runs that produced a parseable summary and finished cleanly |
| Runs-to-goal speed-up | baseline runs-to-goal ÷ AI runs-to-goal |
| Time-to-goal speed-up | baseline wall-to-goal ÷ AI wall-to-goal |

---

## 3. Generated artifacts

```text
results/comparison/
├── comparison_report.md     # full side-by-side tables + speed-up summary
├── coverage_progress.csv    # run, baseline_best_pct, ai_best_pct
└── coverage_progress.png    # plotted trajectories (needs matplotlib)
```

`comparison_report.md` sections:

1. **Header** - generation timestamp.
2. **Side-by-side table** - every metric from §2 for both campaigns.
3. **Speed-up summary** - runs-to-goal, time-to-goal, coverage-per-run ratios.
4. **Artifacts** - links to the raw histories for auditability.

Because both campaigns write the identical `history.json` schema, every
number in the report can be recomputed from the raw records with
`python tests/test_parsers.py` style tooling (the comparison functions are
plain Python in `aidvo/analysis/compare.py`).

---

## 4. Interpreting the outcome

* **Coverage closure acceleration** shows up as fewer runs and less wall time
  to the same goal (`runs-to-goal`, `time-to-goal`), and as a steeper
  coverage-vs-run curve (AUC, coverage/run).
* **Corner-case emphasis**: the hard-to-hit corner cases (full/almost-full,
  empty/almost-empty, blocked read/write) are exactly what raises the scalar
  coverage ceiling; compare the *final best coverage* when the baseline
  stagnates below the goal while the AI campaign keeps finding increments
  after stagnation (the policy reacts to the stagnation observation signal).
* **Quality guardrails**: check the UVM error/warning totals - a legitimate
  speed-up must not come from erroring runs (errors are penalized in the
  reward for this reason).
* **Zero-delay property**: `AI decision overhead` is reported separately; it
  never appears in simulated time.
