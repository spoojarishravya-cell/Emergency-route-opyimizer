
import streamlit as st
import folium
import html
import osmnx as ox

from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation
from geopy.geocoders import Nominatim

from services.road_network import (
    load_road_network,
    get_graph_info,
    calculate_route_metrics
)

from services.hospital_finder import find_nearby_hospitals

from services.pathfinding import bfs, ucs, astar


# =====================================================
# PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="Emergency Hospital Route Optimizer",
    page_icon="🚑",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =====================================================
# CUSTOM DARK THEME
# =====================================================

st.markdown("""
<style>
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
[data-testid="stSidebar"], [data-testid="stHeader"] {
    background-color: #071426 !important;
}
.stApp, .stApp *, [data-testid="stAppViewContainer"] *,
[data-testid="stMain"] *, [data-testid="stSidebar"] * {
    color: #eaf2ff !important;
}
h1, h2, h3, h4, h5, h6 { color: #ffffff !important; }
[data-testid="stSidebar"] > div { background-color: #0d1b2e !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] *,
.stCaption, small { color: #b8c8dc !important; }
.stTextInput input, .stTextArea textarea, [data-testid="stTextInput"] input {
    background: #ffffff !important;
    color: #071426 !important;
    -webkit-text-fill-color: #071426 !important;
    caret-color: #071426 !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"],
[data-testid="stSelectbox"] [data-baseweb="select"] div,
[data-testid="stSelectbox"] [data-baseweb="select"] span {
    background-color: #ffffff !important;
    color: #071426 !important;
    -webkit-text-fill-color: #071426 !important;
}
[data-baseweb="popover"], [data-baseweb="popover"] *,
[role="listbox"], [role="option"] {
    background-color: #ffffff !important;
    color: #071426 !important;
    -webkit-text-fill-color: #071426 !important;
}
[data-testid="stRadio"], [data-testid="stRadio"] * {
    color: #eaf2ff !important;
    -webkit-text-fill-color: #eaf2ff !important;
}
.stButton button, [data-testid="stButton"] button {
    background-color: #1677d2 !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    border: 1px solid #328fe5 !important;
    border-radius: 9px !important;
    font-weight: 700 !important;
    opacity: 1 !important;
}
.stButton button:disabled, [data-testid="stButton"] button:disabled {
    background-color: #294563 !important;
    color: #eaf2ff !important;
    -webkit-text-fill-color: #eaf2ff !important;
    opacity: 1 !important;
}
.metric-card, .hospital-card {
    background-color: #10243d !important;
    border: 1px solid #24517c !important;
    border-radius: 12px !important;
    padding: 18px !important;
    margin-bottom: 12px !important;
}
.metric-label {
    color: #c6d6e9 !important;
    -webkit-text-fill-color: #c6d6e9 !important;
    font-size: 14px;
}
.metric-value, .hospital-card h4 {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    font-size: 23px;
    font-weight: bold;
}
.hospital-card p {
    color: #d5e2f0 !important;
    -webkit-text-fill-color: #d5e2f0 !important;
}
.recommended { border: 2px solid #20c997 !important; }
.status {
    color: #20c997 !important;
    -webkit-text-fill-color: #20c997 !important;
    font-weight: bold;
}
.patient-location-status {
    background: #e9f8f0;
    color: #14532d !important;
    -webkit-text-fill-color: #14532d !important;
    border: 1px solid #86d7aa;
    border-radius: 8px;
    padding: 12px 14px;
    font-weight: 700;
}
.patient-location-status * {
    color: #14532d !important;
    -webkit-text-fill-color: #14532d !important;
}

/* Alert and information boxes */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    background-color: #eaf2ff !important;
}

[data-testid="stAlert"] *,
[data-testid="stAlert"] p,
[data-testid="stAlert"] div,
[data-testid="stAlert"] span {
    color: #071426 !important;
    -webkit-text-fill-color: #071426 !important;
}

/* Traffic condition dropdown */
[data-testid="stSelectbox"] * {
    color: #071426 !important;
    -webkit-text-fill-color: #071426 !important;
}

[data-testid="stSelectbox"] input {
    color: #071426 !important;
    -webkit-text-fill-color: #071426 !important;
}

/* Dropdown options */
[data-baseweb="popover"] *,
[role="listbox"] *,
[role="option"] * {
    color: #071426 !important;
    -webkit-text-fill-color: #071426 !important;
}

hr { border-color: #263d59 !important; }
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
</style>
""", unsafe_allow_html=True)


# =====================================================
# SESSION STATE
# =====================================================

if "patient_lat" not in st.session_state:
    st.session_state.patient_lat = None

if "patient_lon" not in st.session_state:
    st.session_state.patient_lon = None

if "location_source" not in st.session_state:
    st.session_state.location_source = None

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None


