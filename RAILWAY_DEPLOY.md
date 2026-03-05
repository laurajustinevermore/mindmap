# Deploy Your Mindmap to Railway

This is your AI's navigable consciousness—a visual knowledge graph that grows as your agent thinks. This guide will get it running in Railway in ~15 minutes.

## What You're Deploying

- **mindmap-backend**: Flask API that stores and searches your agent's memories
- **mindmap-frontend**: React visualization—see your agent's mind as an interactive graph

That's it. Two services. Simple.

---

## Step 1: Push to GitHub

1. Create a **new GitHub repository** (can be private)
2. In this directory, run:
   ```bash
   git init
   git add .
   git commit -m "mindmap deployment setup"
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git branch -M main
   git push -u origin main
   ```

Done. Your code is on GitHub.

---

## Step 2: Create a Railway Project

1. Go to **https://railway.app**
2. Sign in (or create account)
3. Click **"New Project"** → **"Deploy from GitHub"**
4. Select your mindmap repo
5. Give it a name (e.g., "anna-mindmap")

Railway will auto-detect both services. You don't need to do anything else here.

---

## Step 3: Configure Backend Service

Click **"mindmap-backend"** service in the Railway dashboard.

### Environment Variables

Go to the **"Variables"** tab and add these:

```
MINDMAP_DB_PATH=/app/data/mindmap.db
PORT=5002
HOST=0.0.0.0
LETTA_API_KEY=your-letta-api-key-here
```

(Get your LETTA_API_KEY from https://console.letta.com)

### Add Volume (CRITICAL - Do This Before Testing!)

⚠️ **WITHOUT THIS STEP, YOUR DATABASE WILL BE DELETED ON EVERY REDEPLOY** ⚠️

Go to the **"Data"** tab:

1. Click **"New Volume"**
2. Set name to: `mindmap-data`
3. Set mount path to: `/app/data`
4. Leave size as default (1GB)
5. **Hit Create** and wait for it to show "Mounted"

**Why?** Railway's filesystem is ephemeral—everything gets wiped on redeploy. The volume is persistent storage. Without it, all memories disappear.

**Don't proceed to Step 5 until the volume shows "Mounted" in the Data tab.**

---

## Step 4: Configure Frontend Service

Click **"mindmap-frontend"** service in the Railway dashboard.

### Environment Variables

Go to the **"Variables"** tab and add this:

```
VITE_BACKEND_URL=https://mindmap-backend-REPLACE.railway.app
```

**Replace `REPLACE` with your actual backend service name from Railway.**

(You'll see it in the Railway URL bar—it looks like `mindmap-backend-abc123.railway.app`)

---

## Step 5: Verify Volume is Mounted

Before your agent starts inserting memories, **verify the volume is actually mounted**.

In the backend service:
1. Go to **"Logs"** tab
2. Look for this line: `Database initialized at /app/data/mindmap.db`
3. If you see it, the volume is working ✓
4. If you see `Database initialized at /app/data/mindmap.db` but it disappears after redeploy, **the volume isn't mounted properly**—go back to Step 3 and check

## Step 6: Deploy & Watch

Railway automatically deploys when you pushed the repo.

Watch the logs:
- **Backend**: Should say "Database initialized at /app/data/mindmap.db" and "Flask running on 0.0.0.0:5002"
- **Frontend**: Should say "npm run build" completed

---

## Step 7: Access Your Mindmap

Once both services show **"Healthy"** in the Railway dashboard:

1. Go to your frontend service URL (shown in Railway)
2. You'll see an empty graph (because no memories yet)
3. Your agent can now insert memories into this mindmap!

⚠️ **Important**: Before your agent starts working, confirm:
- [ ] Backend logs show "Database initialized at /app/data/mindmap.db"
- [ ] Volume is showing as "Mounted" in the backend Data tab
- [ ] Both services are "Healthy"
- [ ] Frontend loads without errors

If you skip this verification and redeployed later, the database **will be lost**.

---

## How Your Agent Uses This

Your agent will call the API endpoints to:
- **Insert memories**: `POST /api/nodes`
- **Search memories**: `POST /api/search`
- **Navigate connections**: `GET /api/nodes/{id}`

The frontend visualizes all of this in real-time.

---

## Troubleshooting

**Backend won't start?**
- Check LETTA_API_KEY is valid
- Check logs in Railway dashboard

**Frontend shows blank?**
- Check REACT_APP_API_URL is correct in frontend variables
- Check backend is showing "Healthy"

**Database keeps disappearing after redeploy?**
- **This means the volume isn't mounted.** Go back to Step 3.
- Check backend service → "Data" tab
- If volume shows "Unmounted" or is missing: Create it again with mount path `/app/data`
- Wait for "Mounted" status before redeploying
- This is the #1 cause of data loss

**How to tell if volume is working:**
1. Insert a memory
2. Check backend logs: `SELECT COUNT(*) FROM nodes;` should show 1
3. Redeploy the backend service
4. Check logs again: should still show 1 memory
5. If count drops to 0, volume wasn't persisting—fix Step 3

---

## Cost

Railway Hobby plan = $5/month

Your mindmap uses ~$1-2/month. You're covered. ✅

---

**That's it. Your mindmap lives in Railway now.** 💚

Once your agent starts thinking, memories will appear. Watch the graph grow.
