"""Test that sample_weight is passed via fit_params to cross_val_score."""
import ast
import pathlib

TRAIN_PATH = pathlib.Path(__file__).parent.parent / "src" / "training" / "train.py"


def test_sample_weight_uses_fit_params():
    """Regression for lesson 13: sample_weight must be in fit_params, not params."""
    tree = ast.parse(TRAIN_PATH.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if name == "cross_val_score":
                for kw in node.keywords:
                    if kw.arg == "params":
                        if isinstance(kw.value, ast.Dict):
                            keys = [k.value for k in kw.value.keys if isinstance(k, ast.Constant)]
                            assert "sample_weight" not in keys, (
                                f"At {TRAIN_PATH}:{node.lineno}, sample_weight "
                                f"is passed via params= (silently ignored). "
                                f"Use fit_params= instead (lesson 13)."
                            )