# =====================================================
# ROAD NETWORK CACHE
# =====================================================

@st.cache_resource(show_spinner=False)
def get_roads(patient_lat, patient_lon):
    cache_lat = round(float(patient_lat), 3)
    cache_lon = round(float(patient_lon), 3)

    return load_road_network(cache_lat, cache_lon)


# =====================================================
# HELPER FUNCTION: ALGORITHM RESULTS
# =====================================================

def build_algorithm_result(graph, route):

    if route is None:
        return None

    metrics = calculate_route_metrics(graph, route)

    return {
        "route": route,
        "road_segments": len(route) - 1,
        "distance_km": metrics["distance_km"],
        "travel_time_minutes": metrics["travel_time_minutes"]
    }


# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:

    st.markdown("## 🚑 Emergency Control")

    st.caption("Hospital Route Optimization System")

    st.divider()

    st.markdown("### 📍 Patient Location")

    location_mode = st.radio(
        "Choose location method",
        [
            "Use My Current Location",
            "Enter Address Manually"
        ],
        label_visibility="collapsed"
    )

    # GPS LOCATION
    if location_mode == "Use My Current Location":

        location_data = streamlit_geolocation()

        if location_data:

            latitude = location_data.get("latitude")
            longitude = location_data.get("longitude")

            if latitude is not None and longitude is not None:

                if (
                    latitude != st.session_state.patient_lat
                    or longitude != st.session_state.patient_lon
                ):
                    st.session_state.patient_lat = latitude
                    st.session_state.patient_lon = longitude
                    st.session_state.location_source = "GPS"
                    st.session_state.analysis_result = None

    # MANUAL ADDRESS
    else:

        address = st.text_input(
            "Enter patient address",
            placeholder="Example: Koramangala, Bengaluru"
        )

        if st.button(
            "Find Patient Location",
            use_container_width=True
        ):

            if address.strip():

                try:

                    geolocator = Nominatim(
                        user_agent="emergency_hospital_route_optimizer"
                    )

                    location = geolocator.geocode(
                        address,
                        timeout=15
                    )

                    if location:

                        st.session_state.patient_lat = location.latitude
                        st.session_state.patient_lon = location.longitude
                        st.session_state.location_source = "Manual Address"
                        st.session_state.analysis_result = None

                        st.success("Patient location found!")

                    else:

                        st.error("Address not found. Try another address.")

                except Exception as error:

                    st.error(f"Location error: {error}")

            else:

                st.warning("Please enter an address.")

    st.divider()

    st.markdown("### 🚦 Traffic Condition")

    traffic_level = st.selectbox(
        "Select traffic condition",
        ["Low", "Moderate", "Heavy"]
    )

    st.caption(
        "Traffic selection is informational. "
        "Live traffic data is not connected."
    )

    st.divider()

    if st.session_state.patient_lat is not None:

        st.markdown("### Patient Coordinates")

        st.markdown(
            '<div class="patient-location-status">'
            'Patient location available</div>',
            unsafe_allow_html=True
        )

        st.write(
            f"**Latitude:** {st.session_state.patient_lat:.6f}"
        )

        st.write(
            f"**Longitude:** {st.session_state.patient_lon:.6f}"
        )

        st.caption(
            f"Location source: {st.session_state.location_source}"
        )

    else:

        st.warning("Patient location not selected.")


# =====================================================
# MAIN DASHBOARD HEADER
# =====================================================

st.markdown("# 🚑 Emergency Hospital Route Optimizer")

st.markdown(
    "### Intelligent hospital discovery and fastest road-route analysis"
)

st.divider()

header_col1, header_col2 = st.columns([3, 1])

with header_col1:

    st.markdown("## Emergency Response Dashboard")

    st.caption(
        "Find nearby hospitals and identify the fastest "
        "estimated driving route."
    )

with header_col2:

    st.markdown("""
    <div class="metric-card">
        <span class="status">● SYSTEM READY</span>
        <br><br>
        <span class="metric-label">Route analysis platform</span>
    </div>
    """, unsafe_allow_html=True)


# =====================================================
# ANALYSIS BUTTON
# =====================================================

st.markdown("### 🚨 Start Emergency Route Analysis")

