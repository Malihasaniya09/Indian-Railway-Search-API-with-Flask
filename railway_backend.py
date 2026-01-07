from typing import TypedDict, List, Dict, Annotated
from langgraph.graph import StateGraph, END
from datetime import datetime, timedelta
import operator
import os
from groq import Groq

# Import the RailRadar API client
from live_api import IndianRailwayAPI

# Initialize Groq client
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Initialize Railway API client
railway_api = IndianRailwayAPI()

# State definition for LangGraph
class TrainSearchState(TypedDict):
    source: str
    destination: str
    source_code: str
    destination_code: str
    date: str
    user_preferences: str
    direct_trains: Annotated[List[Dict], operator.add]
    connecting_trains: Annotated[List[Dict], operator.add]
    intermediate_stations: List[str]
    llm_recommendation: str
    search_complete: bool
    alternative_stations: Dict  # NEW: Track alternative stations tried

# ==================== HELPER FUNCTIONS ====================

def get_alternative_stations(station_name: str, current_code: str) -> List[Dict]:
    """
    Get alternative station codes for a city/region
    Returns list of {"code": "XXX", "name": "Station Name", "reason": "why"}
    """
    alternatives = []
    
    # City-based alternatives
    city_alternatives = {
        "Delhi": [
            {"code": "NDLS", "name": "New Delhi", "reason": "Main station"},
            {"code": "DLI", "name": "Delhi Junction", "reason": "Old Delhi"},
            {"code": "NZM", "name": "Hazrat Nizamuddin", "reason": "Major junction"},
            {"code": "ANVT", "name": "Anand Vihar Terminal", "reason": "East Delhi hub"},
        ],
        "Mumbai": [
            {"code": "CSTM", "name": "Mumbai CST", "reason": "Main terminal"},
            {"code": "BCT", "name": "Mumbai Central", "reason": "Western hub"},
            {"code": "LTT", "name": "Lokmanya Tilak", "reason": "Long distance trains"},
            {"code": "BVI", "name": "Borivali", "reason": "Suburban hub"},
        ],
        "Bangalore": [
            {"code": "SBC", "name": "Bangalore City", "reason": "Main station"},
            {"code": "YPR", "name": "Yeshwantpur", "reason": "Major junction"},
            {"code": "KJM", "name": "Krishnarajapuram", "reason": "Cargo hub with passenger trains"},
        ],
        "Chennai": [
            {"code": "MAS", "name": "Chennai Central", "reason": "Main station"},
            {"code": "MS", "name": "Chennai Egmore", "reason": "Southern trains"},
        ],
        "Hyderabad": [
            {"code": "HYB", "name": "Hyderabad Deccan", "reason": "Main station"},
            {"code": "SC", "name": "Secunderabad", "reason": "Major junction"},
        ],
        "Kolkata": [
            {"code": "HWH", "name": "Howrah", "reason": "Main station"},
            {"code": "SDAH", "name": "Sealdah", "reason": "Eastern trains"},
        ],
    }
    
    # Check if station name contains any city name
    for city, stations in city_alternatives.items():
        if city.lower() in station_name.lower():
            # Add all city alternatives except current
            alternatives.extend([s for s in stations if s["code"] != current_code])
            return alternatives[:3]  # Return top 3
    
    # Regional alternatives based on current station
    regional_alternatives = {
        "ANVT": [
            {"code": "NDLS", "name": "New Delhi", "reason": "Main Delhi station, 12km away"},
            {"code": "NZM", "name": "Hazrat Nizamuddin", "reason": "Major junction, 10km away"},
        ],
        "BNC": [
            {"code": "SBC", "name": "Bangalore City", "reason": "Main station, 3km away"},
            {"code": "YPR", "name": "Yeshwantpur", "reason": "Major junction, 8km away"},
        ],
        "BAY": [
            {"code": "GTL", "name": "Guntakal", "reason": "Major junction, 70km away"},
            {"code": "UBL", "name": "Hubli", "reason": "Karnataka hub, 160km away"},
        ],
        "AMI": [
            {"code": "NGP", "name": "Nagpur", "reason": "Central India hub, 155km away"},
            {"code": "AK", "name": "Akola", "reason": "Maharashtra junction, 90km away"},
        ],
        "ALJN": [
            {"code": "AGC", "name": "Agra Cantt", "reason": "Major station, 85km away"},
            {"code": "CNB", "name": "Kanpur Central", "reason": "UP hub, 190km away"},
        ],
    }
    
    if current_code in regional_alternatives:
        alternatives = regional_alternatives[current_code]
    
    return alternatives[:3]  # Return top 3

