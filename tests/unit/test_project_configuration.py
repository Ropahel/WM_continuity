from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _read_config(name: str) -> dict:
    path = ROOT / "configs" / name
    with path.open(encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


def test_environment_config_selects_local_cube_without_external_package() -> None:
    environment = _read_config("environment.yaml")

    assert environment["name"] == "cube"
    assert environment["implementation"] == "local"
    assert environment["task"] == "to_be_defined"


def test_experiment_config_uses_cpu_and_episode_level_splits() -> None:
    experiment = _read_config("experiment.yaml")

    assert experiment["training"]["device"] == "cpu"
    assert experiment["dataset"]["split_by"] == "episode"


def test_model_config_does_not_require_trackmania_telemetry() -> None:
    model = _read_config("model.yaml")

    assert "telemetry" not in model
    assert model["observation"]["modalities"] == ["state"]
    assert model["latent"]["dimension"] > 0
