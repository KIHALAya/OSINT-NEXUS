import httpx
import asyncio
import sys

async def test_end_to_end():
    base_url = "http://localhost:8000"
    
    # 1. Create Case
    print("--- Creating Case ---")
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{base_url}/api/cases", json={
            "subject_name": "Test Subject",
            "subject_description": "A test case for end-to-end verification. Missing in Casablanca near Morocco Mall.",
            "priority": "high"
        })
        if resp.status_code != 201:
            print(f"Failed to create case: {resp.text}")
            return
        
        case_id = resp.json()["case_id"]
        print(f"Created Case: {case_id}")

        # 2. Run Investigation
        print(f"--- Running Investigation for {case_id} ---")
        resp = await client.post(f"{base_url}/api/cases/{case_id}/run")
        if resp.status_code != 200:
            print(f"Failed to run investigation: {resp.text}")
            return
        print(resp.json()["message"])

        # 3. Poll for results
        print("--- Polling for results (60s) ---")
        for i in range(12):
            await asyncio.sleep(5)
            leads = await client.get(f"{base_url}/api/cases/{case_id}/leads")
            posts = await client.get(f"{base_url}/api/cases/{case_id}/posts")
            clusters = await client.get(f"{base_url}/api/cases/{case_id}/clusters")
            
            print(f"Update {i+1}: Posts={len(posts.json())} Clusters={len(clusters.json())} Leads={len(leads.json())}")
            
            if len(leads.json()) > 0:
                print("Leads found! Success.")
                break

if __name__ == "__main__":
    asyncio.run(test_end_to_end())
