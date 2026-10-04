"""
AId-VO self-tests for the pure-Python components (no simulator, no training).

Run with either:
    python tests/test_parsers.py
    pytest tests/            (if pytest is installed)

Covered:
* configuration loading, action-space decoding and boundary run resolution,
* scalar transcript parsing (coverage %, UVM report-summary counts),
* scalar total extraction from a coverage report text,
* command-template expansion,
* history persistence and the baseline-vs-AI comparison report.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aidvo.analysis.compare import campaign_metrics, compare  # noqa: E402
from aidvo.analysis.history import History, RunRecord  # noqa: E402
from aidvo.boundary.runner import build_tokens  # noqa: E402
from aidvo.boundary.transcript import parse_report_total, parse_transcript  # noqa: E402
from aidvo.config import Config  # noqa: E402

CFG_PATH = ROOT / "config" / "aidvo_config.yaml"

SYNTHETIC_TRANSCRIPT = """\
# vsim -c ...
# ** Note: run.do ...
UVM_INFO @ 0: reporter [RNTST] Running test fifo_base_test ...
...
==================================================
Functional Coverage Summary
==================================================
Write Coverage : 81.25%
Read Coverage  : 66.67%
Average Coverage : 73.96%
==================================================
--- UVM Report Summary ---
Number of demoted UVM_WARNING reports  :    0
UVM_INFO :   42
UVM_WARNING :    4
UVM_ERROR   :    0
UVM_FATAL   :    0
# ** Note: $finish : fifo_tb.sv
#    Time: 1000000 ns
"""

SYNTHETIC_REPORT = """\
# Questa coverage summary (synthetic text for parser testing)
------------------------------------------------------------
--------------------------------------------
Group              Hits  Miss  % Coverage
--------------------------------------------
Total              118   12    90.77%
"""

PARSE_CFG = {
    "coverage_regex": r"Average Coverage\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*%",
    "uvm_error_regex": r"UVM_ERROR\s*:\s*(\d+)",
    "uvm_warning_regex": r"UVM_WARNING\s*:\s*(\d+)",
    "uvm_fatal_regex": r"UVM_FATAL\s*:\s*(\d+)",
    "sim_time_regex": r"Time:\s*([0-9.eE+-]+)\s*ns",
}


def test_config_and_action_space():
    cfg = Config.load(str(CFG_PATH))
    assert cfg.n_actions == 10 * 8 * 4, cfg.n_actions
    assert cfg.knob_cardinalities == [10, 8, 4]

    d0 = cfg.decode_action(0)
    assert d0["test"]["value"] == "fifo_reset_test"
    r0 = cfg.resolve_run(d0, episode_index=1)
    assert r0["seed"] == 1000 + 1 * 100000  # vary_by_episode offset
    assert "+UVM_TESTNAME=fifo_reset_test" in r0["plusargs"]
    assert "+WCLK_HALF_NS=5" in r0["plusargs"]
    assert "+RCLK_HALF_NS=7" in r0["plusargs"]

    # mixed-radix decode: first knob fastest
    d = cfg.decode_action(1)
    assert d["test"]["index"] == 1 and d["seed_bucket"]["index"] == 0
    d = cfg.decode_action(10)
    assert d["test"]["index"] == 0 and d["seed_bucket"]["index"] == 1
    cfg.decode_action(cfg.n_actions - 1)  # must not raise
    try:
        cfg.decode_action(cfg.n_actions)
        raise AssertionError("out-of-range action accepted")
    except ValueError:
        pass

    # seed knob with vary disabled
    for knob in cfg.knobs:
        if knob["kind"] == "seed":
            knob["vary_by_episode"] = False
    r = cfg.resolve_run(cfg.decode_action(30), episode_index=7)  # seed_bucket index 3
    assert r["seed"] == 1000 + 3


def test_transcript_parsing():
    stats = parse_transcript(SYNTHETIC_TRANSCRIPT, PARSE_CFG)
    assert stats.coverage_pct == 73.96, stats.coverage_pct
    assert stats.uvm_errors == 0
    assert stats.uvm_warnings == 4
    assert stats.uvm_fatals == 0
    assert stats.sim_time_ns == 1000000.0
    assert stats.valid

    # UVM_ERROR line inside a message must not be picked up (summary wins
    # because only the colon-count form matches the regex)
    messy = "UVM_ERROR file.sv(1) @ 0: uvm_test_top [E] boom\nUVM_ERROR : 2\n"
    s2 = parse_transcript(messy, PARSE_CFG)
    assert s2.uvm_errors == 2

    # missing summary -> invalid run
    s3 = parse_transcript("no summary here", PARSE_CFG)
    assert not s3.valid and s3.coverage_pct is None

    # fatal -> invalid run
    s4 = parse_transcript(SYNTHETIC_TRANSCRIPT + "\nUVM_FATAL : 1\n", PARSE_CFG)
    assert not s4.valid


def test_report_total_parsing():
    total = parse_report_total(
        SYNTHETIC_REPORT,
        r"(?:^|\n)\s*Total[^%\n]*?([0-9]+(?:\.[0-9]+)?)\s*%",
    )
    assert total == 90.77, total
    assert parse_report_total("nothing", r"Total[^%\n]*?([0-9.]+)%") is None


def test_command_template_expansion():
    template = [
        "vsim", "-c", "-work", "{work_lib}", "{top}",
        "-sv_seed", "{seed}", "{plusargs}", "{extra}", "-l", "{log_file}",
    ]
    argv = build_tokens(
        template,
        {"work_lib": "/tmp/work", "top": "fifo_tb", "seed": "42",
         "log_file": "/tmp/t.log"},
        plusargs=["+UVM_TESTNAME=fifo_fwft_test", "+WCLK_HALF_NS=2"],
        extra=["-coverage"],
    )
    assert argv == [
        "vsim", "-c", "-work", "/tmp/work", "fifo_tb", "-sv_seed", "42",
        "+UVM_TESTNAME=fifo_fwft_test", "+WCLK_HALF_NS=2", "-coverage",
        "-l", "/tmp/t.log",
    ]


def _make_history(mode, algo, goal, covs):
    h = History(mode=mode, algo=algo, seed_base=1000, goal_pct=goal)
    for i, cov in enumerate(covs, start=1):
        h.add(RunRecord(run=i, mode=mode, algo=algo, test="t", seed=1000 + i,
                        coverage_pct=cov, uvm_errors=0, uvm_warnings=1,
                        valid=True, wall_time_s=2.0, sim_time_ns=1e6))
    return h


def test_history_and_compare():
    base = _make_history("baseline", "-", 95.0, [10, 20, 28, 35, 40, 44, 47, 49])
    ai = _make_history("ai", "ppo", 95.0, [10, 35, 60, 80, 96])
    mb = campaign_metrics(base)
    ma = campaign_metrics(ai)
    assert mb["runs_to_goal"] is None      # never reaches 95%
    assert ma["runs_to_goal"] == 5
    assert ma["runs"] == 5

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        bdir, adir, odir = tmp_path / "b", tmp_path / "a", tmp_path / "o"
        base.save(bdir)
        ai.save(adir)

        loaded = History.load(bdir)
        assert len(loaded.runs) == 8 and loaded.goal_pct == 95.0
        assert (bdir / "history.csv").is_file()

        report = compare(bdir, adir, odir)
        assert report.is_file()
        text = report.read_text(encoding="utf-8")
        assert "Speed-up summary" in text
        import re as _re
        assert _re.search(r"Coverage-per-run ratio \(AI / baseline\) \| [0-9.]+x", text)
        assert (odir / "coverage_progress.csv").is_file()
        rows = (odir / "coverage_progress.csv").read_text().strip().splitlines()
        assert rows[0] == "run,baseline_best_pct,ai_best_pct"
        assert len(rows) == 1 + 8  # longest campaign
        # json loads cleanly
        json.loads((bdir / "history.json").read_text())


def test_baseline_campaign_mocked():
    """End-to-end AI-off campaign with a stubbed runner (no simulator)."""
    import aidvo.agents.baseline as bl
    from aidvo.boundary.runner import SimResult
    from aidvo.boundary.transcript import TranscriptStats

    cfg = Config.load(str(CFG_PATH))
    cfg.set_goal_pct(50.0)

    class FakeRunner:
        calls = []

        def __init__(self, _cfg):
            pass

        def run(self, run_dir, seed, plusargs=(), extra=()):
            FakeRunner.calls.append({"seed": seed, "plusargs": list(plusargs),
                                     "extra": list(extra)})
            cov = 10.0 * len(FakeRunner.calls)    # 10, 20, ... -> goal at run 5
            stats = TranscriptStats(coverage_pct=cov, uvm_errors=0,
                                    uvm_warnings=1, uvm_fatals=0,
                                    report_summary_found=True)
            return SimResult(run_dir=Path(run_dir), log_file=Path(run_dir) / "transcript.log",
                             command=["vsim"], returncode=0, wall_time_s=0.5,
                             stats=stats, coverage_pct=cov)

    original = bl.SimRunner
    bl.SimRunner = FakeRunner
    FakeRunner.calls = []
    try:
        with tempfile.TemporaryDirectory() as tmp:
            hist = bl.run_baseline(cfg, out_dir=Path(tmp) / "baseline",
                                   runs=20, seed_base=4242)
            # early stop: goal 50% reached on run 5
            assert len(hist.runs) == 5, len(hist.runs)
            assert hist.best_pct == 50.0
            assert hist.mode == "baseline" and hist.goal_pct == 50.0
            # identical history schema as the AI campaign
            loaded = History.load(Path(tmp) / "baseline")
            assert len(loaded.runs) == 5
            first = loaded.runs[0]
            assert first.seed >= 4242 and first.seed < 4242 + 8
            assert first.test.startswith("fifo_")
            assert "WCLK_HALF_NS" in first.profile
            assert first.coverage_pct == 10.0 and first.valid
            # steering uses only boundary inputs: seed + test plusarg +
            # clock-profile plusargs, default profile (index 0) throughout
            assert len(FakeRunner.calls) == 5
            for call in FakeRunner.calls:
                assert 4242 <= call["seed"] < 4242 + 8
                assert any(a.startswith("+UVM_TESTNAME=fifo_") for a in call["plusargs"])
                assert "+WCLK_HALF_NS=5" in call["plusargs"]
                assert "+RCLK_HALF_NS=7" in call["plusargs"]
                assert len(call["plusargs"]) == 3
                assert call["extra"] == []
            # round-robin test scheduling walks distinct tests
            tests_used = [c["plusargs"][0] for c in FakeRunner.calls]
            assert len(set(tests_used)) == 5
    finally:
        bl.SimRunner = original


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in tests:
        try:
            fn()
            print("PASS  %s" % fn.__name__)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print("FAIL  %s: %r" % (fn.__name__, exc))
    print("%d/%d passed" % (len(tests) - failed, len(tests)))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
