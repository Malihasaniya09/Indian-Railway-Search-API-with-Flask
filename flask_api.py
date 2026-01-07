from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the backend logic
from railway_backend import search_trains

# Import RailRadar API client
try:
    from live_api import IndianRailwayAPI
    railway_api = IndianRailwayAPI()
    RAILRADAR_AVAILABLE = True
except ImportError:
    print("⚠️  live_api.py not found - using fallback mode")
    railway_api = None
    RAILRADAR_AVAILABLE = False

# Import station codes
from station_codes import get_all_stations, get_station_code, STATION_CODES

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

app.config['JSON_SORT_KEYS'] = False

# ==================== ROUTES ====================

@app.route('/')
def root():
    """Root endpoint with API information"""
    groq_status = "configured ✅" if os.getenv("GROQ_API_KEY") else "not configured ⚠️"
    railradar_status = "available ✅" if RAILRADAR_AVAILABLE else "not available ⚠️"
    
    return jsonify({
        "message": "Indian Railway Search API with RailRadar & Groq AI (Flask)",
        "version": "3.0.0-flask",
        "status": "operational",
        "groq_ai_status": groq_status,
        "railradar_status": railradar_status,
        "data_source": "RailRadar.in (FREE API)" if RAILRADAR_AVAILABLE else "Local Database",
        "station_coverage": "7,000+ stations" if RAILRADAR_AVAILABLE else "150+ major stations",
        "endpoints": {
            "search_trains": "/api/search-trains",
            "stations": "/api/stations",
            "station_codes": "/api/station-codes",
            "search_station": "/api/search-station/<query>",
            "seat_availability": "/api/seat-availability",
            "health": "/api/health",
            "config": "/api/config"
        },
        "documentation": "Flask API - Check routes above"
    })

@app.route('/api/search-trains', methods=['POST'])
def search_trains_endpoint():
    """
    Search for trains between source and destination using RailRadar API
    Returns both direct and connecting trains with AI recommendations
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'source' not in data or 'destination' not in data or 'date' not in data:
            return jsonify({
                "error": "Missing required fields: source, destination, date"
            }), 400
        
        source = data['source']
        destination = data['destination']
        date = data['date']
        user_preferences = data.get('user_preferences', '')
        
        # Validate date format
        try:
            search_date = datetime.strptime(date, "%Y-%m-%d")
            if search_date.date() < datetime.now().date():
                return jsonify({
                    "error": "Travel date cannot be in the past"
                }), 400
        except ValueError:
            return jsonify({
                "error": "Invalid date format. Use YYYY-MM-DD"
            }), 400
        
        # Validate source and destination
        if not source.strip() or not destination.strip():
            return jsonify({
                "error": "Source and destination cannot be empty"
            }), 400
        
        if source.lower() == destination.lower():
            return jsonify({
                "error": "Source and destination cannot be the same"
            }), 400
        
        # Search for trains using LangGraph backend with RailRadar & Groq AI
        result = search_trains(
            source=source,
            destination=destination,
            date=date,
            user_preferences=user_preferences
        )
        
        if result["total_options"] == 0:
            return jsonify({
                "source": source,
                "destination": destination,
                "date": date,
                "direct_trains": [],
                "connecting_trains": [],
                "llm_recommendation": "No trains found for this route. Please verify station names or try nearby stations.",
                "total_options": 0
            })
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "error": f"Error searching trains: {str(e)}"
        }), 500

@app.route('/api/seat-availability', methods=['POST'])
def get_seat_availability():
    """
    Get REAL-TIME seat availability for a specific train
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['train_no', 'from_code', 'to_code', 'date']
        if not all(field in data for field in required_fields):
            return jsonify({
                "error": f"Missing required fields: {', '.join(required_fields)}"
            }), 400
        
        train_no = data['train_no']
        from_code = data['from_code']
        to_code = data['to_code']
        date = data['date']
        class_type = data.get('class', '3A')
        quota = data.get('quota', 'GN')
        
        if not RAILRADAR_AVAILABLE or not railway_api:
            return jsonify({
                "error": "RailRadar API not available for real-time data"
            }), 503
        
        # Get real-time availability
        availability = railway_api.get_seat_availability(
            train_no=train_no,
            from_station_code=from_code,
            to_station_code=to_code,
            date=date,
            class_type=class_type,
            quota=quota
        )
        
        return jsonify({
            "train_no": train_no,
            "from": from_code,
            "to": to_code,
            "date": date,
            "availability": availability,
            "source": "RailRadar API"
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Error fetching seat availability: {str(e)}"
        }), 500

