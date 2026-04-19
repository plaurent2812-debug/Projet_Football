"""Test that training pipeline never passes test set as eval_set."""

import ast
import pathlib

import pytest

TRAIN_PATH = pathlib.Path(__file__).parent.parent / "src" / "training" / "train.py"


def _find_fit_calls_with_eval_set(source: str) -> list[tuple[int, str]]:
    """Return list of (lineno, variable_name_passed_as_eval_set)."""
    tree = ast.parse(source)
    results = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "fit"
        ):
            for kw in node.keywords:
                if kw.arg == "eval_set":
                    # eval_set=[(X_eval, y_eval)] — extract variable names
                    if isinstance(kw.value, ast.List) and kw.value.elts:
                        elt = kw.value.elts[0]
                        if isinstance(elt, ast.Tuple) and len(elt.elts) == 2:
                            x_name = ast.unparse(elt.elts[0])
                            results.append((node.lineno, x_name))
    return results


def test_no_test_set_in_eval_set():
    """Regression test for lesson 10: eval_set must never be X_test/y_test."""
    source = TRAIN_PATH.read_text()
    fit_calls = _find_fit_calls_with_eval_set(source)
    forbidden = {"X_test", "X_test_fold", "X_test_split"}
    for lineno, x_name in fit_calls:
        assert x_name not in forbidden, (
            f"Data leakage at {TRAIN_PATH}:{lineno} — eval_set uses {x_name} "
            f"which is the test set. Use a separate X_val from train split instead."
        )


@pytest.mark.xfail(
    reason=(
        "R5 audit finding — calculate_team_strengths lacks an as_of_date "
        "parameter, causing future-leak when team strengths are computed on "
        "full-season data during backtests. Follow-up: add as_of_date and "
        "filter match_team_stats.match_date < as_of_date."
    ),
    strict=True,
)
def test_team_strengths_computed_with_match_date_filter():
    """Anti-leakage strict : calculate_team_strengths doit accepter un paramètre
    de date pour filtrer match_team_stats à match_date < as_of_date.

    Vérifie la SIGNATURE de la fonction (pas juste le body d'un caller).
    Audit §2.5 — leakage subtil R5.
    """
    import ast

    with open("src/models/stats_engine.py") as f:
        source = f.read()

    tree = ast.parse(source)

    target: ast.FunctionDef | ast.AsyncFunctionDef | None = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == "calculate_team_strengths":
                target = node
                break

    assert target is not None, "calculate_team_strengths function not found in stats_engine.py"

    param_names = {a.arg for a in target.args.args}
    param_names |= {a.arg for a in target.args.kwonlyargs}

    date_params = {
        "as_of_date",
        "match_date",
        "kickoff_date",
        "fixture_date",
        "until_date",
        "before_date",
    }

    assert param_names & date_params, (
        f"calculate_team_strengths has no date-filter parameter. "
        f"Current params: {sorted(param_names)}. "
        f"Expected one of: {sorted(date_params)}. "
        f"Add as_of_date=None and filter match_team_stats by match_date < as_of_date."
    )
