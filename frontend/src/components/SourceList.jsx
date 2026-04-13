import { useState, useEffect } from 'react'
import { docAPI } from '../api/client'

export default function SourceList({ refreshKey }) {
  const [sources, setSources] = useState([])

  useEffect(() => {
    docAPI.sources().then(data => setSources(data.sources || [])).catch(() => {})
  }, [refreshKey])

  if (sources.length === 0) return null

  return (
    <div className="space-y-1">
      <p className="text-xs text-slate-400 font-semibold">📚 업로드된 문서</p>
      {sources.map((s, i) => (
        <p key={i} className="text-xs text-slate-500 truncate">• {s}</p>
      ))}
    </div>
  )
}