@app.route('/api/stations')
def get_stations():
    """Get list of all available stations - prioritizes RailRadar API"""
    try:
        # Try to get from RailRadar API first (7000+ stations)
        if RAILRADAR_AVAILABLE and railway_api:
            try:
                railradar_stations = railway_api.get_all_stations()
                if railradar_stations and len(railradar_stations) > 100:
                    # Extract unique station names
                    station_names = sorted(list(set([s["name"] for s in railradar_stations if s.get("name")])))
                    return jsonify({
                        "stations": station_names,
                        "count": len(station_names),
                        "source": "RailRadar API (FREE)",
                        "coverage": "All Indian Railway stations",
                        "message": f"Loaded {len(station_names)} stations from RailRadar.in"
                    })
            except Exception as e:
                print(f"⚠️ RailRadar API failed, using fallback: {e}")
        
        # Fallback to local station codes (150+ major stations)
        stations = get_all_stations()
        return jsonify({
            "stations": stations,
            "count": len(stations),
            "source": "Local Database",
            "coverage": "Major stations only",
            "message": f"Using {len(stations)} major stations (RailRadar unavailable)"
        })
    except Exception as e:
        return jsonify({
            "error": f"Error fetching stations: {str(e)}"
        }), 500

@app.route('/api/search-station/<query>')
def search_station(query):
    """
    Search for stations by name using RailRadar API
    This allows finding ANY station dynamically
    """
    if not query or len(query) < 2:
        return jsonify({
            "error": "Search query must be at least 2 characters"
        }), 400
    
    try:
        if RAILRADAR_AVAILABLE and railway_api:
            # Search using RailRadar API
            results = railway_api.search_station_by_name(query)
            if results:
                return jsonify({
                    "query": query,
                    "results": [
                        {
                            "name": s["name"],
                            "code": s["code"],
                            "state": s.get("state", "")
                        }
                        for s in results[:20]  # Return top 20 matches
                    ],
                    "count": len(results),
                    "source": "RailRadar API"
                })
        
        # Fallback to local search
        from station_codes import search_stations
        local_results = search_stations(query)
        return jsonify({
            "query": query,
            "results": local_results[:20],
            "count": len(local_results),
            "source": "Local Database"
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Error searching stations: {str(e)}"
        }), 500

@app.route('/api/station-codes')
def get_station_codes():
    """Get all station codes with their names"""
    try:
        return jsonify({
            "station_codes": [
                {"name": name, "code": code}
                for name, code in STATION_CODES.items()
            ],
            "count": len(STATION_CODES),
            "message": "Station names with their IRCTC codes (expandable via RailRadar search)"
        })
    except Exception as e:
        return jsonify({
            "error": f"Error fetching station codes: {str(e)}"
        }), 500

@app.route('/api/station-code/<station_name>')
def get_station_code_by_name(station_name):
    """Get station code for a specific station"""
    code = get_station_code(station_name)
    if code == station_name:
        # Try RailRadar search
        if RAILRADAR_AVAILABLE and railway_api:
            results = railway_api.search_station_by_name(station_name)
            if results:
                return jsonify({
                    "station_name": results[0]["name"],
                    "station_code": results[0]["code"],
                    "source": "RailRadar API"
                })
        
        return jsonify({
            "error": f"Station code not found for {station_name}"
        }), 404
    return jsonify({
        "station_name": station_name,
        "station_code": code,
        "source": "Local Database"
    })

@app.route('/api/train/schedule/<train_no>')
def get_train_schedule(train_no):
    """Get train schedule from RailRadar"""
    if not RAILRADAR_AVAILABLE or not railway_api:
        return jsonify({
            "error": "RailRadar API not available"
        }), 503
    
    try:
        schedule = railway_api.get_train_schedule(train_no)
        
        if not schedule:
            return jsonify({
                "error": f"Schedule not available for train {train_no}"
            }), 404
        
        return jsonify({
            "train_no": train_no,
            "schedule": schedule,
            "message": "Train schedule retrieved from RailRadar",
            "source": "RailRadar.in (FREE API)"
        })
    except Exception as e:
        return jsonify({
            "error": f"Error fetching schedule: {str(e)}"
        }), 500

@app.route('/api/train/live/<train_no>')
def get_live_train_status(train_no):
    """Get live train status from RailRadar"""
    if not RAILRADAR_AVAILABLE or not railway_api:
        return jsonify({
            "error": "RailRadar API not available"
        }), 503
    
    start_date = request.args.get('start_date')
    if not start_date:
        start_date = datetime.now().strftime("%Y-%m-%d")
    
    try:
        live_status = railway_api.get_live_train_status(train_no, start_date)
        
        if not live_status:
            return jsonify({
                "error": f"Live status not available for train {train_no}"
            }), 404
        
        return jsonify({
            "train_no": train_no,
            "live_status": live_status,
            "message": "Live train status retrieved from RailRadar",
            "source": "RailRadar.in (FREE API)"
        })
    except Exception as e:
        return jsonify({
            "error": f"Error fetching live status: {str(e)}"
        }), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    groq_configured = bool(os.getenv("GROQ_API_KEY"))
    
    # Get database size
    db_size = 0
    if RAILRADAR_AVAILABLE and railway_api:
        try:
            stations = railway_api.get_all_stations()
            db_size = len(stations) if stations else len(STATION_CODES)
        except:
            db_size = len(STATION_CODES)
    else:
        db_size = len(STATION_CODES)
    
    return jsonify({
        "status": "healthy",
        "framework": "Flask",
        "timestamp": datetime.now().isoformat(),
        "database_size": db_size,
        "station_coverage": "7000+ via RailRadar" if RAILRADAR_AVAILABLE else f"{len(STATION_CODES)} local",
        "groq_ai_configured": groq_configured,
        "railradar_available": RAILRADAR_AVAILABLE,
        "data_source": "RailRadar.in (FREE)" if RAILRADAR_AVAILABLE else "Local",
        "python_version": os.sys.version,
        "services": {
            "api": "operational",
            "groq_ai": "configured" if groq_configured else "not configured",
            "railradar": "available ✅ FREE" if RAILRADAR_AVAILABLE else "unavailable",
            "live_tracking": "available ✅" if RAILRADAR_AVAILABLE else "unavailable",
            "dynamic_station_search": "available ✅" if RAILRADAR_AVAILABLE else "limited"
        }
    })

