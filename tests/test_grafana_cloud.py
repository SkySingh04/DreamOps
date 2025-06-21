#!/usr/bin/env python3
"""Test Grafana Cloud connection."""

import httpx
import asyncio
from dotenv import load_dotenv
import os

async def test_grafana_cloud():
    load_dotenv()
    
    grafana_url = os.getenv("GRAFANA_URL")
    api_key = os.getenv("GRAFANA_API_KEY")
    
    print(f"Testing Grafana Cloud connection...")
    print(f"URL: {grafana_url}")
    print(f"API Key: {'Set' if api_key and api_key != 'paste-your-service-account-token-here' else 'Not set'}")
    
    if not grafana_url or not api_key or api_key == 'paste-your-service-account-token-here':
        print("\n❌ Please update your .env file with actual Grafana Cloud details")
        return
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{grafana_url}/api/search",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ Successfully connected to Grafana Cloud!")
                print(f"Found {len(data)} dashboards/folders")
                print(f"Grafana is ready for use with your oncall agent!")
            else:
                print(f"\n❌ Connection failed: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_grafana_cloud())