"""
Test API with structured logging and request_id correlation

Run this script while the API is running to test logging.
"""
import requests
import uuid
import json


def test_health_check():
    """Test health endpoint"""
    print("\n" + "="*60)
    print("TEST 1: Health Check (no request_id)")
    print("="*60)

    response = requests.get("http://localhost:8000/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print(f"X-Request-ID: {response.headers.get('X-Request-ID')}")


def test_with_custom_request_id():
    """Test with custom X-Request-ID header"""
    print("\n" + "="*60)
    print("TEST 2: Custom X-Request-ID")
    print("="*60)

    custom_id = str(uuid.uuid4())
    print(f"Sending request_id: {custom_id}")

    response = requests.get(
        "http://localhost:8000/health",
        headers={"X-Request-ID": custom_id}
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print(f"X-Request-ID in response: {response.headers.get('X-Request-ID')}")
    print(f"Match: {response.headers.get('X-Request-ID') == custom_id}")


def test_item_endpoint():
    """Test item endpoints (if available)"""
    print("\n" + "="*60)
    print("TEST 3: Item Endpoints")
    print("="*60)

    # List items
    response = requests.get("http://localhost:8000/api/v1/items")
    print(f"GET /api/v1/items")
    print(f"Status: {response.status_code}")
    print(f"X-Request-ID: {response.headers.get('X-Request-ID')}")

    if response.status_code == 200:
        items = response.json()
        print(f"Items count: {len(items)}")


def test_concurrent_requests():
    """Test multiple concurrent requests (context isolation)"""
    print("\n" + "="*60)
    print("TEST 4: Concurrent Requests (Context Isolation)")
    print("="*60)

    import concurrent.futures

    request_ids = [str(uuid.uuid4()) for _ in range(5)]

    def make_request(req_id):
        response = requests.get(
            "http://localhost:8000/health",
            headers={"X-Request-ID": req_id}
        )
        return req_id, response.headers.get("X-Request-ID")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request, rid) for rid in request_ids]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    print(f"Sent {len(request_ids)} concurrent requests")
    all_match = all(sent == received for sent, received in results)
    print(f"All request_ids matched: {all_match}")

    if not all_match:
        print("⚠️ Context leak detected!")
        for sent, received in results:
            if sent != received:
                print(f"  Mismatch: sent={sent}, received={received}")


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("API LOGGING TEST SUITE")
    print("="*80)
    print("\nMake sure the API is running: uvicorn api.main:app --reload")
    print("Check logs in the terminal running the API")
    print("="*80)

    try:
        # Test health check
        test_health_check()

        # Test custom request_id
        test_with_custom_request_id()

        # Test item endpoint
        test_item_endpoint()

        # Test concurrent requests
        test_concurrent_requests()

        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETED")
        print("="*80)
        print("\nCheck the API logs to verify:")
        print("1. Each request has a unique request_id")
        print("2. All logs within a request share the same request_id")
        print("3. Request duration is logged")
        print("4. X-Request-ID appears in response headers")
        print("\n")

    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to API")
        print("Make sure the API is running:")
        print("  cd develop/backend")
        print("  uvicorn api.main:app --reload")
        print("\n")


if __name__ == "__main__":
    main()
