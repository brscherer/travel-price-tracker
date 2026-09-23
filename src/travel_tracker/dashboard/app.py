"""Streamlit dashboard. Run via `python -m travel_tracker dashboard`
(needs `pip install -e ".[dashboard]"` first) or directly with
`streamlit run src/travel_tracker/dashboard/app.py`.

Absolute imports below are deliberate: Streamlit executes this file as a
standalone script, not as part of the `travel_tracker` package, so relative
imports (`from ..config import ...`) would fail. Absolute imports work
because the package is installed (editable) into the active venv.
"""

from __future__ import annotations

import streamlit as st

from travel_tracker.config import load_config, load_secrets
from travel_tracker.dashboard import data as dashboard_data
from travel_tracker.db.models import connect

st.set_page_config(page_title="travel-price-tracker", page_icon="✈️", layout="wide")

_ALERT_LABELS = {
    "transfer_bonus": "\U0001f3af Transfer bonus",
    "miles_sale": "\U0001f4b0 Miles sale",
    "promo": "\U0001f4e2 Promo",
    "hot_deal": "\U0001f525 Hot deal",
    "error_fare": "\U0001f6a8 Error fare?",
    "target_price": "\U0001f3af Target price",
}


@st.cache_resource
def get_connection():
    secrets = load_secrets()
    return connect(secrets.database_path)


def main() -> None:
    st.title("POA flight-deal tracker")

    conn = get_connection()
    load_config()  # validates config.yaml is readable; not otherwise used here

    tab_deals, tab_charts, tab_promos = st.tabs(["Today's deals", "Price charts", "Active promos"])

    with tab_deals:
        st.subheader("Deals alerted in the last 24h")
        deals = dashboard_data.load_recent_deals(conn, hours=24)
        if deals.empty:
            st.info("No deals alerted in the last 24 hours.")
        else:
            deals["alert_type"] = deals["alert_type"].map(lambda t: _ALERT_LABELS.get(t, t))
            st.dataframe(deals, use_container_width=True, hide_index=True)

    with tab_charts:
        st.subheader("Price history per route")
        routes = dashboard_data.load_routes(conn)
        if routes.empty:
            st.info("No route data yet -- run a scan first.")
        else:
            routes = routes.copy()
            routes["label"] = routes["origin"] + " -> " + routes["destination"] + " (" + routes["cabin"] + ")"
            choice = st.selectbox("Route", routes["label"])
            route_id = int(routes.loc[routes["label"] == choice, "id"].iloc[0])
            days = st.slider("Days of history", min_value=7, max_value=180, value=60, step=7)

            history = dashboard_data.load_price_history(conn, route_id, days=days)
            if history.empty:
                st.info("No price snapshots yet for this route in that window.")
            else:
                daily_min = history.groupby("date")["price_brl"].min()
                st.line_chart(daily_min)
                st.caption("Daily minimum cached price across all date combinations for this route.")
                st.dataframe(
                    history.sort_values("fetched_at", ascending=False),
                    use_container_width=True,
                    hide_index=True,
                )

    with tab_promos:
        st.subheader("Promos alerted in the last 48h")
        promos = dashboard_data.load_recent_promos(conn, hours=48)
        if promos.empty:
            st.info("No promos alerted in the last 48 hours.")
        else:
            for _, row in promos.iterrows():
                label = _ALERT_LABELS.get(row["alert_type"], row["alert_type"])
                st.markdown(f"**{label}** -- {row['title'] or row['source']}")
                if row["link"]:
                    st.markdown(row["link"])
                st.caption(f"{row['source']} · {row['sent_at']}")
                st.divider()


if __name__ == "__main__":
    main()
