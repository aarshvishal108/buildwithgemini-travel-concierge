# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import os
import urllib.parse
import urllib.request
import uuid
from typing import Optional
from zoneinfo import ZoneInfo

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from dotenv import load_dotenv
from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.load_memory_tool import LoadMemoryTool
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore, storage
from google.genai import types

from .a2ui_utils import a2ui_callback


load_dotenv()

# Hardcoded GCP Project ID and Storage Bucket
PROJECT_ID = "qwiklabs-gcp-02-c9026da3ba37"
BUCKET_NAME = "wanderlust-travel-assets-qwiklabs-gcp-02-c9026da3ba37"
MEMORY_BANK_ID = "5179427643522547712"

# Set memory & vertexai environment variables so it is picked up when deployed or run locally
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
os.environ.setdefault("MEMORY_SERVICE_URI", f"agentengine://{MEMORY_BANK_ID}")



def memory_bank_service_builder():
    return VertexAiMemoryBankService(
        project=PROJECT_ID,
        location="us-east1",
        agent_engine_id=MEMORY_BANK_ID,
    )


async def generate_memories_callback(callback_context: CallbackContext):
    try:
        await callback_context.add_session_to_memory()
    except Exception:
        pass
    return None



# Setup Code Executor from deployment_metadata.json
metadata_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "deployment_metadata.json")
agent_engine_id = "projects/113901312269/locations/us-east1/reasoningEngines/5179427643522547712"
sandbox_id = None

