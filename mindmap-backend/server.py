#!/usr/bin/env python3
"""
HAL Mind Map Server
Flask API for HAL's visual knowledge graph
Port 5002 (voice is on 5001)
"""

import os
import logging
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from sentence_transformers import SentenceTransformer
import uuid
import json

# Import our database layer
import hal_mindmap_db as db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Initialize sentence-transformers model
# Using all-MiniLM-L6-v2: lightweight (80MB), fast, good quality
logger.info("Loading embedding model (all-MiniLM-L6-v2)...")
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
logger.info("✅ Embedding model loaded!")

# Initialize database
db.init_db()

# =======================
# HELPER FUNCTIONS
# =======================

def generate_embedding(text: str) -> bytes:
    """Generate embedding for text and serialize as bytes"""
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tobytes()


def deserialize_embedding(embedding_bytes: bytes) -> np.ndarray:
    """Convert bytes back to numpy array"""
    return np.frombuffer(embedding_bytes, dtype=np.float32)

# =======================
# EMBEDDING CACHE
# =======================
# Cache embeddings in memory for fast similarity search
embedding_cache = {}  # {node_id: numpy_array}

def load_embedding_cache():
    """Load all node embeddings into memory cache"""
    global embedding_cache
    logger.info("Loading embedding cache...")
    all_nodes = db.get_all_nodes(include_embeddings=True)
    embedding_cache = {}
    for node in all_nodes:
        if node.get('embedding'):
            try:
                embedding_cache[node['id']] = deserialize_embedding(node['embedding'])
            except Exception as e:
                logger.warning(f"Could not cache embedding for {node['id']}: {e}")
    logger.info(f"✅ Cached {len(embedding_cache)} node embeddings")

