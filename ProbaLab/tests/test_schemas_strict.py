"""All request schemas must have extra='forbid' (prevents mass assignment)."""
import inspect
import pydantic

from api import schemas


def test_all_schemas_forbid_extra():
    for name, obj in inspect.getmembers(schemas):
        if inspect.isclass(obj) and issubclass(obj, pydantic.BaseModel) and obj is not pydantic.BaseModel:
            config = getattr(obj, "model_config", {})
            extra = config.get("extra") if isinstance(config, dict) else getattr(config, "extra", None)
            assert extra == "forbid", (
                f"{name} must have model_config = ConfigDict(extra='forbid') "
                f"(current: extra={extra!r})"
            )
