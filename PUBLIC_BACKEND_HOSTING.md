# Public Backend Hosting

OmniGameDev AI has two parts:

- The Vercel site is the public web IDE.
- The FastAPI backend is the agent that generates, edits, reviews, runs, stores, and exports projects.

For a public product, the backend must be reachable at a public HTTPS URL.

Because this backend can edit and execute generated project code, set `OMNIGAMEDEV_API_TOKEN` for any public backend. The web IDE has a `Backend access code` field in the left panel and sends that code with API requests.

## Current Quick Public Backend

This machine is currently exposing the local backend through Cloudflare Quick Tunnel:

```text
https://pubs-game-endorsed-seats.trycloudflare.com
```

This is useful for testing the public Vercel frontend immediately. It stays online only while this computer, the local backend, and the `cloudflared` process are running.

Restart it with:

```powershell
cd "C:\Users\prave\Downloads\omnigamedev-ai"
.\tools\start_backend.ps1 -AccessCode "your-access-code"
.\tools\start_public_backend_tunnel.ps1
```

## Permanent Backend With Render

Render is the simplest permanent path for this project because it can run the Docker backend and attach a persistent disk for generated projects and memory.

1. Go to `https://render.com`.
2. Click `Sign In`.
3. Click `New +`.
4. Click `Blueprint`.
5. Connect the GitHub repository that contains this folder.
6. Choose the repository.
7. Render should detect `render.yaml`.
8. Enter a value for `OMNIGAMEDEV_API_TOKEN` when Render asks for it.
9. Click `Apply`.
10. Wait until the service finishes deploying.
11. Open the service page.
12. Copy the backend URL. It will look like `https://omnigamedev-ai-backend.onrender.com`.
13. Open the Vercel project dashboard.
14. Go to `Settings`.
15. Click `Environment Variables`.
16. Add `VITE_API_BASE`.
17. Paste the Render backend URL as the value.
18. Select `Production`.
19. Click `Save`.
20. Go to `Deployments`.
21. Click the three dots on the latest deployment.
22. Click `Redeploy`.
23. Open the public Vercel URL.
24. Paste the same `OMNIGAMEDEV_API_TOKEN` value into `Backend access code`.
25. Click `Use`.
26. The backend status should say `Agent backend online`.

The Docker image installs Python, Node.js, and the OmniGameDev dependencies so generated JavaScript and Python game projects can be smoke-tested by the backend.