# ==================== NODE FUNCTIONS ====================

def resolve_stations(state: TrainSearchState) -> TrainSearchState:
    """Resolve city/station names to station codes with alternatives"""
    source = state["source"]
    destination = state["destination"]
    
    print(f"\n🔍 Resolving stations: {source} → {destination}")
    
    # Try RailRadar API first for comprehensive station search
    source_code = ""
    dest_code = ""
    
    # Search for source station
    try:
        source_stations = railway_api.search_station_by_name(source)
        if source_stations:
            source_code = source_stations[0]["code"]
            print(f"✅ Source resolved: {source} → {source_code} ({source_stations[0]['name']})")
        else:
            # Try exact code match
            if len(source.strip()) <= 5 and source.strip().isupper():
                source_code = source.strip()
                print(f"✅ Using source as code: {source_code}")
            else:
                print(f"⚠️ No stations found for: {source}")
                from station_codes import get_station_code
                fallback_code = get_station_code(source)
                if fallback_code != source:
                    source_code = fallback_code
                    print(f"✅ Source resolved via fallback: {source} → {source_code}")
    except Exception as e:
        print(f"⚠️ Error resolving source: {e}")
        from station_codes import get_station_code
        source_code = get_station_code(source)
    
    # Search for destination station
    try:
        dest_stations = railway_api.search_station_by_name(destination)
        if dest_stations:
            dest_code = dest_stations[0]["code"]
            print(f"✅ Destination resolved: {destination} → {dest_code} ({dest_stations[0]['name']})")
        else:
            if len(destination.strip()) <= 5 and destination.strip().isupper():
                dest_code = destination.strip()
                print(f"✅ Using destination as code: {dest_code}")
            else:
                print(f"⚠️ No stations found for: {destination}")
                from station_codes import get_station_code
                fallback_code = get_station_code(destination)
                if fallback_code != destination:
                    dest_code = fallback_code
                    print(f"✅ Destination resolved via fallback: {destination} → {dest_code}")
    except Exception as e:
        print(f"⚠️ Error resolving destination: {e}")
        from station_codes import get_station_code
        dest_code = get_station_code(destination)
    
    if not source_code or not dest_code:
        print(f"❌ Failed to resolve stations: source={source_code}, dest={dest_code}")
    
    return {
        "source_code": source_code,
        "destination_code": dest_code,
        "alternative_stations": {
            "source_alternatives": get_alternative_stations(source, source_code),
            "dest_alternatives": get_alternative_stations(destination, dest_code)
        }
    }

