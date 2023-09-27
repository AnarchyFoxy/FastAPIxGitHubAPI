from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import List
from fastapi.responses import JSONResponse
import httpx

app = FastAPI()

GITHUB_API_URL = "https://api.github.com"
GITHUB_API_TOKEN = "5550123"  # Replace this with your personal token

class GitHubRepository(BaseModel):
    name: str
    owner: dict
    branches: List[dict]

# HTTPX client declaration outside the function that handles the request
async_client = httpx.AsyncClient()

@app.on_event("shutdown")
async def close_http_client():
    # Shutting down the HTTPX client while closing the application
    await async_client.aclose()

@app.get("/repositories", response_model=List[GitHubRepository])
async def list_user_repositories(
    username: str = Header(..., title="Username"),
    accept: str = Header(None, title="Accept", description="Accept header"),
):
    try:
        if accept != "application/json":
            raise HTTPException(status_code=406, detail="Unsupported Media Type")

        headers = {"Authorization": f"Bearer {GITHUB_API_TOKEN}"}
        github_api_url = f"{GITHUB_API_URL}/users/{username}/repos"
        response = await async_client.get(github_api_url, headers=headers)

        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="User not found")
        elif response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"GitHub API error: {response.text}")

        repositories_data = response.json()
        repositories_info = []
        for repo_data in repositories_data:
            if not repo_data.get("fork", False):
                branches_url = repo_data["branches_url"].replace("{/branch}", "")
                branches_response = await async_client.get(branches_url, headers=headers)
                if branches_response.status_code == 200:
                    branches_data = branches_response.json()
                    branches_info = [{"name": branch["name"], "last_commit_sha": branch["commit"]["sha"]} for branch in branches_data]
                    repositories_info.append({
                        "name": repo_data["name"],
                        "owner": {"login": repo_data["owner"]["login"]},
                        "branches": branches_info,
                    })

        return repositories_info

    except HTTPException as http_error:
        return JSONResponse(content={"status": http_error.status_code, "message": http_error.detail}, status_code=http_error.status_code)

    except Exception as e:
        return JSONResponse(content={"status": 500, "message": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)