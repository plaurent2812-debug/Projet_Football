"""Test that training pipeline never passes test set as eval_set."""

import ast
import pathlib

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
