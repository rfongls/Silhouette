"""Feature flag coverage for the legacy standalone pipeline UI."""

import importlib
import os
import sys
from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from fastapi.testclient import TestClient

@contextmanager
def set_env(**overrides: str):
    """Temporarily set environment variables for the duration of a context."""

    previous = {key: os.environ.get(key) for key in overrides}
    try:
        os.environ.update({key: str(value) for key, value in overrides.items()})
        yield
    finally:
        for key, old_value in previous.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value

@contextmanager
def patched_insights_store():
    """Provide a lightweight insights.store stub to avoid heavy engine imports."""

    module_names = ["insights", "insights.store", "insights.models"]
    previous_modules = {name: sys.modules.get(name) for name in module_names}
    for name in module_names:
        sys.modules.pop(name, None)

    class _FakeProfile(SimpleNamespace):
        pass

    class _FakeStore:
        def __init__(self) -> None:
            self._profiles: dict[str, list[_FakeProfile]] = {
                "transform": [],
                "deid": [],
                "validate": [],
            }
            self._next_id = 1

        @classmethod
        def from_env(cls, url: str | None = None) -> "_FakeStore":
            return cls()

        def list_profiles(self, kind: str) -> list[_FakeProfile]:
            return list(self._profiles.get(kind, []))

        def create_profile(
            self,
            *,
            kind: str,
            name: str,
            description: str | None = None,
            config: dict | None = None,
        ) -> _FakeProfile:
            profile = _FakeProfile(
                id=self._next_id,
                kind=kind,
                name=name,
                description=description,
                config=config or {},
            )
            self._next_id += 1
            self._profiles.setdefault(kind, []).append(profile)
            return profile

        def update_profile(
            self,
            profile_id: int,
            *,
            name: str | None = None,
            description: str | None = None,
        ) -> bool:
            for profiles in self._profiles.values():
                for profile in profiles:
                    if profile.id == profile_id:
                        if name is not None:
                            profile.name = name
                        if description is not None:
                            profile.description = description
                        return True
            return False

        def delete_profile(self, profile_id: int) -> bool:
            for profiles in self._profiles.values():
                for index, profile in enumerate(profiles):
                    if profile.id == profile_id:
                        profiles.pop(index)
                        return True
            return False

        def ensure_schema(self) -> None:  # pragma: no cover - noop for stub
            return None

    fake_store = _FakeStore()

    def _get_store() -> _FakeStore:
        return fake_store

    stub_store = ModuleType("insights.store")
    stub_store.InsightsStore = _FakeStore
    stub_store.get_store = _get_store
    stub_store.reset_store = lambda: None

    stub_models = ModuleType("insights.models")

    stub_package = ModuleType("insights")
    stub_package.__path__ = []  # mark as package
    stub_package.store = stub_store
    stub_package.models = stub_models
    stub_package.InsightsStore = _FakeStore
    stub_package.get_store = _get_store
    stub_package.reset_store = lambda: None

    sys.modules["insights.store"] = stub_store
    sys.modules["insights.models"] = stub_models
    sys.modules["insights"] = stub_package

    try:
        yield
    finally:
        for name in module_names:
            if previous_modules[name] is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous_modules[name]


@contextmanager
def fresh_app():
    """Yield the FastAPI app with patched dependencies and restored modules."""

    module_name = "server"
    with patched_insights_store():
        if module_name in sys.modules:
            del sys.modules[module_name]
        module = importlib.import_module(module_name)
        try:
            yield getattr(module, "app")
        finally:
            sys.modules.pop(module_name, None)


def test_standalone_enabled_by_default():
    with set_env(SILH_STANDALONE_ENABLE="1"):
        with fresh_app() as app:
            assert any(
                getattr(route, "path", None) == "/ui/standalone/pipeline"
                for route in app.router.routes
            )


def test_standalone_disabled_when_flag_off():
    with set_env(SILH_STANDALONE_ENABLE="0"):
        with fresh_app() as app:
            assert not any(
                getattr(route, "path", None) == "/ui/standalone/pipeline"
                for route in app.router.routes
            )


def test_core_v2_routes_unaffected_when_flag_off():
    v2_ui_path = "/ui/interop"
    with set_env(SILH_STANDALONE_ENABLE="0"):
        with fresh_app() as app:
            # Route lookup should succeed regardless of the standalone toggle.
            assert app.url_path_for("ui_interop_hub") == v2_ui_path


def test_flat_compat_path_redirects_when_enabled():
    with set_env(SILH_STANDALONE_ENABLE="1"):
        with fresh_app() as app:
            assert app.url_path_for("_compat_standalone_pipeline") == "/ui/standalonepipeline"
            paths = [getattr(route, "path", None) for route in app.router.routes]
            assert paths.index("/ui/standalonepipeline") < paths.index("/ui/{page:path}")
            with TestClient(app) as client:
                response = client.get("/ui/standalonepipeline", follow_redirects=False)
                assert response.status_code == 307
                assert response.headers["location"] == "/ui/standalone/pipeline"
