import os
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-02-c9026da3ba37"

def seed_database():
    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection("destinations")
    
    seeded_items = [
        {
            "destination_id": "tokyo-sensoji",
            "name": "Senso-ji Temple & Asakusa",
            "city": "Tokyo",
            "country": "Japan",
            "category": "Culture & Heritage",
            "description": "Ancient Buddhist temple located in Asakusa, surrounded by traditional market stalls.",
            "avg_daily_budget_usd": 120,
            "rating": 4.8,
            "tags": ["temple", "history", "food", "walking"]
        },
        {
            "destination_id": "paris-louvre",
            "name": "Louvre Museum & Tuileries",
            "city": "Paris",
            "country": "France",
            "category": "Arts & Museums",
            "description": "World's largest art museum housing iconic masterpieces like the Mona Lisa.",
            "avg_daily_budget_usd": 180,
            "rating": 4.9,
            "tags": ["art", "museum", "landmarks", "romantic"]
        },
        {
            "destination_id": "sf-golden-gate",
            "name": "Golden Gate Park & Bridge",
            "city": "San Francisco",
            "country": "USA",
            "category": "Outdoors & Landmarks",
            "description": "Iconic suspension bridge and expansive urban park with gardens and ocean views.",
            "avg_daily_budget_usd": 150,
            "rating": 4.7,
            "tags": ["bridge", "nature", "biking", "views"]
        },
        {
            "destination_id": "kyoto-arashiyama",
            "name": "Arashiyama Bamboo Grove",
            "city": "Kyoto",
            "country": "Japan",
            "category": "Nature & Scenery",
            "description": "Towering bamboo stalks creating a serene, immersive walking path in western Kyoto.",
            "avg_daily_budget_usd": 100,
            "rating": 4.8,
            "tags": ["nature", "bamboo", "scenic", "photography"]
        },
        {
            "destination_id": "nyc-central-park",
            "name": "Central Park & Bethesda Terrace",
            "city": "New York",
            "country": "USA",
            "category": "Outdoors & Sightseeing",
            "description": "Sprawling 843-acre green oasis in Manhattan featuring lakes, bridges, and walking trails.",
            "avg_daily_budget_usd": 160,
            "rating": 4.8,
            "tags": ["park", "landmarks", "walking", "skyline"]
        }
    ]
    
    for item in seeded_items:
        doc_ref = collection_ref.document(item["destination_id"])
        doc_ref.set(item)
        print(f"Seeded destination: {item['name']} ({item['destination_id']})")

if __name__ == "__main__":
    seed_database()