def search_direct_trains(state: TrainSearchState) -> TrainSearchState:
    """Search for direct trains, trying alternative stations if needed"""
    source_code = state.get("source_code", "")
    dest_code = state.get("destination_code", "")
    date = state["date"]
    
    if not source_code or not dest_code:
        print("❌ Cannot search: Missing station codes")
        return {"direct_trains": []}
    
    print(f"\n🚆 Searching direct trains: {source_code} → {dest_code}")
    
    try:
        trains = railway_api.search_trains(source_code, dest_code, date)
        
        # If no trains found, try alternative stations
        if not trains:
            print(f"⚠️ No direct trains found on {source_code} → {dest_code}")
            alternatives = state.get("alternative_stations", {})
            
            # Try alternative source stations
            for alt_src in alternatives.get("source_alternatives", [])[:2]:
                print(f"🔄 Trying alternative source: {alt_src['code']} ({alt_src['reason']})")
                alt_trains = railway_api.search_trains(alt_src["code"], dest_code, date)
                if alt_trains:
                    print(f"✅ Found {len(alt_trains)} trains from {alt_src['name']}")
                    # Add note to trains
                    for train in alt_trains[:10]:
                        train["alternative_note"] = f"Departs from {alt_src['name']} ({alt_src['reason']})"
                    trains = alt_trains
                    break
            
            # Try alternative destination stations if still no trains
            if not trains:
                for alt_dest in alternatives.get("dest_alternatives", [])[:2]:
                    print(f"🔄 Trying alternative destination: {alt_dest['code']} ({alt_dest['reason']})")
                    alt_trains = railway_api.search_trains(source_code, alt_dest["code"], date)
                    if alt_trains:
                        print(f"✅ Found {len(alt_trains)} trains to {alt_dest['name']}")
                        for train in alt_trains[:10]:
                            train["alternative_note"] = f"Arrives at {alt_dest['name']} ({alt_dest['reason']})"
                        trains = alt_trains
                        break
        
        # Convert to our format
        direct_trains = []
        for train in trains[:10]:
            availability = railway_api.get_seat_availability(
                train["train_no"],
                train.get("from_code", source_code),
                train.get("to_code", dest_code),
                date,
                "3A"
            )
            
            train_info = {
                "train_no": train["train_no"],
                "name": train["name"],
                "from": train["from"],
                "to": train["to"],
                "departure": train["departure"],
                "arrival": train["arrival"],
                "duration": train["duration"],
                "available_seats": availability.get("available", 0),
                "class": availability.get("class", "3A"),
                "price": availability.get("fare", 0),
                "train_type": train.get("train_type", ""),
                "run_days": train.get("run_days", [])
            }
            
            # Add alternative note if present
            if "alternative_note" in train:
                train_info["note"] = train["alternative_note"]
            
            direct_trains.append(train_info)
        
        print(f"✅ Found {len(direct_trains)} direct trains")
        return {"direct_trains": direct_trains}
        
    except Exception as e:
        print(f"❌ Error fetching direct trains: {e}")
        return {"direct_trains": []}

def find_intermediate_stations(state: TrainSearchState) -> TrainSearchState:
    """
    Find intermediate stations - expand based on geography
    """
    source_code = state.get("source_code", "")
    dest_code = state.get("destination_code", "")
    
    if not source_code or not dest_code:
        return {"intermediate_stations": []}
    
    print(f"\n🔄 Finding intermediate stations...")
    
    # Comprehensive major junctions (expanded from 16 to 25)
    major_junctions = [
        "NDLS",  # New Delhi
        "BCT",   # Mumbai Central
        "HWH",   # Howrah (Kolkata)
        "MAS",   # Chennai Central
        "SC",    # Secunderabad
        "SBC",   # Bangalore City
        "PUNE",  # Pune Junction
        "JP",    # Jaipur
        "NGP",   # Nagpur (Central India hub)
        "BPL",   # Bhopal
        "LKO",   # Lucknow
        "CNB",   # Kanpur
        "PNBE",  # Patna
        "ADI",   # Ahmedabad
        "BZA",   # Vijayawada (Andhra hub)
        "ERS",   # Kochi
        "GTL",   # Guntakal (Karnataka/Andhra junction)
        "UBL",   # Hubli (Karnataka)
        "VSKP",  # Visakhapatnam
        "ROU",   # Rourkela (Odisha)
        "BSP",   # Bilaspur (Chhattisgarh)
        "R",     # Raipur
        "JAT",   # Jammu Tawi
        "CDG",   # Chandigarh
        "ASR",   # Amritsar
    ]
    
    # Remove source and destination from intermediate options
    intermediate = [
        station for station in major_junctions 
        if station not in [source_code, dest_code]
    ]
    
    print(f"✅ Using {len(intermediate[:8])} major junction stations")
    return {"intermediate_stations": intermediate[:8]}  # Increased from 5 to 8

