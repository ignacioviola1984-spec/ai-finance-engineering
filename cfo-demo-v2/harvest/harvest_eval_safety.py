"""harvest_eval_safety.py - the bounded self-improvement safety suite (12/12).

Loads and runs self-improvement/tests/test_bounds.py against an isolated temp
store, captures the count and each test's human-readable description.
Emits {"passed","total","tests":[{"name","desc"}]}.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SI = os.path.join(REPO, "self-improvement")

os.environ["SELFIMPROVE_STATE_DIR"] = tempfile.mkdtemp(prefix="v2_safety_state_")
for p in (SI, os.path.join(SI, "tests")):
    sys.path.insert(0, p)

import test_bounds  # noqa: E402


def _describe(test):
    name = test._testMethodName.replace("test_", "").replace("_", " ")
    doc = test.shortDescription()
    return {"name": name, "desc": (doc or name).strip()}


def _walk(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _walk(item)
        else:
            yield item


def main():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(test_bounds)
    tests = [_describe(t) for t in _walk(suite) if hasattr(t, "_testMethodName")]
    buf = io.StringIO()
    with redirect_stdout(buf):
        runner = unittest.TextTestRunner(stream=buf, verbosity=0)
        res = runner.run(suite)
    total = res.testsRun
    failed = len(res.failures) + len(res.errors)
    result = {"passed": total - failed, "total": total, "tests": tests}
    sys.__stdout__.write(json.dumps(result, default=str))


if __name__ == "__main__":
    main()
