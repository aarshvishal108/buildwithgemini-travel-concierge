# Wanderlust — Travel & Itinerary Concierge

Wanderlust is an AI-powered personal travel concierge agent built with Google's **Agent Development Kit (ADK)** and deployed on **Agent Platform**. It assists travelers in discovering destinations, creating custom itineraries, estimating trip budgets, looking up weather, and generating travel media.

![Wanderlust Agent Demo](demo.gif)

---

## 🌟 Key Capabilities & Features

Based on the codebase in `app/`, Wanderlust implements the following core features and integrations:

### 1. 🧠 Long-Term Memory (Vertex AI Memory Bank)
- **Persistent Preferences**: Uses `VertexAiMemoryBankService` (`PreloadMemoryTool` and `LoadMemoryTool`) to remember user details (e.g., favorite travel destinations, budget tier, dietary preferences) across separate chat sessions.
- **Memory Callback**: Automatically updates memory bank upon session completion via `generate_memories_callback`.

### 2. 🗄️ Destination Database (Google Cloud Firestore)
- **Destination Search**: `search_destinations` filters curated destinations by country, tag, and max daily budget.
- **Detailed Lookup**: `get_destination_details` retrieves descriptions, top activities, and local highlights.
- **Community Contributions**: `add_destination` enables users to save custom destinations directly into Firestore.

### 3. 🎨 Generative Media Creation (Gemini AI & Cloud Storage)
- **Image Generation**: `generate_destination_image` and `generate_travel_postcard` generate custom travel artwork and postcards using `gemini-3.1-flash-lite-image`.
- **Video Generation**: `generate_destination_video` creates short video previews using `gemini-omni-flash-preview` in the `global` region.
- **Cloud Storage Integration**: Automatically saves media as session artifacts (`tool_context.save_artifact`) and uploads binary bytes directly to Google Cloud Storage (`google.cloud.storage`).

### 4. 🖼️ A2UI Rich UI Interface
- **Structured Rendering**: Emits A2UI (Agent-to-User Interface) components using `A2uiSchemaManager` (v0.8) and `BasicCatalog`.
- **Rich Output**: Formats travel itineraries, budget breakdowns, and media previews into structured visual cards rather than plain text.

### 5. 🧮 Code Execution Sandbox
- **Budget Calculations**: `calculate_itinerary_budget` executes python allocation algorithms within `AgentEngineSandboxCodeExecutor` for accurate financial breakdowns.

### 6. 🌐 External APIs & Real-Time Services
- **Google Maps Geocoding**: `geocode_address` converts location names into geographic coordinates.
- **Google Places API**: `find_nearby_places` finds nearby attractions, restaurants, and hotels.
- **Currency Exchange**: `get_exchange_rate` converts travel budgets across international currencies via Open Exchange Rates.
- **Weather Forecasts**: `get_weather` fetches real-time weather forecasts via Open-Meteo API.
- **Time Utilities**: `get_current_time` provides current local timestamps for any timezone.

---

## 🏗️ Architecture Overview

```
[ Web Chat Frontend ] 
       │
       ▼ (HTTP / A2A Protocol)
[ FastAPI Proxy ]
       │
       ▼ (Vertex AI Reasoning Engines API)
[ Wanderlust ADK Agent (Agent Runtime) ]
       ├── Vertex AI Memory Bank (Cross-session memory)
       ├── Firestore Database (Destination records)
       ├── Google Cloud Storage (Media bucket)
       ├── Gemini Models (2.5 Flash, 3.1 Flash Lite Image, Omni Flash Preview)
       └── Code Execution Sandbox (Budget engine)
```

---

## 🚀 Running the Project Locally

### Prerequisites
- Python 3.10+
- Google Cloud SDK (`gcloud`) authenticated to your GCP project
- Environment variables configured in `.env` or exported in your shell

### 1. Agent Backend Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set required environment variables:
   ```bash
   export GOOGLE_GENAI_USE_VERTEXAI="true"
   export GOOGLE_MAPS_API_KEY=<your-key>
   export MEMORY_SERVICE_URI="agentengine://<your-memory-bank-id>"
   ```

3. Run the ADK Web Playground locally:
   ```bash
   adk web app
   ```

---

### 2. Frontend Setup

1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```

2. Install frontend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Export the target Agent Engine resource name and directory:
   ```bash
   export AGENT_ENGINE_RESOURCE_NAME="projects/<project-id>/locations/<region>/reasoningEngines/<agent-engine-id>"
   export AGENT_DIRECTORY="app"
   ```

4. Start the FastAPI frontend proxy:
   ```bash
   python main.py
   ```

---

## 📦 Deployment Instructions

### Deploy Agent to Agent Runtime
Deploy the ADK agent using `agents-cli`:
```bash
agents-cli deploy \
  --project <your-gcp-project-id> \
  --region us-east1 \
  --deployment-target agent_runtime \
  --update-env-vars "GOOGLE_MAPS_API_KEY=<your-key>,GOOGLE_GENAI_USE_VERTEXAI=true"
```

### Deploy Frontend to Cloud Run
Deploy the frontend container to Cloud Run:
```bash
gcloud run deploy travel-concierge-frontend \
  --source ./frontend \
  --region us-east1 \
  --allow-unauthenticated \
  --set-env-vars="AGENT_ENGINE_RESOURCE_NAME=<your-resource-name>,AGENT_DIRECTORY=app"
```