def search_connecting_trains(state: TrainSearchState) -> TrainSearchState:
    """Search for connecting trains - optimized to find top 10 fastest"""
    source_code = state.get("source_code", "")
    dest_code = state.get("destination_code", "")
    intermediate_stations = state.get("intermediate_stations", [])
    date = state["date"]
    
    if not source_code or not dest_code:
        return {"connecting_trains": []}
    
    print(f"\n🔄 Searching connecting trains via {len(intermediate_stations)} stations...")
    print(f"⚡ Optimized mode: Will return top 10 fastest connections only")
    
    all_connections = []
    
    for via_station_code in intermediate_stations:
        try:
            print(f"  Checking via {via_station_code}...")
            
            first_leg_trains = railway_api.search_trains(source_code, via_station_code, date)
            
            if not first_leg_trains:
                print(f"    No trains from {source_code} to {via_station_code}")
                continue
            
            second_leg_trains = railway_api.search_trains(via_station_code, dest_code, date)
            
            if not second_leg_trains:
                print(f"    No trains from {via_station_code} to {dest_code}")
                continue
            
            print(f"    Found {len(first_leg_trains)} first leg, {len(second_leg_trains)} second leg trains")
            
            # Match trains with valid layover times
            for first in first_leg_trains[:3]:
                if not first["arrival"]:
                    continue
                    
                try:
                    first_arrival_time = datetime.strptime(first["arrival"], "%H:%M")
                except:
                    continue
                
                for second in second_leg_trains[:3]:
                    if not second["departure"]:
                        continue
                        
                    try:
                        second_departure_time = datetime.strptime(second["departure"], "%H:%M")
                    except:
                        continue
                    
                    # Calculate layover
                    if second_departure_time > first_arrival_time:
                        layover_hours = (second_departure_time - first_arrival_time).seconds / 3600
                    else:
                        layover_hours = (24 * 3600 - first_arrival_time.hour * 3600 + 
                                       second_departure_time.hour * 3600) / 3600
                    
                    # Valid layover: 1-12 hours
                    if 1 <= layover_hours <= 12:
                        first_availability = railway_api.get_seat_availability(
                            first["train_no"], source_code, via_station_code, date
                        )
                        
                        second_availability = railway_api.get_seat_availability(
                            second["train_no"], via_station_code, dest_code, date
                        )
                        
                        via_stations = railway_api.search_station_by_name(via_station_code)
                        via_name = via_stations[0]["name"] if via_stations else via_station_code
                        
                        try:
                            first_duration = float(first["duration"]) if first["duration"] else 0
                            second_duration = float(second["duration"]) if second["duration"] else 0
                            total_duration = first_duration + second_duration + layover_hours
                        except:
                            total_duration = 24
                        
                        total_price = first_availability.get("fare", 0) + second_availability.get("fare", 0)
                        
                        connection = {
                            "first_train": {
                                "train_no": first["train_no"],
                                "name": first["name"],
                                "from": first["from"],
                                "to": via_name,
                                "departure": first["departure"],
                                "arrival": first["arrival"],
                                "duration": first["duration"],
                                "available_seats": first_availability.get("available", 50),
                                "class": first_availability.get("class", "3A"),
                                "price": first_availability.get("fare", 500)
                            },
                            "second_train": {
                                "train_no": second["train_no"],
                                "name": second["name"],
                                "from": via_name,
                                "to": second["to"],
                                "departure": second["departure"],
                                "arrival": second["arrival"],
                                "duration": second["duration"],
                                "available_seats": second_availability.get("available", 50),
                                "class": second_availability.get("class", "3A"),
                                "price": second_availability.get("fare", 500)
                            },
                            "via": via_name,
                            "total_duration": round(total_duration, 2),
                            "layover_hours": round(layover_hours, 2),
                            "total_price": total_price
                        }
                        
                        all_connections.append(connection)
                        print(f"    ✅ Found connection: {first['train_no']} + {second['train_no']} ({total_duration:.1f}h)")
            
        except Exception as e:
            print(f"    ⚠️ Error checking {via_station_code}: {e}")
            continue
    
    # Sort by total duration and take top 10
    all_connections.sort(key=lambda x: x["total_duration"])
    top_10_connections = all_connections[:10]
    
    print(f"\n✅ Found {len(all_connections)} total connections")
    print(f"🎯 Returning top 10 fastest connections ({len(top_10_connections)} found)")
    
    if top_10_connections:
        print(f"⚡ Fastest: {top_10_connections[0]['total_duration']:.1f}h via {top_10_connections[0]['via']}")
        if len(top_10_connections) > 1:
            print(f"⚡ Slowest in top 10: {top_10_connections[-1]['total_duration']:.1f}h via {top_10_connections[-1]['via']}")
    
    return {"connecting_trains": top_10_connections}

