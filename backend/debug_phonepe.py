"""Debug PhonePe API call"""
import asyncio
import base64
import hashlib
import json

import httpx

from src.oncall_agent.config import get_config


async def test_phonepe_api():
    config = get_config()

    # Test data
    merchant_id = config.phonepe_merchant_id
    salt_key = config.phonepe_salt_key
    salt_index = config.phonepe_salt_index
    base_url = config.phonepe_base_url

    print("Using config:")
    print(f"  Merchant ID: {merchant_id}")
    print(f"  Salt Key: {salt_key}")
    print(f"  Salt Index: {salt_index}")
    print(f"  Base URL: {base_url}")

    # Create payload
    payload_dict = {
        "merchantId": merchant_id,
        "merchantTransactionId": "TEST123456789",
        "merchantUserId": "USER123",
        "amount": 10000,
        "redirectUrl": "http://localhost:3000/payment/redirect",
        "redirectMode": "REDIRECT",
        "callbackUrl": "http://localhost:8000/api/v1/payments/callback",
        "mobileNumber": "9999999999",
        "paymentInstrument": {
            "type": "PAY_PAGE"
        }
    }

    # Convert to base64
    payload_json = json.dumps(payload_dict)
    print(f"\nPayload JSON: {payload_json}")

    base64_payload = base64.b64encode(payload_json.encode()).decode()
    print(f"\nBase64 payload: {base64_payload}")

    # Generate checksum
    string_to_hash = base64_payload + "/pg/v1/pay" + salt_key
    sha256_hash = hashlib.sha256(string_to_hash.encode()).hexdigest()
    checksum = sha256_hash + "###" + salt_index
    print(f"\nChecksum: {checksum}")

    # Prepare request
    headers = {
        "Content-Type": "application/json",
        "X-VERIFY": checksum
    }

    request_body = {
        "request": base64_payload
    }

    url = f"{base_url}/pg/v1/pay"
    print(f"\nRequest URL: {url}")
    print(f"Request headers: {headers}")
    print(f"Request body: {json.dumps(request_body, indent=2)}")

    # Make request
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=request_body, headers=headers, timeout=30.0)

        print(f"\nResponse status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response body: {response.text}")

        if response.status_code == 200:
            data = response.json()
            print(f"\nParsed response: {json.dumps(data, indent=2)}")

if __name__ == "__main__":
    asyncio.run(test_phonepe_api())
