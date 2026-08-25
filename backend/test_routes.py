import main

print("FastAPI Routes:")
for route in main.app.routes:
    print(f"  {route.path} - {route.methods if hasattr(route, 'methods') else 'N/A'}")
