import click.testing
import pytest

from tugboat.console.main import DiagnosesCounter, main, setup_logging
from tugboat.version import __version__


@pytest.mark.usefixtures("_reset_logging")
def test_print_anchor():
    runner = click.testing.CliRunner()
    result = runner.invoke(main, ["--anchor"])

    assert result.exit_code == 0
    assert __version__ in result.output
