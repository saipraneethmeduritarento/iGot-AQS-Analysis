
import sys
import json
from google import genai
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from scripts.assessment_quality_score.config import settings

print(f"Project ID: {settings.google_project_id}")
print(f"Location: {settings.google_project_location}")
print(f"Model Names String: {settings.gemini_model_name}")

model_names_str = settings.gemini_model_name

try:
    if model_names_str.startswith("["):
        model_names = json.loads(model_names_str)
    elif "," in model_names_str:
        model_names = [m.strip() for m in model_names_str.split(",")]
    else:
        model_names = [model_names_str]
except Exception as e:
    print(f"Error parsing model names: {e}")
    model_names = []

client = genai.Client(
    vertexai=True,
    project=settings.google_project_id,
    location=settings.google_project_location
)

for model_name in model_names:
    print(f"\nTesting model: {model_name}")
    try:
        response = client.models.generate_content(
            model=model_name,
            contents="Hello, can you hear me?"
        )
        print(f"Success! Response: {response.text}")
    except Exception as e:
        print(f"Failed to connect to {model_name}: {e}")