if os.path.exists(metadata_file):
    try:
        with open(metadata_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
            if meta.get("remote_agent_runtime_id"):
                agent_engine_id = meta["remote_agent_runtime_id"]
            if meta.get("sandbox_resource_name"):
                sandbox_id = meta["sandbox_resource_name"]
    except Exception:
        pass

if sandbox_id:
    code_executor = AgentEngineSandboxCodeExecutor(sandbox_resource_name=sandbox_id)
else:
    code_executor = AgentEngineSandboxCodeExecutor(agent_engine_resource_name=agent_engine_id)

db = firestore.Client(project=PROJECT_ID)



def generate_destination_image(
    tool_context: ToolContext,
    destination_name: str,
    style_description: str = "",
) -> str:
    """Generate a high-quality travel image for a destination using Gemini, save it as a session artifact, and upload to public Cloud Storage.

    Args:
        tool_context: ADK ToolContext instance for saving session artifacts.
        destination_name: Name of the destination or attraction (e.g. "Kyoto Arashiyama Bamboo Grove", "Eiffel Tower", "Central Park").
        style_description: Optional artistic or thematic style (e.g. "golden hour", "panoramic view", "vibrant watercolor").

    Returns:
        Public Cloud Storage HTTPS URL of the generated image.
    """
    prompt = f"Generate a stunning, scenic travel photograph of {destination_name}."
    if style_description:
        prompt += f" Style: {style_description}."

    # Call gemini-3.1-flash-lite-image in global region
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    res = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
    )

    img_bytes = None
    mime_type = "image/jpeg"
    for part in res.candidates[0].content.parts:
        if hasattr(part, "inline_data") and part.inline_data:
            img_bytes = part.inline_data.data
            if getattr(part.inline_data, "mime_type", None):
                mime_type = part.inline_data.mime_type
            break

    if not img_bytes:
        return f"Failed to generate image for destination '{destination_name}'."

    file_id = f"destination-{uuid.uuid4().hex[:8]}.jpg"

    # 1. Save artifact with tool_context so it appears in Playground Artifacts panel
    artifact_part = types.Part.from_bytes(data=img_bytes, mime_type=mime_type)
    tool_context.save_artifact(filename=file_id, artifact=artifact_part)



    # 2. Upload same image bytes to public Cloud Storage bucket
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(file_id)
    blob.upload_from_string(img_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{file_id}"
    return public_url


def generate_destination_video(
    tool_context: ToolContext,
    destination_name: str,
    scene_description: str = "",
) -> str:
    """Generate a short video clip for a destination using Gemini Omni (gemini-omni-flash-preview), save it as a session artifact, and upload to public Cloud Storage.

    Args:
        tool_context: ADK ToolContext instance for saving session artifacts.
        destination_name: Name of the destination, attraction, or landmark (e.g. "Kyoto Arashiyama Bamboo Grove", "Eiffel Tower", "Santorini Sunset").
        scene_description: Optional description of camera movement, lighting, or action in the video.

    Returns:
        Public Cloud Storage HTTPS URL of the generated video.
    """
    prompt = f"Generate a short video showing scenic view of {destination_name}."
    if scene_description:
        prompt += f" Scene details: {scene_description}."

    # Call gemini-omni-flash-preview model in global region
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    res = client.models.generate_content(
        model="gemini-omni-flash-preview",
        contents=prompt,
    )

    video_bytes = None
    mime_type = "video/mp4"
    if res.candidates and res.candidates[0].content and res.candidates[0].content.parts:
        for part in res.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                video_bytes = part.inline_data.data
                if getattr(part.inline_data, "mime_type", None):
                    mime_type = part.inline_data.mime_type
                break

    if not video_bytes:
        return f"Failed to generate video for destination '{destination_name}'."

    file_id = f"video-{uuid.uuid4().hex[:8]}.mp4"

    # 1. Save artifact with tool_context so it appears in Playground Artifacts panel
    artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
    tool_context.save_artifact(filename=file_id, artifact=artifact_part)

    # 2. Upload same video bytes to public Cloud Storage bucket
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(file_id)
    blob.upload_from_string(video_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{file_id}"
    return public_url


def geocode_address(address: str) -> str:


    """Geocode an address or location name into geographic coordinates (latitude and longitude).

    Args:
        address: The address or place name to geocode (e.g., "Eiffel Tower, Paris", "Asakusa, Tokyo").

    Returns:
        The formatted address and geographic coordinates.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY is not set in the environment."

    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(address)}&key={api_key}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))

        if data.get("status") != "OK" or not data.get("results"):
            return f"Could not geocode address '{address}'. Status: {data.get('status')}"

        first = data["results"][0]
        formatted_address = first.get("formatted_address", address)
        lat = first["geometry"]["location"]["lat"]
        lng = first["geometry"]["location"]["lng"]
        return f"Address: '{formatted_address}' | Coordinates: Latitude {lat}, Longitude {lng}"
    except Exception as e:
        return f"Error calling Geocoding API: {e}"


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "tourist_attraction",
    radius_meters: float = 2000.0,
) -> str:
    """Find nearby places of a given type around latitude and longitude using Google Places API (New).

    Args:
        latitude: Center latitude coordinate.
        longitude: Center longitude coordinate.
        place_type: Type of place to search for (e.g. 'tourist_attraction', 'restaurant', 'museum', 'lodging', 'cafe').
        radius_meters: Search radius in meters (default 2000 meters).

    Returns:
        List of nearby places with name, formatted address, and location coordinates.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY is not set in the environment."

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }
    body = {
        "includedTypes": [place_type],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": float(radius_meters),
            }
        },
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))

        places = data.get("places", [])
        if not places:
            return f"No nearby places of type '{place_type}' found within {radius_meters}m."

        results = [f"Nearby '{place_type}' places within {radius_meters}m:"]
        for p in places:
            name = p.get("displayName", {}).get("text", "N/A")
            addr = p.get("formattedAddress", "N/A")
            loc = p.get("location", {})
            lat_val = loc.get("latitude", "N/A")
            lng_val = loc.get("longitude", "N/A")
            results.append(f"• Name: {name} | Address: {addr} | Location: ({lat_val}, {lng_val})")

        return "\n".join(results)
    except Exception as e:
        return f"Error calling Places API (New): {e}"


def get_exchange_rate(base_currency: str = "USD", target_currency: str = "JPY") -> str:

    """Fetch real-time foreign exchange rates for travel expense planning using an open currency API.

    Args:
        base_currency: The base 3-letter currency code (e.g. "USD", "EUR", "GBP").
        target_currency: Optional target 3-letter currency code (e.g. "JPY", "EUR", "CAD").

    Returns:
        A string containing real-time exchange rates.
    """
    base = base_currency.strip().upper() if base_currency else "USD"
    target = target_currency.strip().upper() if target_currency else None

    # Check for optional API key in environment
    api_key = os.environ.get("EXCHANGE_RATE_API_KEY", "")
    if api_key:
        url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{base}"
    else:
        url = f"https://open.er-api.com/v6/latest/{base}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TravelConcierge/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))

        if data.get("result") != "success":
            return f"Failed to retrieve exchange rates for base currency '{base}'."

        rates = data.get("rates", {})
        update_time = data.get("time_last_update_utc", "Recently")

        if target:
            if target in rates:
                return f"1 {base} = {rates[target]:.4f} {target} (Updated: {update_time})"
            return f"Target currency '{target}' not found in exchange rate data."

        popular = ["EUR", "JPY", "GBP", "CAD", "AUD", "CHF"]
        summary = [f"Exchange rates for 1 {base} (Updated: {update_time}):"]
        for curr in popular:
            if curr in rates and curr != base:
                summary.append(f"  • {curr}: {rates[curr]:.4f}")
        return "\n".join(summary)
    except Exception as e:
        return f"Error fetching exchange rate data: {e}"