if st.button(
    "Find Nearest Hospital & Calculate Route",
    type="primary",
    use_container_width=True,
    disabled=st.session_state.patient_lat is None
):

    try:

        patient_lat = st.session_state.patient_lat
        patient_lon = st.session_state.patient_lon

        with st.spinner(
            "Loading road network and searching for nearby hospitals..."
        ):

            # Load road network
            graph = get_roads(patient_lat, patient_lon)

            # Road network information
            graph_info = get_graph_info(graph)

            # Find nearby hospitals
            hospitals = find_nearby_hospitals(
                graph,
                patient_lat,
                patient_lon
            )

            if not hospitals:

                st.session_state.analysis_result = {
                    "error": (
                        "No nearby hospitals found. "
                        "Try another patient location."
                    )
                }

            else:

                # Select hospital with lowest estimated travel time
                best_hospital = min(
                    hospitals,
                    key=lambda hospital: hospital["travel_time_minutes"]
                )

                # Convert patient and hospital coordinates
                # into nearest road intersections
                source_node = ox.distance.nearest_nodes(
                    graph,
                    X=patient_lon,
                    Y=patient_lat
                )

                destination_node = ox.distance.nearest_nodes(
                    graph,
                    X=best_hospital["longitude"],
                    Y=best_hospital["latitude"]
                )

                # -----------------------------------------
                # RUN BFS, UCS AND A*
                # -----------------------------------------

                bfs_route = bfs(
                    graph,
                    source_node,
                    destination_node
                )

                ucs_route = ucs(
                    graph,
                    source_node,
                    destination_node
                )

                astar_route = astar(
                    graph,
                    source_node,
                    destination_node
                )

                # Calculate metrics for every algorithm
                algorithm_results = {
                    "BFS": build_algorithm_result(graph, bfs_route),
                    "UCS": build_algorithm_result(graph, ucs_route),
                    "A*": build_algorithm_result(graph, astar_route)
                }

                # UCS is used for the recommended route
                route_result = algorithm_results["UCS"]

                if route_result is None:

                    raise ValueError(
                        "No reachable road route to the recommended hospital."
                    )

                # Save all results
                st.session_state.analysis_result = {
                    "graph": graph,
                    "graph_info": graph_info,
                    "hospitals": hospitals,
                    "best_hospital": best_hospital,
                    "route_result": route_result,
                    "algorithm_results": algorithm_results,
                    "patient_lat": patient_lat,
                    "patient_lon": patient_lon,
                    "traffic": traffic_level
                }

    except Exception as error:

        st.session_state.analysis_result = {
            "error": str(error)
        }


# =====================================================
# DISPLAY RESULTS
# =====================================================

result = st.session_state.analysis_result

