"""The entry point: the exit-code contract with CI, and `.env` resolution.

Exit 2 means a job failed and exit 4 means bad input. Typer's
`exists`/`dir_okay`/`readable` checks exit 2, so `prechange` validates its
input file itself.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from dotenv import find_dotenv
from typer.testing import CliRunner

import nac_analytics
from nac_analytics.cli import app, main
from nac_analytics.core.exceptions import AnomalyThresholdError, InputError, JobError
from nac_analytics.core.report import DEFAULT_FAIL_ON, Result, build_verdict
from nac_analytics.products.nexus_dashboard.cli import _enforce, _prechange_ui_url
from nac_analytics.products.nexus_dashboard.settings import apply_legacy_env_aliases

runner = CliRunner()

# Enough configuration to reach the file checks. No request is made: the
# input is rejected before any client is constructed.
ENV = {
    "ND_HOST": "nd.example.com",
    "ND_USER": "admin",
    "ND_PASSWORD": "s3cr3t",
    "ND_FABRIC": "FABRIC-A",
}


def test_exit_codes_for_bad_input_and_failed_jobs_do_not_collide() -> None:
    assert InputError.exit_code != JobError.exit_code


def test_enforce_raises_exit_3_when_decision_is_fail() -> None:
    summary = {
        "newAnomaliesCount": 2,
        "anomalyCountBySeverity": [
            {"severity": "major", "newCount": 2, "clearedCount": 0},
        ],
    }
    result = Result(
        command="prechange",
        fabric="FABRIC-A",
        verdict=build_verdict(summary, DEFAULT_FAIL_ON),
    )

    with pytest.raises(AnomalyThresholdError) as caught:
        _enforce(result)

    assert caught.value.exit_code == 3
    assert str(caught.value).startswith("DECISION: FAIL —")


def test_enforce_does_not_raise_when_decision_is_pass() -> None:
    result = Result(
        command="prechange",
        fabric="FABRIC-A",
        verdict=build_verdict({"newAnomaliesCount": 0}, DEFAULT_FAIL_ON),
    )

    _enforce(result)


def test_a_missing_config_file_exits_4_not_click_s_usage_code(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["nd", "prechange", str(tmp_path / "absent.json")], env=ENV
    )

    assert result.exit_code == InputError.exit_code
    assert "does not exist" in result.output


def test_a_directory_in_place_of_a_config_file_exits_4(tmp_path: Path) -> None:
    result = runner.invoke(app, ["nd", "prechange", str(tmp_path)], env=ENV)

    assert result.exit_code == InputError.exit_code
    assert "is not a file" in result.output


def test_an_empty_config_file_exits_4(tmp_path: Path) -> None:
    empty = tmp_path / "empty.json"
    empty.write_text("   \n")

    result = runner.invoke(app, ["nd", "prechange", str(empty)], env=ENV)

    assert result.exit_code == InputError.exit_code
    assert "is empty" in result.output


def test_prechange_requires_config_or_job_id() -> None:
    result = runner.invoke(app, ["nd", "prechange"], env=ENV)

    assert result.exit_code == InputError.exit_code
    assert "unless --job-id" in result.output


def test_prechange_rejects_both_config_and_job_id(tmp_path: Path) -> None:
    plan = tmp_path / "plan.json"
    plan.write_text('{"imdata": []}')

    result = runner.invoke(
        app,
        ["nd", "prechange", str(plan), "--job-id", "abc123"],
        env=ENV,
    )

    assert result.exit_code == InputError.exit_code
    assert "not both" in result.output


# -- .env resolution -------------------------------------------------------


@pytest.fixture
def restore_environ() -> Iterator[None]:
    """Undo the changes `load_dotenv` makes directly to `os.environ`."""
    saved = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(saved)


def run_main(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run the entry point for the nd group. Typer prints help and exits."""
    monkeypatch.setattr(sys, "argv", ["nac-analytics", "nd"])
    with pytest.raises(SystemExit):
        main()


def test_a_dotenv_in_the_working_directory_is_loaded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, restore_environ: None
) -> None:
    (tmp_path / ".env").write_text("ND_HOST=cwd.example.com\n")
    monkeypatch.chdir(tmp_path)
    os.environ.pop("ND_HOST", None)

    run_main(monkeypatch)

    assert os.environ["ND_HOST"] == "cwd.example.com"


def test_the_dotenv_is_resolved_from_the_working_directory_not_the_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, restore_environ: None
) -> None:
    """The path handed to `load_dotenv` is the one below the working directory."""
    package_tree = Path(nac_analytics.__file__).resolve().parent.parent
    (tmp_path / ".env").write_text("ND_HOST=cwd.example.com\n")
    monkeypatch.chdir(tmp_path)
    loaded: list[str] = []

    def spy(path: str = "") -> bool:
        loaded.append(path)
        return True

    monkeypatch.setattr("nac_analytics.cli.load_dotenv", spy)

    run_main(monkeypatch)

    assert loaded == [str(tmp_path / ".env")]
    assert package_tree not in Path(loaded[0]).resolve().parents


