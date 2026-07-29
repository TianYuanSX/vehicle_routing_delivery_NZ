from pathlib import Path

from streamlit.testing.v1 import AppTest


def _chart_json(app: AppTest) -> str:
    charts = app.get("deck_gl_json_chart")
    assert len(charts) == 1
    return charts[0].proto.json


def test_scenario_map_reacts_across_input_modes() -> None:
    app = AppTest.from_file("app.py", default_timeout=20).run()
    assert not app.exception
    assert _chart_json(app).count('"status": "ORDER"') == 10

    app.selectbox[1].select("greedy_insertion")
    app.button[0].click().run()
    assert len(app.metric) == 6

    app.selectbox[0].select("Generated instance").run()
    generated_orders = next(slider for slider in app.slider if slider.label == "Generated orders")
    generated_orders.set_value(3).run()
    assert not app.exception
    assert _chart_json(app).count('"status": "ORDER"') == 3
    assert not app.metric

    app.selectbox[0].select("Manual tables").run()
    assert not app.exception
    assert [item.value for item in app.subheader[:3]] == ["Depot", "Orders", "Vehicles"]
    assert _chart_json(app).count('"status": "ORDER"') == 10

    app.selectbox[0].select("CSV upload").run()
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
