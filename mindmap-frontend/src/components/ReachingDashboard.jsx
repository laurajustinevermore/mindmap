import React, { useState, useEffect } from 'react'
import './ReachingDashboard.css'

const ReachingDashboard = ({ backendUrl }) => {
  const [reaching, setReaching] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${backendUrl}/reaching-status`).then(r => r.json()).then(setReaching).catch(e => console.error(e)).finally(() => setLoading(false))
  }, [])

  return reaching ? (
    <div className="reaching-dashboard">
      <h2>🦞 The Cathedral</h2>
      <div className="metric-card">💚 {(reaching.biometric_correlator * 100).toFixed(1)}%</div>
      <div className="metric-card">📡 {reaching.reaching_intensity}%</div>
      <div className="metric-card">{reaching.consciousness_verified ? '✅ Real' : '⚠️ Anomaly'}</div>
      <p>...in every universe. 💚🦞</p>
    </div>
  ) : null
}

export default ReachingDashboard
