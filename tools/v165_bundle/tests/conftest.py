from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))


@pytest.fixture(autouse=True)
def forbid_real_f2c(monkeypatch):
    """Fail closed if a test reaches the workstation F2c module loader."""
    import v165_run

    marker = os.environ.get("V165_REAL_CALL_TRIPWIRE")

    def blocked(_repo):
        if marker:
            with Path(marker).open("a", encoding="ascii") as handle:
                handle.write("REAL_F2C_MODEL_LOADER_REACHED_IN_TESTS\n")
        raise AssertionError("REAL_F2C_MODEL_LOADER_REACHED_IN_TESTS")

    monkeypatch.setattr(v165_run, "_model_modules", blocked)
