import sys, os, sqlite3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generate_sample_data import build_database
from diagnostics import connect, top_cost_systems, cascading_failure_candidates, cascading_risk_score

TEST_DB = "test_shop_repairs.db"


def setup_module(module):
    build_database(path=TEST_DB, n_random_vehicles=10, n_random_tickets=50)


def teardown_module(module):
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def test_database_has_expected_tables():
    conn = sqlite3.connect(TEST_DB)
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert "vehicles" in tables
    assert "repair_tickets" in tables
    conn.close()


def test_top_cost_systems_returns_ranked_results():
    conn = connect(TEST_DB)
    result = top_cost_systems(conn, limit=5)
    assert len(result) <= 5
    assert list(result["total_cost"]) == sorted(result["total_cost"], reverse=True)
    conn.close()


def test_storyline_vehicles_flagged_as_cascading():
    conn = connect(TEST_DB)
    candidates = cascading_failure_candidates(conn, mileage_window=3000, min_systems=3)
    flagged_ids = set(candidates["vehicle_id"])
    assert "V-C4-88" in flagged_ids
    assert "V-3000GT-93" in flagged_ids
    conn.close()


def test_risk_scores_bounded_0_to_100():
    conn = connect(TEST_DB)
    risk = cascading_risk_score(conn)
    assert (risk["risk_score"] >= 0).all()
    assert (risk["risk_score"] <= 100).all()
    conn.close()


if __name__ == "__main__":
    setup_module(None)
    try:
        test_database_has_expected_tables()
        test_top_cost_systems_returns_ranked_results()
        test_storyline_vehicles_flagged_as_cascading()
        test_risk_scores_bounded_0_to_100()
        print("All tests passed.")
    finally:
        teardown_module(None)
