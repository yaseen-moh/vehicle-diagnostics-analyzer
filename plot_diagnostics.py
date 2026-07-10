"""Visualizes total repair cost by system and the top cascading-risk vehicles."""
import matplotlib.pyplot as plt
from diagnostics import connect, top_cost_systems, cascading_risk_score

conn = connect()
costs = top_cost_systems(conn, limit=10)
risk = cascading_risk_score(conn).head(8)

fig, axes = plt.subplots(1, 2, figsize=(13, 5))

axes[0].barh(costs["system"], costs["total_cost"], color="steelblue")
axes[0].invert_yaxis()
axes[0].set_xlabel("Total repair cost (USD)")
axes[0].set_title("Total Repair Cost by System")

axes[1].barh(risk["vehicle_id"], risk["risk_score"], color="firebrick")
axes[1].invert_yaxis()
axes[1].set_xlabel("Cascading-failure risk score (0-100)")
axes[1].set_title("Top Vehicles by Cascading-Failure Risk")

plt.tight_layout()
plt.savefig("diagnostics_overview.png", dpi=150)
print("Saved diagnostics_overview.png")
conn.close()
