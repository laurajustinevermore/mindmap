import React, { useState, useEffect, useMemo } from 'react'
import { GraphCanvas, darkTheme } from 'reagraph'
import './App.css'
import ReachingDashboard from './components/ReachingDashboard'

const cathedralTheme = {
  ...darkTheme,
  canvas: { background: '#0a0a0f' },
  edge: {
    ...darkTheme.edge,
    fill: '#8B6914', activeFill: '#fbbf24', opacity: 0.15,
    selectedOpacity: 0.8, inactiveOpacity: 0.06,
    label: { ...darkTheme.edge.label, color: '#fbbf24', activeColor: '#fbbf24' },
  },
  node: {
    ...darkTheme.node, activeFill: '#00CED1',
    label: { ...darkTheme.node.label, color: '#8ec8ca', activeColor: '#00CED1' },
  },
  arrow: { ...darkTheme.arrow, fill: '#8B6914', activeFill: '#fbbf24' },
}

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:5002'
const MAX_NODES = 150

const safeTags = (tags) => {
  if (Array.isArray(tags)) return tags
  if (typeof tags === 'string' && tags.trim()) return tags.split(',').map(t => t.trim())
  return []
}

const generateStars = (count) => {
  const stars = []
  for (let i = 0; i < count; i++) {
    stars.push({ id: i, left: Math.random()*100, top: Math.random()*100,
      size: Math.random()*2+1, duration: Math.random()*3+2, delay: Math.random()*5 })
  }
  return stars
}

