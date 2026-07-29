from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from vrp_demo.presentation import map_layers


@pytest.fixture(autouse=True)
def clear_streamlit_data_cache():
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def _chart_json(app: AppTest) -> str:
    charts = app.get("deck_gl_json_chart")
    assert len(charts) == 1
    return charts[0].proto.json


def _selectbox(app: AppTest, label: str):
    return next(selectbox for selectbox in app.selectbox if selectbox.label == label)


class FakeDirectionResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self):
        return {
            "code": "Ok",
            "routes": [
                {
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [174.78, -41.28],
                            [174.781234, -41.281234],
                            [174.79, -41.29],
                        ],
                    }
                }
            ],
        }


class FakeDirectionClient:
    def __init__(self) -> None:
        self.calls = 0
        self.fail = False

    def get(self, url, *, params, timeout):
        self.calls += 1
        if self.fail:
            return FakeNoRouteResponse()
        return FakeDirectionResponse()


class FakeNoRouteResponse(FakeDirectionResponse):
    def json(self):
        return {"code": "NoRoute"}


def test_default_dispatch_map_preserves_two_argument_call(monkeypatch) -> None:
    """Both line styles work when hot reload retains the previous map module."""
    original_dispatch_deck = map_layers.dispatch_deck
    call_count = 0
    direction_client = FakeDirectionClient()

    def previous_dispatch_deck(instance, solution):
        nonlocal call_count
        call_count += 1
        return original_dispatch_deck(instance, solution)

    monkeypatch.setattr(map_layers, "dispatch_deck", previous_dispatch_deck)
    monkeypatch.setattr(
        "vrp_demo.distance.route_geometry.httpx.Client",
        lambda: direction_client,
    )

    app = AppTest.from_file("app.py", default_timeout=20).run()
    _selectbox(app, "Solver").select("greedy_insertion")
    next(button for button in app.button if button.label == "Solve dispatch").click().run()

    assert not app.exception
    assert call_count == 1
    assert len(app.metric) == 6

    app.segmented_control[0].set_value("Follow roads").run()

    assert not app.exception
    assert call_count == 2
    assert direction_client.calls > 0
    assert "174.781234" in app.get("deck_gl_json_chart")[-1].proto.json


def test_scenario_map_reacts_across_input_modes(monkeypatch) -> None:
    direction_client = FakeDirectionClient()
    monkeypatch.setattr(
        "vrp_demo.distance.route_geometry.httpx.Client",
        lambda: direction_client,
    )
    app = AppTest.from_file("app.py", default_timeout=20).run()
    assert not app.exception
    assert _chart_json(app).count('"status": "ORDER"') == 10

    _selectbox(app, "Solver").select("greedy_insertion")
    app.button[0].click().run()
    assert len(app.metric) == 6
    assert app.segmented_control[0].value == "Straight lines"
    assert not any(selectbox.label == "Direction service" for selectbox in app.selectbox)
    assert direction_client.calls == 0
    app.segmented_control[0].set_value("Follow roads").run()
    assert not app.exception
    assert any(selectbox.label == "Direction service" for selectbox in app.selectbox)
    assert direction_client.calls > 0
    assert "174.781234" in app.get("deck_gl_json_chart")[-1].proto.json

    _selectbox(app, "Input mode").select("Generated instance").run()
    generated_orders = next(slider for slider in app.slider if slider.label == "Generated orders")
    generated_orders.set_value(3).run()
    assert not app.exception
    assert _chart_json(app).count('"status": "ORDER"') == 3
    assert not app.metric
    direction_client.fail = True
    next(button for button in app.button if button.label == "Solve dispatch").click().run()
    app.segmented_control[0].set_value("Follow roads").run()
    assert not app.exception
    assert any("Showing straight lines instead" in item.value for item in app.warning)

    _selectbox(app, "Input mode").select("Manual tables").run()
    assert not app.exception
    assert [item.value for item in app.subheader[:3]] == ["Depot", "Orders", "Vehicles"]
    assert _chart_json(app).count('"status": "ORDER"') == 10

    _selectbox(app, "Input mode").select("CSV upload").run()
    assert not app.get("deck_gl_json_chart")
    directory = Path("data/wellington")
    for uploader, filename in zip(
        app.file_uploader,
        ("orders.csv", "vehicles.csv", "depots.csv"),
        strict=True,
    ):
        uploader.upload(filename, (directory / filename).read_bytes(), "text/csv")
    app.run()

    assert not app.exception
    assert _chart_json(app).count('"status": "ORDER"') == 10