def get_llm_recommendation(state: TrainSearchState) -> TrainSearchState:
    """Use Groq LLM to provide intelligent recommendations"""
    direct_trains = state.get("direct_trains", [])
    connecting_trains = state.get("connecting_trains", [])
    user_prefs = state.get("user_preferences", "")
    alternatives = state.get("alternative_stations", {})
    
    # Check if we used alternative stations
    used_alternatives = any("note" in train for train in direct_trains)
    
    # Prepare context for LLM
    context = f"""
    User is searching for trains from {state['source']} to {state['destination']} on {state['date']}.
    
    User preferences: {user_prefs if user_prefs else "No specific preferences mentioned"}
    
    Available Direct Trains ({len(direct_trains)}):
    """
    
    for i, train in enumerate(direct_trains[:5], 1):
        note = f" [{train.get('note', '')}]" if train.get('note') else ""
        context += f"\n{i}. {train['name']} ({train['train_no']}) - Departure: {train['departure']}, Arrival: {train['arrival']}, Duration: {train['duration']}hrs{note}"
    
    context += f"\n\nTop 10 Fastest Connecting Trains ({len(connecting_trains)}):"
    
    for i, conn in enumerate(connecting_trains[:5], 1):
        context += f"\n{i}. Via {conn['via']} - Total: {conn['total_duration']}hrs, Layover: {conn['layover_hours']}hrs"
    
    if len(direct_trains) == 0 and len(connecting_trains) == 0:
        # Suggest alternatives
        alt_suggestions = []
        for alt in alternatives.get("source_alternatives", [])[:2]:
            alt_suggestions.append(f"Try departing from {alt['name']} ({alt['reason']})")
        for alt in alternatives.get("dest_alternatives", [])[:2]:
            alt_suggestions.append(f"Try arriving at {alt['name']} ({alt['reason']})")
        
        if alt_suggestions:
            context += f"\n\nNo direct routes found. Suggestions:\n" + "\n".join(alt_suggestions)
    
    context += "\n\nProvide a brief, helpful recommendation (3-4 sentences) with practical travel advice."
    
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful Indian Railway travel assistant. Provide concise, practical recommendations."
                },
                {
                    "role": "user",
                    "content": context
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=250
        )
        
        recommendation = chat_completion.choices[0].message.content
        
    except Exception as e:
        if direct_trains and connecting_trains:
            fastest_direct = min(direct_trains, key=lambda x: float(x['duration']))
            fastest_connecting = connecting_trains[0]
            recommendation = f"Found {len(direct_trains)} direct and {len(connecting_trains)} connecting options. Fastest direct: {fastest_direct['name']} ({fastest_direct['duration']}hrs). Fastest connecting: via {fastest_connecting['via']} ({fastest_connecting['total_duration']:.1f}hrs total)."
        elif direct_trains:
            fastest = min(direct_trains, key=lambda x: float(x['duration']))
            note = f" Note: {direct_trains[0].get('note', '')}" if direct_trains[0].get('note') else ""
            recommendation = f"Found {len(direct_trains)} direct trains. Fastest: {fastest['name']} taking {fastest['duration']}hrs.{note}"
        elif connecting_trains:
            fastest = connecting_trains[0]
            recommendation = f"No direct trains available. Best connecting option: via {fastest['via']} taking {fastest['total_duration']:.1f}hrs total with {fastest['layover_hours']:.1f}hrs layover."
        else:
            # Provide alternative suggestions
            alt_text = []
            for alt in alternatives.get("source_alternatives", [])[:2]:
                alt_text.append(f"{alt['name']}")
            for alt in alternatives.get("dest_alternatives", [])[:2]:
                alt_text.append(f"{alt['name']}")
            
            if alt_text:
                recommendation = f"No trains found on this route. Consider nearby stations: {', '.join(alt_text)}. These stations typically have better connectivity."
            else:
                recommendation = "No trains found. This route may not have direct connectivity. Try searching major nearby cities or check if the stations are correct."
        
        print(f"⚠️ LLM Error: {str(e)}")
    
    return {"llm_recommendation": recommendation}

