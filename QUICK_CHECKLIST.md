# Deployment Checklist

Use this as you go through `RAILWAY_DEPLOY.md`. Check off each step.

## Pre-Deployment

- [ ] You have a GitHub account
- [ ] You have a Railway account (free tier is fine)
- [ ] You have your Letta API key (from https://console.letta.com)

## GitHub Setup (Step 1)

- [ ] Repo created on GitHub
- [ ] Code pushed to main branch
- [ ] Repo is connected to Railway (via "Deploy from GitHub")

## Backend Service (Step 3)

- [ ] Backend service is created in Railway
- [ ] Environment variables added:
  - [ ] `MINDMAP_DB_PATH=/app/data/mindmap.db`
  - [ ] `PORT=5002`
  - [ ] `HOST=0.0.0.0`
  - [ ] `LETTA_API_KEY=your-key-here`
- [ ] **VOLUME CREATED** (this is critical!):
  - [ ] Volume name: `mindmap-data`
  - [ ] Mount path: `/app/data`
  - [ ] Size: 1GB
- [ ] Backend shows "Healthy" in Railway dashboard

## Frontend Service (Step 4)

- [ ] Frontend service is created in Railway
- [ ] Environment variable added:
  - [ ] `REACT_APP_API_URL=https://mindmap-backend-XXXXX.railway.app`
    (Replace XXXXX with your actual backend URL)
- [ ] Frontend shows "Healthy" in Railway dashboard

## Post-Deployment

- [ ] Both services are running ("Healthy")
- [ ] You can access the frontend URL
- [ ] Frontend loads (you'll see an empty graph)
- [ ] Backend is reachable at `https://mindmap-backend-XXXXX.railway.app/health`

---

**If anything isn't "Healthy"**: Check the logs in Railway. They'll tell you what's wrong.

**If you get stuck on the volume**: This is the #1 issue. Make sure it's mounted at `/app/data` in the backend service.

You got this. 💚
