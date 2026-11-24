"""Framework configuration for AId-UVO-RT.

Centralized, environment-variable-driven configuration. Sensible defaults are
provided so the optimizer can run with zero edits; the QuestaSim batch files
override values via environment variables.
"""

import os
from typing import Any, Dict


def _env(name: str, default: Any) -> Any:
    return os.environ.get(name, default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on", "y", "t")


class Config:
    """Runtime configuration for the optimizer."""

    # --- Mode -------------------------------------------------------------
    mode: str = _env("AID_UVO_MODE", "baseline")  # baseline | srie | blackbox | compare

    # --- AI / RL ----------------------------------------------------------
    ai_on: bool = _env_bool("AID_UVO_AI_ON", True)
    rl_algorithm: str = _env("AID_UVO_RL_ALGO", "dqn")  # qlearning | dqn | ppo

    # --- Regression control ----------------------------------------------
    num_runs: int = _env_int("AID_UVO_NUM_RUNS", 10)
    seed_mode: str = _env("AID_UVO_SEED_MODE", "random")  # random | fixed:N | list:a,b,c
    fixed_seed: int = _env_int("AID_UVO_FIXED_SEED", 42)
    seed_list: str = _env("AID_UVO_SEED_LIST", "")

    coverage_goal: float = _env_float("AID_UVO_COVERAGE_GOAL", 100.0)
    max_sim_time: str = _env("AID_UVO_MAX_SIM_TIME", "1ms")
    output_dir: str = _env("AID_UVO_OUTPUT_DIR", "results")

    # --- SRIE (runtime introspection) -------------------------------------
    srie_vpi_port: int = _env_int("SRIE_VPI_PORT", 5555)
    srie_vpi_host: str = _env("SRIE_VPI_HOST", "127.0.0.1")
    srie_vpi_dll: str = _env("SRIE_VPI_DLL", "sim/Questa/vpi/srie_vpi.dll")
    srie_event_trigger: str = _env("SRIE_EVENT_TRIGGER", "coverage_stall")

    # --- Blackbox ---------------------------------------------------------
    blackbox_log_file: str = _env("BLACKBOX_LOG_FILE", "sim.log")
    blackbox_coverage_db: str = _env("BLACKBOX_COVERAGE_DB", "coverage.ucdb")
    blackbox_report_file: str = _env("BLACKBOX_REPORT_FILE", "coverage_report.txt")

    # --- RL hyperparameters -----------------------------------------------
    rl_gamma: float = _env_float("RL_GAMMA", 0.95)
    rl_lr: float = _env_float("RL_LR", 0.01)
    rl_epsilon: float = _env_float("RL_EPSILON", 0.1)
    rl_epsilon_decay: float = _env_float("RL_EPSILON_DECAY", 0.995)
    rl_epsilon_min: float = _env_float("RL_EPSILON_MIN", 0.01)
    rl_buffer_size: int = _env_int("RL_BUFFER_SIZE", 1000)
    rl_batch_size: int = _env_int("RL_BATCH_SIZE", 32)
    rl_hidden: int = _env_int("RL_HIDDEN", 32)

    # --- QuestaSim --------------------------------------------------------
    questa_home: str = _env("QUESTA_HOME", "")
    vsim_cmd: str = _env("VSIMS_CMD", "vsim")
    vlog_cmd: str = _env("VLOG_CMD", "vlog")

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in vars(self).items() if not k.startswith("_")}

    def __repr__(self) -> str:
        items = ", ".join(f"{k}={v!r}" for k, v in self.to_dict().items())
        return f"Config({items})"


# Default (module-level) config instance.
CFG = Config()