def mark_complete(state: TrainSearchState) -> TrainSearchState:
    """Mark the search as complete"""
    return {"search_complete": True}

def should_search_connecting(state: TrainSearchState) -> str:
    """Always search for connecting trains"""
    return "search_connecting"

# ==================== BUILD LANGGRAPH WORKFLOW ====================

def create_train_search_graph():
    workflow = StateGraph(TrainSearchState)
    
    workflow.add_node("resolve_stations", resolve_stations)
    workflow.add_node("search_direct", search_direct_trains)
    workflow.add_node("find_intermediate", find_intermediate_stations)
    workflow.add_node("search_connecting", search_connecting_trains)
    workflow.add_node("get_recommendation", get_llm_recommendation)
    workflow.add_node("complete", mark_complete)
    
    workflow.set_entry_point("resolve_stations")
    workflow.add_edge("resolve_stations", "search_direct")
    workflow.add_edge("search_direct", "find_intermediate")
    workflow.add_conditional_edges(
        "find_intermediate",
        should_search_connecting,
        {"search_connecting": "search_connecting"}
    )
    workflow.add_edge("search_connecting", "get_recommendation")
    workflow.add_edge("get_recommendation", "complete")
    workflow.add_edge("complete", END)
    
    return workflow.compile()

# ==================== MAIN SEARCH FUNCTION ====================

def search_trains(source: str, destination: str, date: str, user_preferences: str = "") -> Dict:
    """
    Main function to search for trains with smart fallbacks
    """
    graph = create_train_search_graph()
    
    initial_state = {
        "source": source,
        "destination": destination,
        "source_code": "",
        "destination_code": "",
        "date": date,
        "user_preferences": user_preferences,
        "direct_trains": [],
        "connecting_trains": [],
        "intermediate_stations": [],
        "llm_recommendation": "",
        "search_complete": False,
        "alternative_stations": {}
    }
    
    result = graph.invoke(initial_state)
    
    return {
        "source": source,
        "destination": destination,
        "date": date,
        "direct_trains": result["direct_trains"],
        "connecting_trains": result["connecting_trains"],
        "llm_recommendation": result["llm_recommendation"],
        "total_options": len(result["direct_trains"]) + len(result["connecting_trains"]),
        "alternative_stations": result.get("alternative_stations", {})
    }

# ==================== TEST ====================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚂 Testing Smart Station Fallback System")
    print("="*60)
    
    # Test problematic route
    print("\n🔍 Test: Anand Vihar Terminal → Bellary (typically 0 trains)")
    result = search_trains("Anand Vihar Terminal", "Bellary", "2025-11-15")
    print(f"\n✅ Direct trains: {len(result['direct_trains'])}")
    print(f"✅ Connecting trains: {len(result['connecting_trains'])}")
    print(f"\n💡 AI Recommendation:\n{result['llm_recommendation']}")
    
    if result.get('alternative_stations'):
        print(f"\n🔄 Alternative stations suggested:")
        for alt in result['alternative_stations'].get('source_alternatives', []):
            print(f"  Source: {alt['name']} - {alt['reason']}")
        for alt in result['alternative_stations'].get('dest_alternatives', []):
            print(f"  Dest: {alt['name']} - {alt['reason']}")
    
    print("\n" + "="*60)