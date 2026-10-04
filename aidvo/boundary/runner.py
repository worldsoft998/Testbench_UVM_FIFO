"""
Simulation-boundary runner.

Builds and executes vendor simulator command lines (QuestaSim by default,
adaptable through the command templates in the YAML config) and returns the
scalar observations obtained from the resulting transcript.

Each simulation runs with its *own working directory*, so parallel RL
workers never collide on transcript/dump.vcd output files.  The compiled
design library is referenced through an absolute path.

No testbench file is read or written here - the runner only shells out to
the simulator at the simulation boundary.
"""
from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from ..config import Config
from .transcript import TranscriptStats, parse_report_total, parse_transcript


@dataclass
class SimResult:
    """Outcome of one boundary simulation plus its scalar observations."""

    run_dir: Path
    log_file: Path
    command: List[str]
    returncode: int
    wall_time_s: float
    stats: TranscriptStats
    coverage_pct: Optional[float] = None   # scalar coverage for this run
    timed_out: bool = False

    @property
    def valid(self) -> bool:
        return (not self.timed_out) and self.returncode == 0 and self.stats.valid


def detect_uvm_src(cfg: Config) -> str:
    """Locate the vendor UVM source directory (never touches the testbench)."""
    candidates: List[str] = []
    env_src = os.environ.get("UVM_SRC")
    if env_src:
        candidates.append(env_src)
    uvm_home = os.environ.get("UVM_HOME")
    if uvm_home:
        candidates.append(str(Path(uvm_home) / "src"))
    questa = os.environ.get("QUESTA_HOME")
    if questa:
        for ver in ("uvm-1800.2-2017", "uvm-1.2", "uvm-1.1d"):
            candidates.append(str(Path(questa) / "verilog_src" / ver / "src"))
    guess = cfg.commands.get("uvm_src_guess") or cfg.data.get("uvm", {}).get("auto_src_guess", "")
    if guess:
        candidates.append(str(Path(guess)))
    for cand in candidates:
        if cand and (Path(cand) / "uvm_pkg.sv").is_file():
            return str(Path(cand))
    return candidates[0] if candidates else ""


def _subst(token: str, mapping: Dict[str, str]) -> str:
    for key, val in mapping.items():
        token = token.replace("{%s}" % key, str(val))
    return token


def build_tokens(
    template: Sequence[str],
    mapping: Dict[str, str],
    plusargs: Sequence[str] = (),
    extra: Sequence[str] = (),
) -> List[str]:
    """Expand a config command template (list of argv tokens) into argv."""
    out: List[str] = []
    for token in template:
        if token == "{plusargs}":
            out.extend(str(a) for a in plusargs)
        elif token == "{extra}":
            out.extend(str(a) for a in extra)
        elif token == "{inputs}":
            continue  # handled via mapping["inputs"] by the caller
        else:
            out.append(_subst(token, mapping))
    return out


class SimRunner:
    """Executes simulations strictly at the simulation boundary."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.repo_root = cfg.repo_root
        self.work_lib = (self.repo_root / "work").as_posix()
        self.do_file = (self.repo_root / "sim" / "run.do").as_posix()
        self.uvm_src = detect_uvm_src(cfg)
        self.timeout_s = int(cfg.commands.get("timeout_s", 900))

    # ------------------------------------------------------------ command build
    def _mapping(self, run_dir: Path, log_file: Path, seed: int) -> Dict[str, str]:
        return {
            "top": self.cfg.top,
            "seed": str(seed),
            "work_lib": self.work_lib,
            "run_dir": str(run_dir),
            "log_file": str(log_file),
            "uvm_src": self.uvm_src,
            "repo_root": str(self.repo_root),
            "do_file": self.do_file,
        }

    def build_simulate_command(
        self,
        run_dir: Path,
        seed: int,
        plusargs: Sequence[str] = (),
        extra: Sequence[str] = (),
    ) -> List[str]:
        log_file = run_dir / "transcript.log"
        template = self.cfg.commands.get("simulate")
        if not template:
            raise RuntimeError("config commands.simulate is missing")
        return build_tokens(template, self._mapping(run_dir, log_file, seed), plusargs, extra)

    # ------------------------------------------------------------------ compile
    def compile(self) -> int:
        """Run the configured compile steps (used by `aidvo compile`)."""
        steps = self.cfg.commands.get("compile_steps", [])
        for step in steps:
            argv = build_tokens(
                step,
                {"uvm_src": self.uvm_src, "repo_root": str(self.repo_root),
                 "work_lib": self.work_lib},
            )
            print("[AId-VO] compile:", " ".join(argv))
            rc = subprocess.run(argv, cwd=str(self.repo_root)).returncode
            if rc != 0:
                return rc
        return 0

    # ---------------------------------------------------------------- simulate
    def run(
        self,
        run_dir: Path,
        seed: int,
        plusargs: Sequence[str] = (),
        extra: Sequence[str] = (),
    ) -> SimResult:
        run_dir = Path(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        log_file = run_dir / "transcript.log"
        cmd = self.build_simulate_command(run_dir, seed, plusargs, extra)

        timed_out = False
        start = time.monotonic()
        with open(run_dir / "vsim_stdout.log", "wb") as out_fh:
            try:
                rc = subprocess.run(
                    cmd,
                    cwd=str(run_dir),
                    stdout=out_fh,
                    stderr=subprocess.STDOUT,
                    timeout=self.timeout_s,
                    check=False,
                ).returncode
            except subprocess.TimeoutExpired:
                rc = -9
                timed_out = True
            except FileNotFoundError as exc:
                rc = -1
                timed_out = False
                with open(run_dir / "vsim_stdout.log", "ab") as fh:
                    fh.write(("\n[AId-VO] failed to launch simulator: %s\n" % exc).encode())
        wall = time.monotonic() - start

        text = ""
        if log_file.is_file():
            text = log_file.read_text(encoding="utf-8", errors="replace")
        stats = parse_transcript(text, self.cfg.log_parse)

        return SimResult(
            run_dir=run_dir,
            log_file=log_file,
            command=cmd,
            returncode=rc,
            wall_time_s=wall,
            stats=stats,
            coverage_pct=stats.coverage_pct,
            timed_out=timed_out,
        )

    # -------------------------------------------------------- coverage (ucdb)
    def merge_ucdb(self, out_ucdb: Path, inputs: Sequence[Path]) -> bool:
        template = self.cfg.commands.get("merge_coverage")
        if not template:
            return False
        mapping = {"out": str(out_ucdb), "inputs": ""}
        argv: List[str] = []
        for token in template:
            if token == "{inputs}":
                argv.extend(str(p) for p in inputs)
            else:
                argv.append(_subst(token, mapping))
        rc = subprocess.run(argv, cwd=str(self.repo_root)).returncode
        return rc == 0 and Path(out_ucdb).is_file()

    def report_total(self, ucdb: Path, out_file: Path) -> Optional[float]:
        """Scalar TOTAL coverage percentage from a vendor report - the only
        coverage quantity AId-VO is allowed to observe in ucdb mode."""
        template = self.cfg.commands.get("coverage_report")
        if not template:
            return None
        mapping = {"ucdb": str(ucdb), "out_file": str(out_file), "out": str(out_file)}
        argv = build_tokens(template, mapping)
        rc = subprocess.run(argv, cwd=str(self.repo_root)).returncode
        if rc != 0 or not Path(out_file).is_file():
            return None
        text = Path(out_file).read_text(encoding="utf-8", errors="replace")
        return parse_report_total(text, str(self.cfg.coverage.get("report_total_regex", "")))
