import { useState, useEffect, useCallback } from 'react'
import { watcherAPI } from '../api/client'

export default function WatcherPanel({ onChanged }) {
  const [input, setInput] = useState('')
  const [status, setStatus] = useState(null)
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(false)
  const [showLogs, setShowLogs] = useState(false)

  const fetchStatus = useCallback(async () => {
    try {
      const data = await watcherAPI.status()
      setStatus(data)
      setLogs(data.recent_logs || [])
    } catch (_err) {
      // 서버 미응답 시 무시
    }
  }, [])

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 5000)
    return () => clearInterval(interval)
  }, [fetchStatus])

  const handleAdd = async () => {
    if (!input.trim()) return
    setLoading(true)
    try {
      await watcherAPI.add(input.trim())
      setInput('')
      await fetchStatus()
      if (onChanged) onChanged()
    } catch (err) {
      alert('실패: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleRemove = async (path) => {
    setLoading(true)
    try {
      await watcherAPI.remove(path)
      await fetchStatus()
    } catch (_err) {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  const handleStopAll = async () => {
    setLoading(true)
    try {
      await watcherAPI.stop()
      await fetchStatus()
    } catch (_err) {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  const paths = status?.paths || []
  const scanning = status?.scanning || []

  return (
    <div className="space-y-2">
      <p className="text-xs text-slate-400 font-semibold">📁 폴더 감시</p>

      {/* 폴더 추가 입력 */}
      <div className="flex gap-1">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleAdd()}
          placeholder="/path/to/docs"
          disabled={loading}
          className="flex-1 bg-slate-700 text-white text-xs rounded px-2 py-1 border border-slate-600 focus:border-blue-500 focus:outline-none disabled:opacity-50 min-w-0"
        />
        <button
          onClick={handleAdd}
          disabled={loading || !input.trim()}
          className="text-xs px-2 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded disabled:opacity-50 transition-colors"
        >
          +
        </button>
      </div>

      {/* 감시 중인 폴더 목록 */}
      {paths.length > 0 && (
        <div className="space-y-1">
          {paths.map((p) => (
            <div key={p} className="flex items-center gap-1 bg-slate-800 rounded px-2 py-1">
              <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse flex-shrink-0" />
              <span className="text-[10px] text-slate-300 truncate flex-1" title={p}>
                {p}
              </span>
              {scanning.includes(p) && (
                <span className="text-[10px] text-yellow-400 flex-shrink-0">스캔중</span>
              )}
              <button
                onClick={() => handleRemove(p)}
                disabled={loading}
                className="text-[10px] text-red-400 hover:text-red-300 flex-shrink-0 disabled:opacity-50"
              >
                ✕
              </button>
            </div>
          ))}
          <button
            onClick={handleStopAll}
            disabled={loading}
            className="w-full text-[10px] px-2 py-0.5 text-slate-500 hover:text-red-400 transition-colors disabled:opacity-50"
          >
            전체 중지
          </button>
        </div>
      )}

      {/* 로그 */}
      {logs.length > 0 && (
        <div>
          <button
            onClick={() => setShowLogs(!showLogs)}
            className="text-[10px] text-slate-500 hover:text-slate-300 transition-colors"
          >
            {showLogs ? '▼ 로그 숨기기' : '▶ 최근 로그'}
          </button>
          {showLogs && (
            <div className="mt-1 max-h-32 overflow-y-auto space-y-0.5">
              {[...logs].reverse().map((log, i) => (
                <p key={i} className={'text-[10px] ' + (log.error ? 'text-red-400' : 'text-slate-500')}>
                  {log.time?.slice(11)} {log.action} — {log.target}
                  {log.chunks > 0 ? ' (' + log.chunks + ')' : ''}
                  {log.error ? ' ⚠ ' + log.error : ''}
                </p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
