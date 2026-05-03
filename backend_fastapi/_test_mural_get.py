"""Test mural GET endpoint."""
import requests

# Test different ports
for port in [8000, 8060, 8075, 8085]:
    try:
        r = requests.get(f"http://127.0.0.1:{port}/", timeout=3)
        print(f"Port {port}: OK - {r.json().get('status','?')}")
    except Exception as e:
        print(f"Port {port}: {type(e).__name__}")

# Test mural on working port  
BASE = "http://127.0.0.1:8085"
s = requests.Session()
s.post(f"{BASE}/auth/login", json={"username":"authtest","password":"senha123#"})
r = s.get(f"{BASE}/api/mural/", timeout=5)
print(f"\nMural GET: status={r.status_code}")
print(f"  headers: {dict(r.headers)}")
print(f"  body: {r.text[:300]}")
