import requests
import json

# Test health endpoint
print("=" * 50)
print("Testing /health endpoint:")
try:
    response = requests.get("http://localhost:8000/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

# Test login endpoint
print("\n" + "=" * 50)
print("Testing /auth/login endpoint:")
try:
    payload = {"email": "demo@example.com", "password": "demo123"}
    response = requests.post("http://localhost:8000/auth/login", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

# Test with /api prefix
print("\n" + "=" * 50)
print("Testing /api/auth/login endpoint:")
try:
    payload = {"email": "demo@example.com", "password": "demo123"}
    response = requests.post("http://localhost:8000/api/auth/login", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