@app.route('/api/config')
def get_config():
    """Get configuration status"""
    return jsonify({
        "framework": "Flask",
        "groq_api_key": "configured ✅" if os.getenv("GROQ_API_KEY") else "missing ⚠️",
        "railradar_api": "available ✅ (FREE - No key needed)" if RAILRADAR_AVAILABLE else "not installed ⚠️",
        "station_coverage": "7,000+ stations via RailRadar API" if RAILRADAR_AVAILABLE else "150+ major stations (local)",
        "setup_instructions": {
            "groq": {
                "status": "configured" if os.getenv("GROQ_API_KEY") else "missing",
                "url": "https://console.groq.com",
                "env_var": "GROQ_API_KEY",
                "description": "Required for AI recommendations",
                "cost": "FREE with generous limits"
            },
            "railradar": {
                "status": "available" if RAILRADAR_AVAILABLE else "missing",
                "url": "https://railradar.in",
                "file": "live_api.py",
                "description": "FREE API - No authentication required!",
                "cost": "100% FREE - No limits!",
                "features": [
                    "Search from 7,000+ stations",
                    "Real-time train data",
                    "Dynamic station search",
                    "No rate limits"
                ]
            }
        }
    })

@app.route('/api/stats')
def get_stats():
    """Get application statistics"""
    
    total_trains = "13,000+" if RAILRADAR_AVAILABLE else "Limited"
    total_stations = 0
    
    if RAILRADAR_AVAILABLE and railway_api:
        try:
            stations = railway_api.get_all_stations()
            total_stations = len(stations) if stations else len(STATION_CODES)
        except:
            total_stations = len(STATION_CODES)
    else:
        total_stations = len(STATION_CODES)
    
    return jsonify({
        "total_trains": total_trains,
        "total_stations": total_stations,
        "station_coverage": "All Indian Railway stations" if RAILRADAR_AVAILABLE else "Major stations only",
        "api_version": "3.0.0-flask",
        "framework": "Flask",
        "data_source": "RailRadar.in (FREE API)" if RAILRADAR_AVAILABLE else "Local Database",
        "features": [
            "Direct train search",
            "Top 10 fastest connecting trains",
            "AI recommendations (Groq)",
            "Live train tracking" if RAILRADAR_AVAILABLE else "Static data",
            "Real-time seat availability" if RAILRADAR_AVAILABLE else "Mock availability",
            "Dynamic station search - ANY station" if RAILRADAR_AVAILABLE else "Limited station coverage",
            "Station code mapping",
            "FREE API - No authentication needed" if RAILRADAR_AVAILABLE else "Limited data"
        ]
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚂 Indian Railway Search API with RailRadar & Groq AI (Flask)")
    print("="*60)
    
    # Check for Groq API key
    if not os.getenv("GROQ_API_KEY"):
        print("\n⚠️  WARNING: GROQ_API_KEY not found in environment variables")
        print("   AI recommendations will not work.")
        print("   Get your FREE key from https://console.groq.com")
    else:
        print("\n✅ Groq AI: Configured")
    
    if not RAILRADAR_AVAILABLE:
        print("\n⚠️  WARNING: live_api.py not found")
        print("   Using local train data (limited to 150+ major stations).")
        print("   Copy the RailRadar integration file to live_api.py")
    else:
        print("\n✅ RailRadar API: Available (FREE - No authentication needed!)")
        print("   🎉 Real-time train data from railradar.in")
        print("   🌟 Dynamic station search - search ANY Indian Railway station!")
    
    print("\n" + "="*60)
    print("🎉 FLASK BENEFITS:")
    print("  ✅ Simpler, more Pythonic than FastAPI")
    print("  ✅ Easier to debug and understand")
    print("  ✅ Better for smaller projects")
    print("  ✅ Real-time seat availability endpoint added!")
    print("="*60)
    
    print("\nStarting Flask server on http://localhost:8000")
    print("API Endpoints:")
    print("  - POST /api/search-trains")
    print("  - POST /api/seat-availability (NEW!)")
    print("  - GET  /api/stations")
    print("  - GET  /api/health")
    print("="*60 + "\n")
    
    app.run(host="0.0.0.0", port=8000, debug=True, threaded=True, use_reloader=False)