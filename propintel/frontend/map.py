"""PropIntel — suburb intelligence map.

Run:
    cd propintel/
    streamlit run frontend/map.py
    (uvicorn api.main:app --port 8000 must be running)
"""

import mapclassify
import numpy as np
import requests
import streamlit as st
import pydeck as pdk

API_BASE = "http://localhost:8000"

_PURPLES_10 = [
    [242, 240, 247],
    [218, 218, 235],
    [188, 189, 220],
    [158, 154, 200],
    [128, 125, 186],
    [106, 81, 163],
    [84, 39, 143],
    [63, 0, 125],
    [44, 0, 88],
    [30, 0, 60],
]

st.set_page_config(layout="wide", page_title="PropIntel — Suburb Explorer")
st.title("PropIntel — Melbourne Suburb Explorer")


@st.cache_data(ttl=300, show_spinner=False)
def fetch_colored_suburbs() -> dict:
    raw = requests.get(f"{API_BASE}/suburbs").json()
    prices = [
        f["properties"]["latest_median_house_price"]
        for f in raw["features"]
        if f["properties"]["latest_median_house_price"] is not None
    ]
    classifier = mapclassify.NaturalBreaks(np.array(prices), k=10)

    features = []
    for f in raw["features"]:
        price = f["properties"]["latest_median_house_price"]
        sal_name = f["properties"]["sal_name"]
        change = f["properties"]["house_price_1y_change"]
        if price is not None:
            bin_idx = min(classifier.find_bin([price]).item(), 9)
            color = _PURPLES_10[bin_idx] + [110]
            change_str = f"{change:+.1f}%" if change is not None else "n/a"
            tooltip_html = (
                f"<b>{sal_name}</b><br/>"
                f"Median: ${price:,.0f}<br/>"
                f"1y change: {change_str}"
            )
        else:
            color = [160, 160, 160, 110]
            tooltip_html = f"<b>{sal_name}</b><br/>No price data"
        features.append(
            {
                **f,
                "properties": {
                    **f["properties"],
                    "_color": color,
                    "_tooltip": tooltip_html,
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "features": features,
        "classifier": classifier,
    }


@st.cache_data(ttl=300, show_spinner=False)
def fetch_school_zones() -> dict:
    return requests.get(f"{API_BASE}/school-zones").json()


suburbs = fetch_colored_suburbs()
school_zones = fetch_school_zones()

# --- Sidebar controls ---
st.sidebar.header("Layers")
zone_options = ["Off", "Primary", "Y7", "Y8", "Y9", "Y10", "Y11", "Y12"]
selected_zone = st.sidebar.selectbox("School zones", zone_options)
font_size = st.sidebar.number_input(
    "Label size", min_value=8, max_value=20, value=12, step=1
)

# --- Layers ---
active_metric = "house_price"
suburb_cache_key = f"suburb_layer_{active_metric}"
if suburb_cache_key not in st.session_state:
    st.session_state[suburb_cache_key] = pdk.Layer(
        "GeoJsonLayer",
        data=suburbs,
        get_fill_color="properties._color",
        get_line_color=[255, 255, 255, 60],
        line_width_min_pixels=1,
        pickable=True,
        auto_highlight=True,
        highlight_color=[255, 220, 0, 200],
    )
suburb_layer = st.session_state[suburb_cache_key]

layers = []

if selected_zone != "Off":
    zone_level = "primary" if selected_zone == "Primary" else selected_zone
    zone_cache_key = f"zone_{selected_zone}"

    if zone_cache_key not in st.session_state:
        filtered_zones = {
            "type": "FeatureCollection",
            "features": [
                f
                for f in school_zones["features"]
                if f["properties"]["zone_level"] == zone_level
            ],
        }
        st.session_state[zone_cache_key] = pdk.Layer(
            "GeoJsonLayer",
            data=filtered_zones,
            get_fill_color=[0, 0, 0, 0],
            get_line_color=[0, 0, 0, 100],
            line_width_min_pixels=1.5,
            pickable=False,
        )
        st.session_state[f"{zone_cache_key}_data"] = filtered_zones

    school_geojson_layer = st.session_state[zone_cache_key]
    filtered_zones = st.session_state[f"{zone_cache_key}_data"]
    text_data = [
        {
            "position": [
                f["properties"]["centroid_lng"],
                f["properties"]["centroid_lat"],
            ],
            "name": f["properties"]["school_name"],
        }
        for f in filtered_zones["features"]
        if f["properties"].get("centroid_lng") is not None
    ]
    text_layer = pdk.Layer(
        "TextLayer",
        data=text_data,
        get_position="position",
        get_text="name",
        get_size=font_size,
        get_color=[0, 0, 0, 200],
        pickable=False,
    )
    layers.append(school_geojson_layer)
    layers.append(text_layer)

layers.append(suburb_layer)

# --- Map ---
view_state = pdk.ViewState(
    latitude=-37.8136,
    longitude=144.9631,
    zoom=10,
    pitch=0,
)

tooltip = {
    "html": "{_tooltip}",
    "style": {
        "backgroundColor": "#1e1e2e",
        "color": "white",
        "fontSize": "13px",
        "padding": "8px",
    },
}

st.pydeck_chart(
    pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style="light",
        tooltip=tooltip,
    ),
    use_container_width=True,
    height=750,
)

# --- Legend ---
bounds = suburbs["classifier"].bins
st.caption(
    f"Choropleth: median house price  |  "
    f"${bounds[0]:,.0f} → ${bounds[-1]:,.0f}  |  "
    f"Grey = no price data"
)
