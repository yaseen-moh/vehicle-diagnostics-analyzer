"""
Vehicle Repair & Failure-Pattern Analyzer
--------------------------------------------
SQL + pandas analysis over a shop repair-ticket database: which systems
fail together (cascading failure patterns), which vehicles/systems are
costing the most, and a simple heuristic "cascading failure risk" score
per vehicle based on how many distinct systems have shown symptoms in a
short mileage window -- the kind of pattern-recognition that comes from
diagnosing real cascading failures across drive, power, and structural
systems under time pressure (e.g. mid-competition, or reasoning from
first principles when a failure spans multiple interconnected systems).

Author: Yaseen Mohamed
"""
from __future__ import annotations
import sqlite3
import pandas as pd


def connect(path: str = "shop_repairs.db") -> sqlite3.Connection:
    return sqlite3.connect(path)


def top_cost_systems(conn: sqlite3.Connection, limit: int = 10) -> pd.DataFrame:
    """Which systems account for the most total repair spend across the fleet?"""
    query = """
        SELECT system,
               COUNT(*)              AS ticket_count,
               ROUND(SUM(cost_usd), 2)   AS total_cost,
               ROUND(AVG(cost_usd), 2)   AS avg_cost,
               ROUND(SUM(labor_hours), 1) AS total_labor_hours
        FROM repair_tickets
        GROUP BY system
        ORDER BY total_cost DESC
        LIMIT ?
    """
    return pd.read_sql_query(query, conn, params=(limit,))


def vehicle_repair_history(conn: sqlite3.Connection, vehicle_id: str) -> pd.DataFrame:
    """Full chronological repair history for a single vehicle."""
    query = """
        SELECT service_date, mileage, system, symptom, repair_performed,
               labor_hours, cost_usd
        FROM repair_tickets
        WHERE vehicle_id = ?
        ORDER BY service_date ASC
    """
    return pd.read_sql_query(query, conn, params=(vehicle_id,))


def cascading_failure_candidates(conn: sqlite3.Connection,
                                  mileage_window: int = 3000,
                                  min_systems: int = 3) -> pd.DataFrame:
    """
    Flags vehicles where `min_systems` or more DISTINCT systems showed up
    in repair tickets within a `mileage_window`-mile span -- a proxy for
    a cascading-failure pattern (one root cause creating downstream
    symptoms across multiple interconnected systems) rather than
    unrelated, independent repairs spread across a vehicle's life.
    """
    query = """
        SELECT vehicle_id, service_date, mileage, system, symptom
        FROM repair_tickets
        ORDER BY vehicle_id, mileage
    """
    df = pd.read_sql_query(query, conn)

    results = []
    for vehicle_id, group in df.groupby("vehicle_id"):
        group = group.sort_values("mileage").reset_index(drop=True)
        mileages = group["mileage"].values
        for i in range(len(group)):
            window_mask = (mileages >= mileages[i]) & (mileages <= mileages[i] + mileage_window)
            window = group[window_mask]
            n_systems = window["system"].nunique()
            if n_systems >= min_systems:
                results.append({
                    "vehicle_id": vehicle_id,
                    "window_start_mileage": mileages[i],
                    "window_end_mileage": mileages[i] + mileage_window,
                    "distinct_systems_affected": n_systems,
                    "systems": ", ".join(sorted(window["system"].unique())),
                    "ticket_count_in_window": len(window),
                })

    if not results:
        return pd.DataFrame(columns=["vehicle_id", "window_start_mileage",
                                      "window_end_mileage", "distinct_systems_affected",
                                      "systems", "ticket_count_in_window"])

    out = pd.DataFrame(results)
    # keep only the strongest (widest) window per vehicle to avoid duplicate
    # overlapping windows cluttering the output
    out = out.sort_values("distinct_systems_affected", ascending=False)
    out = out.drop_duplicates(subset="vehicle_id", keep="first")
    return out.sort_values("distinct_systems_affected", ascending=False).reset_index(drop=True)


def cascading_risk_score(conn: sqlite3.Connection, mileage_window: int = 3000) -> pd.DataFrame:
    """
    A simple 0-100 heuristic risk score per vehicle: combines how many
    distinct systems clustered together in a short mileage window with
    how many total tickets that vehicle has filed. Meant as a triage
    signal for "which vehicles are worth a deeper diagnostic look",
    not a certified prediction.
    """
    candidates = cascading_failure_candidates(conn, mileage_window=mileage_window, min_systems=1)
    if candidates.empty:
        return candidates

    max_systems = candidates["distinct_systems_affected"].max()
    max_tickets = candidates["ticket_count_in_window"].max()

    candidates["risk_score"] = (
        60 * (candidates["distinct_systems_affected"] / max_systems) +
        40 * (candidates["ticket_count_in_window"] / max_tickets)
    ).round(1)

    return candidates.sort_values("risk_score", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    conn = connect()

    print("=== Top systems by total repair cost across the fleet ===")
    print(top_cost_systems(conn).to_string(index=False))

    print("\n=== Cascading failure candidates (3+ systems within 3,000 miles) ===")
    print(cascading_failure_candidates(conn).head(10).to_string(index=False))

    print("\n=== Top 5 vehicles by cascading-failure risk score ===")
    print(cascading_risk_score(conn).head(5).to_string(index=False))

    print("\n=== Full repair history: V-C4-88 (1988 Corvette C4 project car) ===")
    print(vehicle_repair_history(conn, "V-C4-88").to_string(index=False))

    conn.close()
