from vrp_demo.io.example_data import load_wellington_example


def test_wellington_example_uses_verified_public_land_locations() -> None:
    orders, vehicles, depot, scenario = load_wellington_example()

    assert len(orders) == 10
    assert len(vehicles) == 3
    assert scenario.scenario_id == "wellington-demo"
    assert (
        depot.name,
        depot.address,
        depot.suburban,
        depot.city,
        depot.latitude,
        depot.longitude,
    ) == (
        "NZ Post Wellington Super Depot",
        "8 Carmel Terrace",
        "Grenada Village",
        "Wellington",
        -41.2007115,
        174.8255637,
    )

    assert all(
        order.customer_name and order.suburban and order.address and order.city for order in orders
    )
    assert {order.city for order in orders} == {"Wellington"}
    assert len({(order.latitude, order.longitude) for order in orders}) == 10
    assert all(-41.35 < order.latitude < -41.19 for order in orders)
    assert all(174.73 < order.longitude < 174.84 for order in orders)
    assert {order.suburban for order in orders} >= {
        "Churton Park",
        "Johnsonville",
        "Karori",
        "Miramar",
        "Kilbirnie",
        "Island Bay",
        "Te Aro",
        "Thorndon",
        "Wellington Central",
    }