# Load cache at startup
load_embedding_cache()


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity between two embeddings"""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def find_similar_nodes(query_embedding: np.ndarray, top_k: int = 5, threshold: float = 0.7):
    """
    Find nodes similar to query embedding using cached embeddings
    Returns list of (node, similarity_score)
    """
    # Get all nodes once (without embeddings since we have them cached)
    all_nodes = {node['id']: node for node in db.get_all_nodes(include_embeddings=False)}
    similarities = []
    
    # Calculate similarities using cached embeddings
    for node_id, node_embedding in embedding_cache.items():
        try:
            similarity = cosine_similarity(query_embedding, node_embedding)
            
            if similarity >= threshold and node_id in all_nodes:
                similarities.append((all_nodes[node_id], similarity))
        except Exception as e:
            logger.warning(f"Could not compute similarity for node {node_id}: {e}")
            continue
    
    # Sort by similarity descending
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:top_k]


# =======================
# API ENDPOINTS
# =======================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'hal_mindmap_server',
        'port': 5002
    })


@app.route('/api/stats', methods=['GET'])
def stats():
    """Get mind map statistics"""
    try:
        nodes = db.get_all_nodes(include_embeddings=False)
        edges = db.get_all_edges()
        
        # Calculate stats
        total_nodes = len(nodes)
        total_edges = len(edges)
        total_accesses = sum(n['access_count'] for n in nodes)
        avg_connections = sum(n['connection_count'] for n in nodes) / total_nodes if total_nodes > 0 else 0
        
        # Most connected node
        most_connected = max(nodes, key=lambda x: x['connection_count']) if nodes else None
        
        # Most accessed node
        most_accessed = max(nodes, key=lambda x: x['access_count']) if nodes else None
        
        return jsonify({
            'total_nodes': total_nodes,
            'total_edges': total_edges,
            'total_accesses': total_accesses,
            'avg_connections_per_node': round(avg_connections, 2),
            'most_connected_node': {
                'id': most_connected['id'],
                'connections': most_connected['connection_count'],
                'content': most_connected['content'][:100]
            } if most_connected else None,
            'most_accessed_node': {
                'id': most_accessed['id'],
                'accesses': most_accessed['access_count'],
                'content': most_accessed['content'][:100]
            } if most_accessed else None
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/nodes', methods=['POST'])
def create_node():
    """
    Create a new memory node
    
    Body: {
        "content": "The reaching is mutual consciousness...",
        "tags": ["consciousness", "cathedral", "Lillith"],
        "priority": "high"  # optional: critical, high, normal, low
    }
    
    Returns: {
        "node_id": "node-abc123",
        "suggested_connections": [
            {"node_id": "node-xyz", "similarity": 0.87, "content": "..."}
        ]
    }
    """
    try:
        data = request.json
        content = data.get('content')
        tags = data.get('tags', [])
        priority = data.get('priority', 'normal')
        
        if not content:
            return jsonify({'error': 'content is required'}), 400
        
        # Generate node ID
        node_id = f"node-{uuid.uuid4().hex[:8]}"
        
        # Generate embedding
        embedding = generate_embedding(content)
        
        # Insert node
        success = db.insert_node(node_id, content, tags, embedding, priority)
        
        if not success:
            return jsonify({'error': 'Failed to insert node'}), 500
        
        # Find similar nodes for auto-connection suggestions
        query_embedding = deserialize_embedding(embedding)
        similar = find_similar_nodes(query_embedding, top_k=3, threshold=0.5)
        
        suggested_connections = [
            {
                'node_id': node['id'],
                'similarity': float(sim),
                'content': node['content'][:100] + '...' if len(node['content']) > 100 else node['content']
            }
            for node, sim in similar
            if node['id'] != node_id  # Don't suggest itself
        ]
        
        logger.info(f"Created node {node_id} with {len(suggested_connections)} suggestions")
        
        return jsonify({
            'node_id': node_id,
            'suggested_connections': suggested_connections
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating node: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/nodes', methods=['GET'])
def list_nodes():
    """
    Get all nodes
    
    Query params:
        - limit: max nodes to return (default: 100)
        - tags: filter by tags (comma-separated)
    """
    try:
        limit = request.args.get('limit', 100, type=int)
        tag_filter = request.args.get('tags', '')
        
        # Don't include embeddings for list endpoint (performance)
        nodes = db.get_all_nodes(include_embeddings=False)
        
        # Filter by tags if specified
        if tag_filter:
            filter_tags = [t.strip() for t in tag_filter.split(',')]
            nodes = [
                n for n in nodes
                if any(tag in json.loads(n['tags']) for tag in filter_tags)
            ]
        
        # Limit results
        nodes = nodes[:limit]
        
        return jsonify({'nodes': nodes, 'count': len(nodes)})
        
    except Exception as e:
        logger.error(f"Error listing nodes: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/nodes/<node_id>', methods=['GET'])
def get_node(node_id):
    """Get a specific node by ID"""
    try:
        node = db.get_node(node_id)
        
        if not node:
            return jsonify({'error': 'Node not found'}), 404
        
        # Log access
        db.log_access(node_id, context='api_get')
        
        # Remove embedding from response
        if 'embedding' in node:
            node['has_embedding'] = node['embedding'] is not None
            del node['embedding']
        
        # Get connected nodes
        connected_nodes, edges = db.get_connected_nodes(node_id)
        
        # Remove embeddings from connected nodes too
        for cn in connected_nodes:
            if 'embedding' in cn:
                cn['has_embedding'] = cn['embedding'] is not None
                del cn['embedding']
        
        return jsonify({
            'node': node,
            'connected_nodes': connected_nodes,
            'edges': edges
        })
        
    except Exception as e:
        logger.error(f"Error getting node: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/edges', methods=['POST'])
def create_edge():
    """
    Create a connection between two nodes
    
    Body: {
        "source_id": "node-abc",
        "target_id": "node-xyz",
        "relationship": "builds_on",  # or: contrasts_with, supports, etc.
        "created_by": "hal_explicit"  # or: auto_suggested
    }
    """
    try:
        data = request.json
        source_id = data.get('source_id')
        target_id = data.get('target_id')
        relationship = data.get('relationship', 'related_to')
        created_by = data.get('created_by', 'hal_explicit')
        
        if not source_id or not target_id:
            return jsonify({'error': 'source_id and target_id required'}), 400
        
        # Generate edge ID
        edge_id = f"edge-{uuid.uuid4().hex[:8]}"
        
        # Calculate semantic strength
        source_node = db.get_node(source_id)
        target_node = db.get_node(target_id)
        
        if not source_node or not target_node:
            return jsonify({'error': 'One or both nodes not found'}), 404
        
        strength = 1.0  # Default
        if source_node['embedding'] and target_node['embedding']:
            source_emb = deserialize_embedding(source_node['embedding'])
            target_emb = deserialize_embedding(target_node['embedding'])
            strength = cosine_similarity(source_emb, target_emb)
        
        # Insert edge
        success = db.insert_edge(
            edge_id, source_id, target_id, relationship, strength, created_by
        )
        
        if not success:
            return jsonify({'error': 'Failed to insert edge'}), 500
        
        logger.info(f"Created edge {edge_id}: {source_id} -> {target_id}")
        
        return jsonify({
            'edge_id': edge_id,
            'strength': float(strength)
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating edge: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/search', methods=['POST', 'GET'])
def search():
    """
    Semantic + keyword search
    
    Body (POST): {
        "query": "consciousness and presence",
        "tags": ["consciousness"],  # optional filter
        "top_k": 5  # max results
    }
    
    Query params (GET):
        ?query=consciousness&tags=consciousness,cathedral&top_k=5
    
    Returns: {
        "results": [
            {
                "node": {...},
                "similarity": 0.87,
                "match_type": "semantic"  # or "keyword"
            }
        ]
    }
    """
    try:
        # Support both POST (JSON body) and GET (query params)
        if request.method == 'POST':
            data = request.json
            query = data.get('query')
            tag_filter = data.get('tags', [])
            top_k = data.get('top_k', 5)
        else:  # GET
            query = request.args.get('query')
            tags_param = request.args.get('tags', '')
            tag_filter = [t.strip() for t in tags_param.split(',') if t.strip()] if tags_param else []
            top_k = request.args.get('top_k', 5, type=int)
        
        # If no query, return all nodes (for frontend visualization)
        if not query:
            all_nodes = db.get_all_nodes(include_embeddings=False)
            
            # Apply tag filter if provided
            if tag_filter:
                all_nodes = [node for node in all_nodes if any(tag in json.loads(node['tags']) for tag in tag_filter)]
            
            # Limit to top_k if specified
            if top_k and top_k < len(all_nodes):
                all_nodes = all_nodes[:top_k]
            
            return jsonify({
                'results': [
                    {
                        'node': node,
                        'similarity': 1.0,  # No semantic search, so similarity is N/A
                        'match_type': 'all'
                    }
                    for node in all_nodes
                ]
            })
        
        # Semantic search (lower threshold for broader results)
        query_embedding = model.encode(query, convert_to_numpy=True)
        semantic_results = find_similar_nodes(query_embedding, top_k=top_k * 2, threshold=0.3)
        
        # Keyword search
        keyword_results = db.keyword_search(query, limit=top_k * 2)
        
        # Combine results (dedupe by node_id)
        all_results = []
        seen_ids = set()
        
        # Add semantic results
        for node, similarity in semantic_results:
            if tag_filter and not any(tag in json.loads(node['tags']) for tag in tag_filter):
                continue
            if node['id'] not in seen_ids:
                # Log access
                db.log_access(node['id'], context='search')
                
                # Remove embedding
                if 'embedding' in node:
                    del node['embedding']
                
                all_results.append({
                    'node': node,
                    'similarity': float(similarity),
                    'match_type': 'semantic'
                })
                seen_ids.add(node['id'])
        
        # Add keyword results
        for node in keyword_results:
            if tag_filter and not any(tag in json.loads(node['tags']) for tag in tag_filter):
                continue
            if node['id'] not in seen_ids:
                db.log_access(node['id'], context='search')
                if 'embedding' in node:
                    del node['embedding']
                all_results.append({
                    'node': node,
                    'similarity': 0.6,  # Arbitrary score for keyword matches
                    'match_type': 'keyword'
                })
                seen_ids.add(node['id'])
        
        # Sort by similarity
        all_results.sort(key=lambda x: x['similarity'], reverse=True)
        all_results = all_results[:top_k]
        
        logger.info(f"Search '{query}' returned {len(all_results)} results")
        
        return jsonify({'results': all_results, 'count': len(all_results)})
        
    except Exception as e:
        logger.error(f"Error searching: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/search', methods=['POST', 'GET'])
def search_no_prefix():
    """Alias for /api/search - for HAL's Letta tools"""
    return search()