def test_find_dotenv_reports_nothing_when_no_file_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty path is what `load_dotenv` receives when there is no file."""
    monkeypatch.chdir(tmp_path)

    assert find_dotenv(usecwd=True) == ""


def test_a_real_environment_variable_beats_the_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, restore_environ: None
) -> None:
    (tmp_path / ".env").write_text("ND_HOST=cwd.example.com\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ND_HOST", "real.example.com")

    run_main(monkeypatch)

    assert os.environ["ND_HOST"] == "real.example.com"


def test_running_without_a_dotenv_does_not_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, restore_environ: None
) -> None:
    monkeypatch.chdir(tmp_path)
    os.environ.pop("ND_HOST", None)

    run_main(monkeypatch)

    assert "ND_HOST" not in os.environ


def test_prechange_ui_url_points_at_the_nd_prechange_page() -> None:
    assert _prechange_ui_url("https://nd.example.com") == (
        "https://nd.example.com/appcenter/cisco/nexus-insights/ui/"
        "#/changeManagement/preChangeAnalysis"
    )


def test_root_help_lists_product_groups_not_env_vars() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "nexus-dashboard" in result.output
    assert "version" in result.output
    # Product-specific env config lives under the product help, not the root.
    assert "ND_HOST" not in result.output
    assert "Configuration:" not in result.output


def test_nexus_dashboard_help_lists_configuration_variables() -> None:
    result = runner.invoke(app, ["nd", "--help"])

    assert result.exit_code == 0
    assert "Configuration:" in result.output
    assert "ND_HOST" in result.output
    assert "ND_CONFIG" in result.output
    assert "nac-analytics.yaml" in result.output
    assert ".env" in result.output
    assert "ND_VERIFY_TLS" in result.output


def test_nd_verify_tls_is_mapped_when_nd_verify_ssl_is_unset(
    restore_environ: None,
) -> None:
    os.environ.pop("ND_VERIFY_SSL", None)
    os.environ["ND_VERIFY_TLS"] = "false"

    apply_legacy_env_aliases()

    assert os.environ["ND_VERIFY_SSL"] == "false"


def test_nd_verify_ssl_wins_over_the_legacy_tls_alias(
    restore_environ: None,
) -> None:
    os.environ["ND_VERIFY_SSL"] = "true"
    os.environ["ND_VERIFY_TLS"] = "false"

    apply_legacy_env_aliases()

    assert os.environ["ND_VERIFY_SSL"] == "true"


def test_a_dotenv_with_only_nd_verify_tls_is_honoured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, restore_environ: None
) -> None:
    (tmp_path / ".env").write_text("ND_VERIFY_TLS=false\n")
    monkeypatch.chdir(tmp_path)
    os.environ.pop("ND_VERIFY_SSL", None)
    os.environ.pop("ND_VERIFY_TLS", None)

    run_main(monkeypatch)

    assert os.environ["ND_VERIFY_SSL"] == "false"


def test_compliance_all_and_fabric_together_exit_4() -> None:
    result = runner.invoke(
        app,
        ["nd", "compliance", "--all", "--fabric", "FABRIC-A"],
        env=ENV,
    )

    assert result.exit_code == InputError.exit_code
    assert "cannot be combined" in result.output


# -- --help must never require config (regression) -------------------------
#
# Config is bootstrapped in `main()` before Typer runs, so these go through
# `main()` (not CliRunner, which bypasses bootstrap) with a flat/invalid
# `nac-analytics.yaml` in the cwd — the exact conditions that used to make a
# plain `--help` exit 4 with a config error.

FLAT_CONFIG = "host: nd.example.com\nfabric: FABRIC-A\n"


@pytest.mark.parametrize(
    ("argv", "needle"),
    [
        (["nac-analytics", "--help"], "nexus-dashboard"),
        (["nac-analytics", "nexus-dashboard", "--help"], "Configuration:"),
        (["nac-analytics", "nd", "--help"], "Configuration:"),
        (["nac-analytics", "nexus-dashboard", "prechange", "--help"], "prechange"),
        (["nac-analytics", "nexus-dashboard", "delta", "--help"], "delta"),
        (["nac-analytics", "nd", "prechange", "--help"], "prechange"),
    ],
)
def test_help_exits_0_even_with_flat_config_in_cwd(
    argv: list[str],
    needle: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    restore_environ: None,
) -> None:
    (tmp_path / "nac-analytics.yaml").write_text(FLAT_CONFIG)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", argv)

    with pytest.raises(SystemExit) as caught:
        main()

    assert caught.value.code == 0
    out = capsys.readouterr().out
    assert "Usage" in out
    assert needle in out


@pytest.mark.parametrize(
    "argv",
    [
        ["nac-analytics", "nexus-dashboard", "--help"],
        ["nac-analytics", "nexus-dashboard", "prechange", "--help"],
    ],
)
def test_help_exits_0_even_with_invalid_config_in_cwd(
    argv: list[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    restore_environ: None,
) -> None:
    (tmp_path / "nac-analytics.yaml").write_text("::: not valid yaml : : :\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", argv)

    with pytest.raises(SystemExit) as caught:
        main()

    assert caught.value.code == 0
    assert "Usage" in capsys.readouterr().out


def test_a_real_command_with_flat_config_still_exits_4(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    restore_environ: None,
) -> None:
    """The strict nested-scope validation still fires for actual runs."""
    (tmp_path / "nac-analytics.yaml").write_text(FLAT_CONFIG)
    (tmp_path / "plan.json").write_text('{"imdata": []}')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys, "argv", ["nac-analytics", "nexus-dashboard", "prechange", "plan.json"]
    )

    with pytest.raises(SystemExit) as caught:
        main()

    assert caught.value.code == InputError.exit_code
    assert "nexus_dashboard:" in capsys.readouterr().err
