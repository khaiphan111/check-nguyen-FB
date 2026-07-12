import httpx
import json

async def check_ig(username):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "X-IG-App-ID": "936619743392459", # Standard web app ID
    }
    url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
    
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        resp = await client.get(url)
        print("Status:", resp.status_code)
        try:
            data = resp.json()
            print("Success, found user info")
        except:
            print("Failed to parse JSON. Response:")
            print(resp.text[:500])

import asyncio
asyncio.run(check_ig("cristiano"))
