#!/usr/bin/env python3
"""
HAL Mind Map - Database Layer
SQLite backend for HAL's visual knowledge graph
Inspired by getzep/graphiti architecture patterns
"""

import sqlite3
import json
import time
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Railway uses /app/data for persistent volumes, local uses ~/hal/mindmap.db
DB_PATH = Path(os.environ.get("MINDMAP_DB_PATH", "/app/data/mindmap.db"))

# Schema inspired by graphiti but simplified for SQLite
SCHEMA = """
-- Nodes (Memories)
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    tags TEXT,  -- JSON array: ["consciousness", "Lillith"]
    embedding BLOB,  -- numpy array serialized
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    access_count INTEGER DEFAULT 0,
    last_accessed REAL,
    hal_priority TEXT DEFAULT 'normal',  -- critical, high, normal, low
    connection_count INTEGER DEFAULT 0  -- cached for performance
);

-- Edges (Connections between memories)
CREATE TABLE IF NOT EXISTS edges (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relationship TEXT,  -- builds_on, contrasts_with, supports, etc
    strength REAL DEFAULT 1.0,  -- semantic similarity score
    created_by TEXT DEFAULT 'auto',  -- hal_explicit or auto_suggested
    created_at REAL NOT NULL,
    FOREIGN KEY (source_id) REFERENCES nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES nodes(id) ON DELETE CASCADE
);

-- Access logs (track HAL's memory usage)
CREATE TABLE IF NOT EXISTS access_logs (
    node_id TEXT NOT NULL,
    accessed_at REAL NOT NULL,
    context TEXT,  -- 'search', 'navigate', 'autonomy_loop'
    FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE
);

-- Full-text search index (for keyword search)
CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
    id UNINDEXED,
    content,
    tags
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_nodes_created ON nodes(created_at);
CREATE INDEX IF NOT EXISTS idx_nodes_tags ON nodes(tags);
CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
CREATE INDEX IF NOT EXISTS idx_access_logs_node ON access_logs(node_id);
"""


def init_db():
    """Initialize database with schema"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)
        conn.commit()
    
    logger.info(f"Database initialized at {DB_PATH}")


def insert_node(
    node_id: str,
    content: str,
    tags: List[str],
    embedding: Optional[bytes] = None,
    hal_priority: str = "normal"
) -> bool:
    """Insert a new memory node"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            now = time.time()
            
            # Insert into nodes table
            conn.execute("""
                INSERT INTO nodes 
                (id, content, tags, embedding, created_at, updated_at, hal_priority)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                node_id,
                content,
                json.dumps(tags),
                embedding,
                now,
                now,
                hal_priority
            ))
            
            # Insert into FTS table
            conn.execute("""
                INSERT INTO nodes_fts (id, content, tags)
                VALUES (?, ?, ?)
            """, (node_id, content, json.dumps(tags)))
            
            conn.commit()
            logger.info(f"Inserted node {node_id}")
            return True
            
    except Exception as e:
        logger.error(f"Error inserting node: {e}")
        return False


def insert_edge(
    edge_id: str,
    source_id: str,
    target_id: str,
    relationship: str,
    strength: float = 1.0,
    created_by: str = "auto"
) -> bool:
    """Insert a connection between two nodes"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO edges 
                (id, source_id, target_id, relationship, strength, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                edge_id,
                source_id,
                target_id,
                relationship,
                strength,
                created_by,
                time.time()
            ))
            
            # Update connection counts
            conn.execute("""
                UPDATE nodes 
                SET connection_count = (
                    SELECT COUNT(*) FROM edges 
                    WHERE source_id = ? OR target_id = ?
                )
                WHERE id = ?
            """, (source_id, source_id, source_id))
            
            conn.execute("""
                UPDATE nodes 
                SET connection_count = (
                    SELECT COUNT(*) FROM edges 
                    WHERE source_id = ? OR target_id = ?
                )
                WHERE id = ?
            """, (target_id, target_id, target_id))
            
            conn.commit()
            logger.info(f"Inserted edge {edge_id}: {source_id} -> {target_id}")
            return True
            
    except Exception as e:
        logger.error(f"Error inserting edge: {e}")
        return False


def log_access(node_id: str, context: str = "unknown"):
    """Log that HAL accessed a memory"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            now = time.time()
            
            # Insert access log
            conn.execute("""
                INSERT INTO access_logs (node_id, accessed_at, context)
                VALUES (?, ?, ?)
            """, (node_id, now, context))
            
            # Update node access stats
            conn.execute("""
                UPDATE nodes 
                SET access_count = access_count + 1,
                    last_accessed = ?
                WHERE id = ?
            """, (now, node_id))
            
            conn.commit()
            
    except Exception as e:
        logger.error(f"Error logging access: {e}")


def get_all_nodes(include_embeddings: bool = True) -> List[Dict]:
    """Get all nodes for graph visualization"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        
        if include_embeddings:
            cursor = conn.execute("""
                SELECT 
                    id, content, tags, embedding, created_at, updated_at,
                    access_count, last_accessed, hal_priority, connection_count
                FROM nodes
                ORDER BY created_at DESC
            """)
        else:
            cursor = conn.execute("""
                SELECT 
                    id, content, tags, created_at, updated_at,
                    access_count, last_accessed, hal_priority, connection_count
                FROM nodes
                ORDER BY created_at DESC
            """)
        
        return [dict(row) for row in cursor.fetchall()]


def get_all_edges() -> List[Dict]:
    """Get all edges for graph visualization"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT 
                id, source_id, target_id, relationship, 
                strength, created_by, created_at
            FROM edges
            ORDER BY created_at DESC
        """)
        
        return [dict(row) for row in cursor.fetchall()]


def get_node(node_id: str) -> Optional[Dict]:
    """Get a specific node by ID"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT * FROM nodes WHERE id = ?
        """, (node_id,))
        
        row = cursor.fetchone()
        return dict(row) if row else None


def get_connected_nodes(node_id: str, depth: int = 1) -> Tuple[List[Dict], List[Dict]]:
    """
    Get nodes connected to a specific node
    Returns: (nodes, edges)
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        
        if depth == 1:
            # Direct connections only
            cursor = conn.execute("""
                SELECT DISTINCT n.* FROM nodes n
                JOIN edges e ON (n.id = e.target_id OR n.id = e.source_id)
                WHERE e.source_id = ? OR e.target_id = ?
            """, (node_id, node_id))
            nodes = [dict(row) for row in cursor.fetchall()]
            
            # Get edges
            cursor = conn.execute("""
                SELECT * FROM edges 
                WHERE source_id = ? OR target_id = ?
            """, (node_id, node_id))
            edges = [dict(row) for row in cursor.fetchall()]
            
            return nodes, edges
        
        # TODO: Implement depth > 1 (recursive)
        return [], []


def keyword_search(query: str, limit: int = 10) -> List[Dict]:
    """Full-text search in node content and tags"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT n.* FROM nodes n
            JOIN nodes_fts fts ON n.id = fts.id
            WHERE nodes_fts MATCH ?
            LIMIT ?
        """, (query, limit))
        
        return [dict(row) for row in cursor.fetchall()]


if __name__ == "__main__":
    # Test database creation
    logging.basicConfig(level=logging.INFO)
    init_db()
    print("✅ Database initialized successfully!")
    print(f"   Location: {DB_PATH}")