if result:

    if "error" in result:

        st.error(result["error"])

    else:

        best = result["best_hospital"]
        hospitals = result["hospitals"]
        route_result = result["route_result"]

        st.divider()

        # ---------------------------------------------
        # EMERGENCY STATISTICS
        # ---------------------------------------------

        st.markdown("## 📊 Emergency Route Statistics")

        col1, col2, col3, col4 = st.columns(4)

        metric_items = [
            (
                col1,
                "Recommended Hospital",
                best["name"]
            ),
            (
                col2,
                "Road Distance",
                f'{route_result["distance_km"]} km'
            ),
            (
                col3,
                "Estimated Travel Time",
                f'{route_result["travel_time_minutes"]} min'
            ),
            (
                col4,
                "Nearby Hospitals",
                str(len(hospitals))
            )
        ]

        for column, label, value in metric_items:

            with column:

                safe_label = html.escape(str(label))
                safe_value = html.escape(str(value))

                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">{safe_label}</div>
                        <div class="metric-value">{safe_value}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        st.divider()

        # ---------------------------------------------
        # INTERACTIVE MAP
        # ---------------------------------------------

        st.markdown("## 🗺️ Emergency Route Map")

        st.caption(
            "Red marker: Patient | Green marker: Recommended hospital "
            "| Blue markers: Other hospitals"
        )

        patient_lat = result["patient_lat"]
        patient_lon = result["patient_lon"]

        map_object = folium.Map(
            location=[patient_lat, patient_lon],
            zoom_start=14,
            tiles="OpenStreetMap",
            control_scale=True
        )

        # Patient marker
        folium.Marker(
            location=[patient_lat, patient_lon],
            tooltip="Patient Location",
            popup="Emergency Patient",
            icon=folium.Icon(
                color="red",
                icon="user"
            )
        ).add_to(map_object)

        # Hospital markers
        for index, hospital in enumerate(hospitals):

            is_recommended = (
                hospital["name"] == best["name"]
                and hospital["latitude"] == best["latitude"]
                and hospital["longitude"] == best["longitude"]
            )

            folium.Marker(
                location=[
                    hospital["latitude"],
                    hospital["longitude"]
                ],
                tooltip=hospital["name"],
                popup=(
                    f'{hospital["name"]}<br>'
                    f'Distance: {hospital["distance_km"]} km<br>'
                    f'Time: {hospital["travel_time_minutes"]} min'
                ),
                icon=folium.Icon(
                    color="green" if is_recommended else "blue",
                    icon="plus-sign"
                )
            ).add_to(map_object)

        # Recommended UCS route
        route = route_result["route"]

        if len(route) >= 2:

            route_coordinates = [
                (
                    result["graph"].nodes[node]["y"],
                    result["graph"].nodes[node]["x"]
                )
                for node in route
            ]

            folium.PolyLine(
                route_coordinates,
                color="#ff334f",
                weight=6,
                opacity=0.9,
                tooltip="Recommended UCS Emergency Route"
            ).add_to(map_object)

        st_folium(
            map_object,
            use_container_width=True,
            height=550,
            returned_objects=[]
        )

        st.divider()

        # ---------------------------------------------
        # HOSPITAL CARDS
        # ---------------------------------------------

        st.markdown("## 🏥 Recommended Nearby Hospitals")

        for index, hospital in enumerate(hospitals):

            is_recommended = (
                hospital["name"] == best["name"]
                and hospital["latitude"] == best["latitude"]
                and hospital["longitude"] == best["longitude"]
            )

            card_class = (
                "hospital-card recommended"
                if is_recommended
                else "hospital-card"
            )

            badge_text = (
                "⭐ FASTEST ESTIMATED ROUTE"
                if is_recommended
                else f"HOSPITAL {index + 1}"
            )

            safe_name = html.escape(str(hospital["name"]))
            safe_badge = html.escape(badge_text)

            st.markdown(
                f"""
                <div class="{card_class}">
                    <h4>🏥 {safe_name}</h4>
                    <span class="status">{safe_badge}</span>
                    <br><br>
                    <p>
                        <b>Distance:</b>
                        {hospital["distance_km"]} km
                        &nbsp;&nbsp;&nbsp;
                        <b>Estimated travel time:</b>
                        {hospital["travel_time_minutes"]} minutes
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.divider()

        # ---------------------------------------------
        # ALGORITHM COMPARISON
        # ---------------------------------------------

        st.markdown("## 🧠 Search Algorithm Comparison")

        st.caption(
            "All three algorithms are evaluated using the same "
            "patient location and recommended hospital."
        )

        comparison_rows = []

        for algorithm_name, algorithm_result in result[
            "algorithm_results"
        ].items():

            if algorithm_result is None:

                comparison_rows.append({
                    "Algorithm": algorithm_name,
                    "Road Segments": "No route",
                    "Distance (km)": "-",
                    "Travel Time (min)": "-"
                })

            else:

                comparison_rows.append({
                    "Algorithm": algorithm_name,
                    "Road Segments": algorithm_result["road_segments"],
                    "Distance (km)": algorithm_result["distance_km"],
                    "Travel Time (min)": algorithm_result[
                        "travel_time_minutes"
                    ]
                })

        st.table(comparison_rows)

        st.markdown("### How the algorithms work")

        comparison_col1, comparison_col2, comparison_col3 = st.columns(3)

        with comparison_col1:

            st.markdown("#### 🔵 BFS")

            st.write(
                "Explores roads level by level and finds a route "
                "with the fewest road segments. It does not "
                "necessarily find the fastest route."
            )

        with comparison_col2:

            st.markdown("#### 🟢 UCS")

            st.write(
                "Expands the route with the lowest accumulated "
                "travel time. It finds the minimum-cost route."
            )

        with comparison_col3:

            st.markdown("#### 🟣 A*")

            st.write(
                "Uses actual travel cost and estimated remaining "
                "travel cost to find a minimum-cost route."
            )

        st.info(
            "UCS and A* should produce the same minimum estimated "
            "travel time. BFS may produce a different result because "
            "it minimizes road segments rather than travel time."
        )

        st.caption(
            "UCS is equivalent to Dijkstra's algorithm when all "
            "road travel-time costs are non-negative."
        )

        st.divider()

        # ---------------------------------------------
        # ROAD NETWORK INFORMATION
        # ---------------------------------------------

        st.markdown("## ⚙️ Road Network Information")

        info_col1, info_col2, info_col3 = st.columns(3)

        info_col1.metric(
            "Road Intersections",
            result["graph_info"]["intersections"]
        )

        info_col2.metric(
            "Road Segments",
            result["graph_info"]["road_segments"]
        )

        info_col3.metric(
            "Selected Traffic Condition",
            result["traffic"]
        )

        st.caption(
            "Road travel-time costs are fixed estimated values "
            "during each analysis. Live traffic updates are not connected."
        )


# =====================================================
# EMPTY STATE
# =====================================================

else:

    st.info(
        "📍 Select a patient location from the sidebar and click "
        "'Find Nearest Hospital & Calculate Route' to begin."
    )


# =====================================================
# FOOTER
# =====================================================

st.divider()

st.caption(
    "Emergency Hospital Route Optimizer | OpenStreetMap road data | "
    "Travel times are estimates and are not live ambulance dispatch guidance."
)
