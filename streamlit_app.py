import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd

# Configuration
API_BASE_URL = "http://localhost:8000"

# Page config
st.set_page_config(
    page_title="Indian Railway Search AI",
    page_icon="🚂",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - same styling
st.markdown("""
    <style>
    .main { padding: 2rem; }
    .stButton>button {
        width: 100%;
        background-color: #FF6B35;
        color: white;
        font-weight: bold;
        padding: 0.5rem;
        border-radius: 5px;
        border: none;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #E55A2B;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .train-card {
        padding: 1.5rem;
        border-radius: 10px;
        background-color: #f0f2f6;
        margin: 1rem 0;
        border-left: 5px solid #FF6B35;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .seat-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: bold;
        margin: 0.25rem;
    }
    .seat-available { background-color: #d4edda; color: #155724; }
    .seat-limited { background-color: #fff3cd; color: #856404; }
    .seat-waitlist { background-color: #f8d7da; color: #721c24; }
    .ai-recommendation {
        padding: 1.5rem;
        border-radius: 10px;
        background-color: #e8f5e9;
        margin: 1.5rem 0;
        border-left: 5px solid #4CAF50;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.875rem;
        font-weight: 600;
        margin: 0.25rem;
    }
    .status-success { background-color: #d4edda; color: #155724; }
    .status-warning { background-color: #fff3cd; color: #856404; }
    .search-progress {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border-left: 4px solid #2196F3;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'search_performed' not in st.session_state:
    st.session_state.search_performed = False

# Helper functions
@st.cache_data(ttl=300)
def get_all_stations_with_codes():
    """Get ALL stations with their codes from API"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/station-codes", timeout=5)
        if response.status_code == 200:
            data = response.json()
            stations = sorted([s["name"] for s in data["station_codes"]])
            return stations
    except Exception as e:
        print(f"Error fetching stations: {e}")
    
    return sorted([
        "New Delhi", "Delhi Junction", "Mumbai Central", "Bangalore City",
        "Chennai Central", "Howrah", "Hyderabad", "Pune Junction"
    ])

@st.cache_data(ttl=60)
def check_api_health():
    """Check API health status"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        return None

# Header
st.markdown("""
    <div style="text-align: center; padding: 1rem; background: linear-gradient(90deg, #FF6B35 0%, #F7931E 100%); border-radius: 10px; margin-bottom: 2rem;">
        <h1 style="color: white; margin: 0;">🚂 Indian Railway Search AI</h1>
        <p style="color: white; margin: 0.5rem 0 0 0;">Flask API • Real-time Seat Availability • AI Recommendations</p>
    </div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("📋 About")
    st.info("""
    **Features:**
    - ✅ Search from ALL railway stations
    - 🎯 Direct trains search
    - 🔄 Connecting trains via major junctions
    - 💺 **REAL-TIME seat availability**
    - 💰 Dynamic fare calculation
    - 🤖 AI-powered recommendations
    
    **Powered by:**
    - 🆓 RailRadar.in (FREE API)
    - 🤖 Groq AI (Llama 3.3)
    - ⚡ Flask backend (NEW!)
    - 🎨 Streamlit UI
    """)
    
    st.markdown("---")
    
    # Check API status
    api_health = check_api_health()
    
    if api_health:
        st.markdown("### 🔧 System Status")
        
        if api_health.get("status") == "healthy":
            st.markdown('<span class="status-badge status-success">✅ API Online (Flask)</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-badge status-warning">⚠️ API Issues</span>', unsafe_allow_html=True)
        
        if api_health.get("groq_ai_configured"):
            st.markdown('<span class="status-badge status-success">✅ Groq AI Active</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-badge status-warning">⚠️ AI Disabled</span>', unsafe_allow_html=True)
        
        if api_health.get("railradar_available"):
            st.markdown('<span class="status-badge status-success">✅ RailRadar (FREE)</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-badge status-info">ℹ️ Local Data</span>', unsafe_allow_html=True)
        
        st.caption(f"Database: {api_health.get('database_size', 0)} stations")
        st.caption(f"Framework: {api_health.get('framework', 'Flask')}")
    else:
        st.error("❌ Cannot connect to API server")
        st.info("Make sure the Flask API server is running:\n```bash\npython flask_api.py\n```")

# Main content
st.markdown("### 🔎 Search Trains")

col1, col2 = st.columns(2)
with col1:
    st.info("🌟 **NEW**: Real-time seat availability for all trains!")
with col2:
    st.info("⚡ **Flask API**: Simpler, faster, more reliable!")

# Get all stations
all_stations = get_all_stations_with_codes()

# Search form
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    source = st.selectbox(
        "From Station",
        options=all_stations,
        index=all_stations.index("New Delhi") if "New Delhi" in all_stations else 0,
        key="source_station"
    )

with col2:
    destination = st.selectbox(
        "To Station",
        options=all_stations,
        index=all_stations.index("Mumbai Central") if "Mumbai Central" in all_stations else (1 if len(all_stations) > 1 else 0),
        key="dest_station"
    )

with col3:
    travel_date = st.date_input(
        "Travel Date",
        min_value=datetime.now().date(),
        value=datetime.now().date() + timedelta(days=1),
    )

user_preferences = st.text_input(
    "🎯 Your Preferences (Optional)",
    placeholder="E.g., prefer fastest trains, budget-friendly, morning departure",
)

# Search button
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    search_button = st.button("🔍 Search with Real-time Availability", type="primary", use_container_width=True)

# Perform search
if search_button:
    if source == destination:
        st.error("❌ Source and destination cannot be the same!")
    else:
        progress_placeholder = st.empty()
        progress_placeholder.markdown("""
        <div class="search-progress">
            <h4>🔄 Searching trains with REAL-TIME seat availability...</h4>
            <p>⚡ This may take 30-60 seconds:</p>
            <ul>
                <li>✅ Finding direct trains</li>
                <li>✅ Checking connecting routes</li>
                <li>✅ Getting LIVE seat availability</li>
                <li>✅ Calculating dynamic fares</li>
                <li>✅ AI analysis</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/search-trains",
                json={
                    "source": source,
                    "destination": destination,
                    "date": travel_date.strftime("%Y-%m-%d"),
                    "user_preferences": user_preferences
                },
                timeout=120
            )
            
            progress_placeholder.empty()
            
            if response.status_code == 200:
                data = response.json()
                st.session_state.search_performed = True
                
                # Summary
                st.success(f"🎉 Found {data['total_options']} travel options!")
                
                # AI Recommendation
                if data.get("llm_recommendation"):
                    st.markdown("## 🤖 AI Recommendation")
                    st.markdown(f"""
                    <div class="ai-recommendation">
                        <p style="font-size: 1.1rem; line-height: 1.6;">{data['llm_recommendation']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Tabs
                tab1, tab2 = st.tabs([
                    f"🎯 Direct Trains ({len(data['direct_trains'])})",
                    f"🔄 Connecting Trains ({len(data['connecting_trains'])})"
                ])
                
                # Direct Trains
                with tab1:
                    if data["direct_trains"]:
                        for idx, train in enumerate(data["direct_trains"], 1):
                            seats = train['available_seats']
                            
                            # Dynamic seat badge styling
                            if seats == 0 or "WAITLIST" in str(seats):
                                seat_class = "seat-waitlist"
                                seat_text = "WAITLIST"
                            elif seats < 20:
                                seat_class = "seat-limited"
                                seat_text = f"{seats} seats left"
                            else:
                                seat_class = "seat-available"
                                seat_text = f"{seats} available"
                            
                            col1, col2 = st.columns([4, 1])
                            
                            with col1:
                                st.markdown(f"""
                                <div class="train-card">
                                    <h3>🚂 {idx}. {train['train_no']} - {train['name']}</h3>
                                    <div style="margin-top: 1rem;">
                                        <p><b>🚉 From:</b> {train['from']} at {train['departure']}</p>
                                        <p><b>🚉 To:</b> {train['to']} at {train['arrival']}</p>
                                        <p><b>⏱️ Duration:</b> {train['duration']} hours</p>
                                        <p><b>🎫 Class:</b> {train.get('class', '3A')} | <b>💰 Fare:</b> ₹{train.get('price', 'N/A')}</p>
                                        <span class="seat-badge {seat_class}">💺 {seat_text}</span>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            with col2:
                                st.markdown("<br><br>", unsafe_allow_html=True)
                                if st.button("📱 Book", key=f"book_direct_{idx}"):
                                    st.info(f"🎫 Booking {train['name']}...")
                    else:
                        st.warning("⚠️ No direct trains available")
                
                # Connecting Trains
                with tab2:
                    if data["connecting_trains"]:
                        for idx, option in enumerate(data["connecting_trains"], 1):
                            first = option["first_train"]
                            second = option["second_train"]
                            
                            with st.expander(
                                f"🔄 Option {idx}: Via {option['via']} | ⏱️ {round(option['total_duration'], 1)}h | 💰 ₹{option.get('total_price', 'N/A')}",
                                expanded=(idx <= 2)
                            ):
                                # First train
                                st.markdown("#### 🚂 First Train")
                                col1, col2, col3 = st.columns(3)
                                
                                with col1:
                                    st.markdown(f"**Train:** {first['train_no']}")
                                    st.markdown(f"**Name:** {first['name']}")
                                
                                with col2:
                                    st.markdown(f"**Departure:** {first['departure']}")
                                    st.markdown(f"**Arrival:** {first['arrival']}")
                                
                                with col3:
                                    seats1 = first['available_seats']
                                    st.markdown(f"**💺 Seats:** {seats1}")
                                    st.markdown(f"**💰 Fare:** ₹{first.get('price', 'N/A')}")
                                
                                st.info(f"⏱️ Layover at {option['via']}: {option['layover_hours']} hours")
                                
                                # Second train
                                st.markdown("#### 🚂 Second Train")
                                col1, col2, col3 = st.columns(3)
                                
                                with col1:
                                    st.markdown(f"**Train:** {second['train_no']}")
                                    st.markdown(f"**Name:** {second['name']}")
                                
                                with col2:
                                    st.markdown(f"**Departure:** {second['departure']}")
                                    st.markdown(f"**Arrival:** {second['arrival']}")
                                
                                with col3:
                                    seats2 = second['available_seats']
                                    st.markdown(f"**💺 Seats:** {seats2}")
                                    st.markdown(f"**💰 Fare:** ₹{second.get('price', 'N/A')}")
                                
                                st.success(f"📊 Total: {round(option['total_duration'], 1)}h | ₹{option.get('total_price', 'N/A')}")
                    else:
                        st.info("ℹ️ No connecting options found")
                        
            else:
                st.error(f"❌ Server error: {response.status_code}")
                
        except requests.exceptions.Timeout:
            progress_placeholder.empty()
            st.error("⏱️ Request timed out. Please try again.")
        except Exception as e:
            progress_placeholder.empty()
            st.error(f"❌ Error: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 2rem; background: #f8f9fa; border-radius: 10px;">
    <p style="font-size: 1.1rem; margin: 0;"><b>Made with ❤️ using</b></p>
    <p style="margin: 0.5rem 0;">Flask • Streamlit • LangGraph • Groq AI • RailRadar</p>
    <p style="color: #666; margin-top: 1rem;">
        ⚠️ Demo app • Real-time seat estimation • Not connected to IRCTC
    </p>
</div>
""", unsafe_allow_html=True)