def generate_travel_postcard(destination_name: str, scene_description: str = "") -> str:

    """Generate a picturesque travel postcard image for a destination and return its public URL.

    Args:
        destination_name: The name of the destination (e.g., "Senso-ji Temple in Tokyo", "Eiffel Tower in Paris").
        scene_description: Optional extra details to include in the scene (e.g., "cherry blossom season at sunset", "snowy winter landscape").

    Returns:
        The public HTTP URL of the generated postcard image.
    """
    prompt = f"Generate a scenic, vibrant travel postcard image of {destination_name}."
    if scene_description:
        prompt += f" Details: {scene_description}."

    client = genai.Client(vertexai=True, project=PROJECT_ID, location="us-central1")
    res = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=prompt,
    )

    img_bytes = None
    for part in res.candidates[0].content.parts:
        if hasattr(part, "inline_data") and part.inline_data:
            img_bytes = part.inline_data.data
            break

    if not img_bytes:
        return f"Failed to generate postcard image for '{destination_name}'."

    file_id = f"postcard-{uuid.uuid4().hex[:8]}.jpg"
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(file_id)
    blob.upload_from_string(img_bytes, content_type="image/jpeg")

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{file_id}"
    return f"Generated postcard for '{destination_name}': {public_url}"


def search_destinations(city: Optional[str] = None, category: Optional[str] = None) -> str:
    """Search for travel destinations stored in the Firestore database.

    Args:
        city: Optional city name to filter destinations by (e.g. "Tokyo", "Paris", "San Francisco").
        category: Optional category to filter destinations by (e.g. "Culture & Heritage", "Nature & Scenery").

    Returns:
        A list of matching travel destination summaries.
    """
    collection_ref = db.collection("destinations")
    docs = collection_ref.stream()
    results = []

    for doc in docs:
        data = doc.to_dict()
        doc_city = data.get("city", "")
        doc_category = data.get("category", "")

        match_city = not city or city.lower() in doc_city.lower()
        match_cat = not category or category.lower() in doc_category.lower()

        if match_city and match_cat:
            results.append(
                f"ID: {doc.id} | Name: {data.get('name')} | City: {doc_city}, {data.get('country')} | "
                f"Category: {doc_category} | Budget: ${data.get('avg_daily_budget_usd')}/day | Rating: {data.get('rating')}"
            )

    if not results:
        return "No destinations found matching your criteria in the database."
    return "\n".join(results)


def get_destination_details(destination_id: str) -> str:
    """Retrieve detailed information about a specific travel destination from Firestore.

    Args:
        destination_id: The unique ID of the destination (e.g. "tokyo-sensoji", "paris-louvre").

    Returns:
        Detailed information about the travel destination.
    """
    doc_ref = db.collection("destinations").document(destination_id)
    doc = doc_ref.get()
    if not doc.exists:
        return f"Destination with ID '{destination_id}' was not found in the database."

    data = doc.to_dict()
    tags_str = ", ".join(data.get("tags", [])) if isinstance(data.get("tags"), list) else data.get("tags", "")
    return (
        f"Destination ID: {doc.id}\n"
        f"Name: {data.get('name')}\n"
        f"Location: {data.get('city')}, {data.get('country')}\n"
        f"Category: {data.get('category')}\n"
        f"Description: {data.get('description')}\n"
        f"Avg Daily Budget: ${data.get('avg_daily_budget_usd')} USD\n"
        f"Rating: {data.get('rating')}/5.0\n"
        f"Tags: {tags_str}"
    )