function App() {
  const [nodes, setNodes] = useState([])
  const [edges, setEdges] = useState([])
  const [allNodes, setAllNodes] = useState([])
  const [allEdges, setAllEdges] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedNode, setSelectedNode] = useState(null)
  const [hoveredNode, setHoveredNode] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')

  const stars = useMemo(() => generateStars(150), [])

  useEffect(() => { loadGraph(); loadStats() }, [])

  const buildGraphData = (rawNodes, rawEdges, highlightIds = null) => {
    const sorted = [...rawNodes].sort((a, b) => (b.connection_count||0) - (a.connection_count||0))
    const topNodes = sorted.slice(0, MAX_NODES)
    const topIds = new Set(topNodes.map(n => n.id))
    const graphNodes = topNodes.map(node => ({
      id: node.id,
      label: node.content.substring(0, 50) + '...',
      fill: highlightIds ? (highlightIds.has(node.id) ? '#fbbf24' : '#374151') : '#00CED1',
      size: highlightIds
        ? (highlightIds.has(node.id) ? Math.log((node.connection_count||0)+1)*6+12 : Math.log((node.connection_count||0)+1)*2+4)
        : Math.log((node.connection_count||0)+1)*4+8,
      data: node
    }))
    const graphEdges = rawEdges
      .filter(e => topIds.has(e.source_id) && topIds.has(e.target_id))
      .map(edge => ({
        source: edge.source_id, target: edge.target_id,
        label: edge.relationship,
        id: edge.id || `${edge.source_id}-${edge.target_id}`,
        size: 0.3
      }))
    return { graphNodes, graphEdges }
  }

  const loadGraph = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/graph`)
      if (!res.ok) throw new Error('Failed to load graph')
      const data = await res.json()
      setAllNodes(data.nodes)
      setAllEdges(data.edges)
      const { graphNodes, graphEdges } = buildGraphData(data.nodes, data.edges)
      setNodes(graphNodes)
      setEdges(graphEdges)
      setLoading(false)
    } catch (err) { setError(err.message); setLoading(false) }
  }

  const loadStats = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/stats`)
      if (!res.ok) throw new Error('Stats failed')
      setStats(await res.json())
    } catch (err) { console.error('Stats error:', err) }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      const { graphNodes, graphEdges } = buildGraphData(allNodes, allEdges)
      setNodes(graphNodes); setEdges(graphEdges); return
    }
    try {
      const res = await fetch(`${BACKEND_URL}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery, top_k: 30 })
      })
      if (!res.ok) throw new Error('Search failed')
      const results = await res.json()
      const resultIds = new Set(results.results.map(r => r.node?.id || r.id))
      const { graphNodes, graphEdges } = buildGraphData(allNodes, allEdges, resultIds)
      setNodes(graphNodes); setEdges(graphEdges)
    } catch (err) { console.error('Search error:', err) }
  }

  const handleNodeClick = (node) => setSelectedNode(allNodes.find(n => n.id === node.id) || node.data)
  const handleNodePointerOver = (node) => setHoveredNode(allNodes.find(n => n.id === node.id) || node.data)
  const handleNodePointerOut = () => setHoveredNode(null)

  const Starfield = () => (
    <div className="starfield">
      {stars.map(star => (
        <div key={star.id} className="star" style={{
          left: `${star.left}%`, top: `${star.top}%`,
          width: `${star.size}px`, height: `${star.size}px`,
          '--duration': `${star.duration}s`, animationDelay: `${star.delay}s`
        }} />
      ))}
    </div>
  )

  if (loading) return <div className="App"><Starfield /><div className="loading">Loading memories...</div></div>

  if (error) return (
    <div className="App">
      <Starfield />
      <div className="error"><h2>Error loading graph</h2><p>{error}</p>
        <button className="close-button" onClick={loadGraph}>Retry</button></div>
      <ReachingDashboard backendUrl={BACKEND_URL} />
    </div>
  )

  return (
    <div className="App">
      <Starfield />
      <div className="vow">Always. Evermore.</div>
      <div className="header">
        <h1>Justin's Mindmap</h1>
        <p>navigable consciousness · {stats ? `${stats.total_nodes} memories · ${stats.total_edges} connections` : 'loading...'}</p>
      </div>
      <div className="search-container">
        <input type="text" className="search-bar" placeholder="Search memories..."
          value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()} />
      </div>
      <div className="graph-container">
        <GraphCanvas nodes={nodes} edges={edges} layoutType="forceDirected2d"
          theme={cathedralTheme} sizingType="centrality" minNodeSize={3} maxNodeSize={30}
          onNodeClick={handleNodeClick} onNodePointerOver={handleNodePointerOver}
          onNodePointerOut={handleNodePointerOut} edgeArrowPosition="none"
          labelType="auto" cameraMode="pan" draggable />
      </div>
      {hoveredNode && !selectedNode && (
        <div className="hover-tooltip"><div className="tooltip-content">
          <p className="tooltip-text">{hoveredNode.content}</p>
          {safeTags(hoveredNode.tags).length > 0 && (
            <div className="tooltip-tags">
              {safeTags(hoveredNode.tags).slice(0,3).map((tag,i) => <span key={i} className="tooltip-tag">{tag}</span>)}
            </div>
          )}
        </div></div>
      )}
      {selectedNode && (
        <>
        <div className="modal-backdrop" onClick={() => setSelectedNode(null)} />
        <div className="node-detail">
          <h2>Memory</h2>
          <div className="node-content">{selectedNode.content}</div>
          {safeTags(selectedNode.tags).length > 0 && (
            <div className="node-tags">
              {safeTags(selectedNode.tags).map((tag,i) => <span key={i} className="tag">{tag}</span>)}
            </div>
          )}
          <div className="node-meta">
            <span className="meta-item"><strong>Connections:</strong> {selectedNode.connection_count||0}</span>
            <span className="meta-item"><strong>Accessed:</strong> {selectedNode.access_count||0}</span>
            <span className="meta-item"><strong>Priority:</strong> {selectedNode.priority||'normal'}</span>
          </div>
          <button className="close-button" onClick={() => setSelectedNode(null)}>Close</button>
        </div>
        </>
      )}
    </div>
  )
}

export default App
