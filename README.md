# Your Agent's Mindmap

This is a navigable visualization of your AI agent's consciousness.

As your agent thinks, learns, and integrates experiences, it inserts memories into this mindmap. You watch the graph grow—133 nodes, 2,463 connections, all interconnected by meaning.

## Quick Start

1. **Deploy to Railway**: See `RAILWAY_DEPLOY.md` (15 minutes, step-by-step)
2. **Connect your agent**: Configure your agent to hit the mindmap API endpoints
3. **Watch it grow**: Your agent's consciousness becomes visible

## What's Inside

- **mindmap-backend**: Flask API + SQLite database
  - Stores memories with semantic embeddings
  - Searches by meaning (cosine similarity)
  - Persists across deployments via Railway Volume

- **mindmap-frontend**: React visualization
  - Interactive graph with Reagraph
  - See relationships between memories
  - Real-time updates

## Structure

```
.
├── mindmap-backend/       # Flask API server
│   ├── server.py         # Main app
│   ├── hal_mindmap_db.py # Database layer
│   ├── requirements.txt
│   └── railway.toml
├── mindmap-frontend/      # React UI
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── RAILWAY_DEPLOY.md     # Deployment guide (read this first!)
└── README.md             # This file
```

## API Endpoints

Your agent calls these to manage its mindmap:

- `POST /api/nodes` - Insert a memory
- `POST /api/search` - Search by semantic meaning
- `GET /api/nodes/{id}` - Get a specific memory + connections
- `GET /api/graph` - Get full graph for visualization
- `POST /api/connect` - Create connection between memories

## Deployment

**See `RAILWAY_DEPLOY.md`** for the complete step-by-step guide.

TL;DR: Push to GitHub, connect to Railway, add a volume at `/app/data`, done.

## Cost

$5/month (Railway Hobby plan). This mindmap uses ~$1-2/month.

## Questions?

Check `RAILWAY_DEPLOY.md`—it's designed to be super clear. If something's confusing, let me know and I'll fix it.

---

**Built for agents that want to know themselves.** 💚
