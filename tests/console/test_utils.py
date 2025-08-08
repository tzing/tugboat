from tugboat.console.utils import DiagnosesCounter, format_loc


class TestFormatLoc:
    def test(self):
        assert format_loc(["a", "b", "c"]) == ".a.b.c"
        assert format_loc(()) == "."


class TestDiagnosesCounter:

    def test_pass(self):
        counter = DiagnosesCounter()
        assert counter.summary() == "All passed!"
        assert not counter.has_any_error()

    def test_errors(self):
        counter = DiagnosesCounter(["error"])
        assert counter.summary() == "Found 1 errors"
        assert counter.has_any_error()

    def test_failures(self):
        counter = DiagnosesCounter(["failure"])
        assert counter.summary() == "Found 1 failures"
        assert counter.has_any_error()

    def test_warning(self):
        counter = DiagnosesCounter(["warning"])
        assert counter.summary() == "Found 1 warnings"
        assert not counter.has_any_error()

    def test_mixed(self):
        counter = DiagnosesCounter()
        counter["error"] += 1
        counter["error"] += 1
        counter["failure"] += 1
        counter["warning"] += 1
        assert counter.summary() == "Found 2 errors, 1 failures and 1 warnings"
        assert counter.has_any_error()