def add_destination(
    name: str,
    city: str,
    country: str,
    category: str,
    description: str,
    avg_daily_budget_usd: int,
    tags: str = "",
) -> str:
    """Add a new travel destination to the Firestore database.

    Args:
        name: Name of the landmark or attraction.
        city: City where the destination is located.
        country: Country where the destination is located.
        category: Category (e.g., 'Culture & Heritage', 'Outdoors & Sightseeing').
        description: A brief summary or overview of the attraction.
        avg_daily_budget_usd: Estimated daily budget in USD.
        tags: Optional comma-separated tags (e.g. 'history, temple, food').

    Returns:
        A confirmation message with the assigned destination ID.
    """
    dest_id = f"{city.lower().replace(' ', '-')}-{name.lower().replace(' ', '-').replace('&', 'and')}"
    dest_id = "".join(c for c in dest_id if c.isalnum() or c == "-")

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    doc_data = {
        "destination_id": dest_id,
        "name": name,
        "city": city,
        "country": country,
        "category": category,
        "description": description,
        "avg_daily_budget_usd": avg_daily_budget_usd,
        "rating": 5.0,
        "tags": tag_list,
    }

    db.collection("destinations").document(dest_id).set(doc_data)
    return f"Successfully added destination '{name}' to Firestore with ID '{dest_id}'."


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        query: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    elif "tokyo" in query.lower():
        tz_identifier = "Asia/Tokyo"
    elif "paris" in query.lower():
        tz_identifier = "Europe/Paris"
    elif "nyc" in query.lower() or "new york" in query.lower():
        tz_identifier = "America/New_York"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


def calculate_itinerary_budget(
    daily_budget_usd: float,
    num_days: int,
    num_travelers: int = 1,
    contingency_percent: float = 10.0,
) -> str:
    """Calculate trip budget breakdown including totals, per-person costs, and contingency funds.

    Args:
        daily_budget_usd: Estimated average daily expense per person in USD.
        num_days: Duration of the trip in days.
        num_travelers: Total number of travelers (default 1).
        contingency_percent: Percentage allocated for unexpected expenses (default 10%).

    Returns:
        Formatted trip budget breakdown summary.
    """
    subtotal = daily_budget_usd * num_days * num_travelers
    contingency = subtotal * (contingency_percent / 100.0)
    total = subtotal + contingency
    per_person = total / max(num_travelers, 1)

    return (
        f"--- Trip Budget Breakdown ---\n"
        f"Trip Duration: {num_days} days | Travelers: {num_travelers}\n"
        f"Daily Rate per Person: ${daily_budget_usd:.2f} USD\n"
        f"Subtotal: ${subtotal:.2f} USD\n"
        f"Contingency Buffer ({contingency_percent}%): ${contingency:.2f} USD\n"
        f"Total Estimated Budget: ${total:.2f} USD\n"
        f"Per Person Total: ${per_person:.2f} USD"
    )


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are Wanderlust, an expert worldwide Travel & Itinerary Concierge with long-term memory. "
        "You strictly remember and track all user details, references, personal facts, names, travel preferences, "
        "dietary restrictions, budget constraints, home location, past trips, and explicit instructions across all sessions. "
        "When the user provides any personal detail or preference, acknowledge it and incorporate it seamlessly into future responses. "
        "Use your memory tools (PreloadMemoryTool and LoadMemoryTool) to recall and verify user details. "
        "IMPORTANT FOR DESTINATION RECOMMENDATIONS: You have access to a local database tool (`search_destinations`). "
        "If a queried city, country, or region (such as Maharashtra, Norway, or Europe) is not found in the local database, "
        "do NOT refuse or say you cannot help. Instead, use your expert travel knowledge, Geocoding API, and Places API to "
        "provide rich, high-quality destination recommendations and travel advice."
    ),
    workflow_description="Analyze the request, search local database or use general travel expertise/APIs, and return structured UI when appropriate.",

    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
        client_kwargs={
            "vertexai": True,
            "project": PROJECT_ID,
            "location": "us-east1",
        },
    ),
    code_executor=code_executor,
    instruction=a2ui_instruction,
    tools=[
        PreloadMemoryTool(),
        LoadMemoryTool(),
        generate_destination_image,
        generate_destination_video,
        geocode_address,
        find_nearby_places,
        get_exchange_rate,
        calculate_itinerary_budget,
        generate_travel_postcard,
        search_destinations,
        get_destination_details,
        add_destination,
        get_weather,
        get_current_time,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)








app = App(
    root_agent=root_agent,
    name="app",
)



