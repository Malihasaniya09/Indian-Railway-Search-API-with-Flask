# Indian-Railway-Search-API-with-Flask

A powerful Flask-based REST API for searching Indian Railway trains with real-time seat availability, AI-powered recommendations, and intelligent route planning. Built with LangGraph for agentic workflows and integrated with RailRadar.in's free API.
✨ Key Features
🎯 Core Functionality

Direct Train Search - Find direct trains between any two stations
Connecting Trains - Smart routing through major junctions (top 10 fastest routes)
Real-time Seat Availability - Intelligent availability estimation based on train type, route popularity, and booking patterns
Dynamic Fare Calculation - Distance and class-based pricing
AI Recommendations - Powered by Groq AI (Llama 3.3 70B)

🌟 Advanced Features

7,000+ Stations - Access to all Indian Railway stations via dynamic search
Alternative Station Suggestions - Smart fallback when direct routes aren't available
Live Train Tracking - Real-time train status and schedules
Multi-class Support - 1A, 2A, 3A, SL, 2S, CC classes
No Authentication Required - Free RailRadar API (no rate limits!)

🚀 Quick Start

🚀 Quick Start
Prerequisites

Python 3.8 or higher
pip package manager

Installation

1. Clone the repository

git clone https://github.com/Malihasaniya09/railway-search-api.git
cd railway-search-api

2. Install dependencies

pip install -r requirements.txt

3. Set up environment variables

Create a .env file in the root directory:

GROQ_API_KEY=your_groq_api_key_here

Get your free Groq API key from https://console.groq.com

4. Run the Flask API server

python flask_api.py

5.  Run the Streamlit UI

streamlit run streamlit_app.py

How It Works

1. Station Resolution: Converts city/station names to official railway codes
2. Direct Search: Queries RailRadar API for direct trains
3. Alternative Stations: Suggests nearby stations if no direct routes found
4. Connecting Routes: Finds connections via 25 major junction stations
5. Seat Availability: Calculates intelligent availability based on:

Train type (Rajdhani, Duronto, Express, etc.)
Days until travel (dynamic booking patterns)
Route popularity (major routes have less availability)
Distance-based fare calculation
6. AI Recommendations: Groq LLM analyzes all options and provides personalized advice
7. Response: Returns top 10 fastest connections with complete details

🎨 Features in Detail
Intelligent Seat Availability
The API provides realistic seat availability estimation (not actual IRCTC booking data) based on:

-Train Type Analysis: Rajdhani/Shatabdi have different capacity than Mail/Express

-Temporal Patterns: Availability decreases closer to travel date

-Route Popularity: Delhi-Mumbai has less availability than smaller routes

-Class-based Pricing: Automatic fare adjustment for 1A, 2A, 3A, SL, 2S, CC

-Distance Calculation: Fare increases with journey distance

Smart Station Fallbacks
When no direct trains are found, the system automatically:

-Suggests alternative stations in the same city

-Provides regional alternatives within 70-160km

-Explains why each alternative is recommended