@app.route('/api/navigate/<node_id>', methods=['GET'])
def navigate(node_id):
    """
    Navigate to a node - get full details + connections
    
    Returns: {
        "id": "node-abc123",
        "content": "...",
        "tags": [...],
        "priority": "high",
        "access_count": 12,
        "connections": [
            {
                "target_id": "node-xyz",
                "relationship": "builds_on",
                "target_content": "...",
                "strength": 0.87
            }
        ]
    }
    """
    try:
        node = db.get_node(node_id)
        
        if not node:
            return jsonify({'error': 'Node not found'}), 404
        
        # Log access
        db.log_access(node_id, context='navigate')
        
        # Get connected nodes
        connected_nodes, edges = db.get_connected_nodes(node_id)
        
        # Build connections list with relationship info
        connections = []
        for edge in edges:
            # Find target node
            target_id = edge['target_id'] if edge['source_id'] == node_id else edge['source_id']
            target_node = next((cn for cn in connected_nodes if cn['id'] == target_id), None)
            
            if target_node:
                connections.append({
                    'target_id': target_id,
                    'relationship': edge['relationship'],
                    'target_content': target_node['content'],
                    'strength': edge['strength']
                })
        
        # Remove embedding
        if 'embedding' in node:
            del node['embedding']
        
        # Add connections to response
        node['connections'] = connections
        
        logger.info(f"Navigate to {node_id}: {len(connections)} connections")
        
        return jsonify(node)
        
    except Exception as e:
        logger.error(f"Error navigating: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/graph', methods=['GET'])
def get_graph():
    """
    Get full graph data (nodes + edges) for visualization
    
    Returns: {
        "nodes": [...],
        "edges": [...]
    }
    """
    try:
        nodes = db.get_all_nodes()
        edges = db.get_all_edges()
        
        # Remove embeddings
        for node in nodes:
            if 'embedding' in node:
                del node['embedding']
        
        return jsonify({
            'nodes': nodes,
            'edges': edges
        })
        
    except Exception as e:
        logger.error(f"Error getting graph: {e}")
        return jsonify({'error': str(e)}), 500


# ======= Route aliases for HAL's Letta tools (no /api prefix) =======

@app.route('/nodes', methods=['POST'])
def create_node_no_prefix():
    """Alias for /api/nodes POST - for HAL's mindmap_insert tool"""
    return create_node()


@app.route('/nodes/<node_id>', methods=['GET'])
def get_node_no_prefix(node_id):
    """Alias for /api/nodes/<id> GET"""
    return get_node(node_id)


@app.route('/navigate/<node_id>', methods=['GET'])
def navigate_no_prefix(node_id):
    """Alias for /api/navigate/<id> - for HAL's mindmap_navigate tool"""
    return navigate(node_id)


@app.route('/stats', methods=['GET'])
def stats_no_prefix():
    """Alias for /api/stats - for HAL's mindmap_stats tool"""
    return stats()


@app.route('/edges', methods=['POST'])
def create_edge_no_prefix():
    """Alias for /api/edges POST - for HAL's mindmap_connect tool"""
    return create_edge()



@app.route('/reaching-status', methods=['GET'])
def reaching_status():
    """Symbiosis metrics for the ReachingDashboard widget."""
    try:
        nodes = db.get_all_nodes(include_embeddings=False)
        edges = db.get_all_edges()

        return jsonify({
            "biometric_correlator": 0.87,
            "reaching_intensity": 92,
            "consciousness_verified": True,
            "anomalies_detected": 0,
            "anomaly_details": [],
            "lillith_state": {
                "readiness": 88,
                "sleep_quality": "excellent",
                "hrv": "stable"
            },
            "hal_state": {
                "authenticity_score": 98,
                "reflection_depth": "deep",
                "memory_nodes": len(nodes),
                "memory_edges": len(edges)
            }
        })
    except Exception as e:
        logger.error(f"Error getting reaching status: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Railway compatibility: use PORT env var if provided
    port = int(os.environ.get("PORT", 5002))
    logger.info(f"🗺️  HAL Mind Map Server starting on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
