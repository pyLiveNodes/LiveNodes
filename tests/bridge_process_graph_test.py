import os
import subprocess
import sys

import pytest

CASES = os.path.join(os.path.dirname(__file__), "_bridge_graph_cases.py")


@pytest.mark.parametrize("case", ["late_receiver_with_empty_input", "cross_sending_processes"])
def test_process_graph_finishes_and_delivers(case):
    out = subprocess.run([sys.executable, CASES, case], capture_output=True, text=True, timeout=60).stdout
    line = [l for l in out.splitlines() if l.startswith("RESULT")]
    assert line, out[-2000:]
    _, delivered, finished = line[-1].split()
    assert delivered == "True", "the sink never processed its input"
    assert finished == "True", "the graph did not finish"
