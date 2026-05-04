# Public Backend Hosting

OmniGameDev AI has two parts:

- The Vercel site is the public web IDE.
- The FastAPI backend is the agent that generates, edits, reviews, runs, stores, and exports projects.

For a public product, the backend must be reachable at a public HTTPS URL.

Because this backend can edit and execute generated project code, set `OMNIGAMEDEV_API_TOKEN` for any public backend. The web IDE has a `Backend access code` field in the left panel and sends that code with API requests.

MongoDB is the recommended persistence layer for the free Render setup. Render Free services use an ephemeral filesystem, so OmniGameDev AI stores generated project files and memory records in MongoDB, then restores them into `/tmp` when the backend starts.

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

Render is the simplest permanent path for this project because it can run the Docker backend for free while MongoDB Atlas stores generated projects and memory.

### Create MongoDB Atlas

1. Go to `https://www.mongodb.com/products/platform/atlas-database`.
2. Click `Try Free`.
3. Create or sign in to your MongoDB account.
4. Create an `M0 Free` cluster.
5. Click `Database Access`.
6. Click `Add New Database User`.
7. Create a username and password.
8. Click `Network Access`.
9. Click `Add IP Address`.
10. For quick setup, choose `Allow Access from Anywhere`.
11. Click `Database`.
12. Click `Connect`.
13. Choose `Drivers`.
14. Copy the connection string.
15. Replace `<password>` with the database user's password.

1. Go to `https://render.com`.
2. Click `Sign In`.
3. Click `New +`.
4. Click `Blueprint`.
5. Connect the GitHub repository that contains this folder.
6. Choose the repository.
7. Render should detect `render.yaml`.
8. Enter a value for `OMNIGAMEDEV_API_TOKEN` when Render asks for it.
9. Paste the MongoDB connection string into `MONGODB_URI`.
10. Keep `MONGODB_DB` as `omnigamedev`.
11. Click `Apply`.
12. Wait until the service finishes deploying.
13. Open the service page.
14. Copy the backend URL. It will look like `https://omnigamedev-ai-backend.onrender.com`.
15. Open the Vercel project dashboard.
16. Go to `Settings`.
17. Click `Environment Variables`.
18. Add `VITE_API_BASE`.
19. Paste the Render backend URL as the value.
20. Select `Production`.
21. Click `Save`.
22. Go to `Deployments`.
23. Click the three dots on the latest deployment.
24. Click `Redeploy`.
25. Open the public Vercel URL.
26. Paste the same `OMNIGAMEDEV_API_TOKEN` value into `Backend access code`.
27. Click `Use`.
28. The backend status should say `Agent backend online`.

The Docker image installs Python, Node.js, and the OmniGameDev dependencies so generated JavaScript and Python game projects can be smoke-tested by the backend. MongoDB stores project snapshots and memory; the local filesystem is only a runtime workspace.
