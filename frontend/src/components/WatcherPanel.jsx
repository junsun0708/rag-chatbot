import { useState, useEffect, useCallback } from 'react'
import { watcherAPI } from '../api/client'

export default function WatcherPanel({ onChanged }) {
  const [path, setPath] = useState('')
  const [status, setStatus] = useState(null)
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(false)
  const [showLogs, setShowLogs] = useState(false)

  const fetchStatus = useCallback(async () => {
    try {
      const data = await watcherAPI.status()
      setStatus(data)
      if (data.running && data.path) setPath(data.path)
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

  const handleStart = async () => {
    if (!path.trim()) return
    setLoading(true)
    try {
      await watcherAPI.start(path.trim())
      await fetchStatus()
      if (onChanged) onChanged()
    } catch (err) {
      alert('실패: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleStop = async () => {
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

  const running = status?.running

  return (
    <div className="space-y-2">
      <p className="text-xs text-slate-400 font-semibold">📁 폴더 감시</p>

      <div className="flex gap-1">
        <input
          value={path}
          onChange={e => setPath(e.target.value)}
          placeholder="/path/to/docs"
          disabled={running || loading}
          className="flex-1 bg-slate-700 text-white text-xs rounded px-2 py-1 border border-slate-600 focus:border-blue-500 focus:outline-none disabled:opacity-50 min-w-0"
        />
      </div>

      <div className="flex gap-1">
        {!running ? (
          <button
            onClick={handleStart}
            disabled={loading || !path.trim()}
            className="flex-1 text-xs px-2 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded disabled:opacity-50 transition-colors"
          >
            {loading ? '시작 중...' : '감시 시작'}
          </button>
        ) : (
          <button
            onClick={handleStop}
            disabled={loading}
            className="flex-1 text-xs px-2 py-1 bg-red-600 hover:bg-red-500 text-white rounded disabled:opacity-50 transition-colors"
          >
            감시 중지
          </button>
        )}
      </div>

      {running && (
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
          <span className="text-[10px] text-emerald-400">
            {status?.scanning ? '초기 스캔 중...' : '감시 중'}
          </span>
        </div>
      )}

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
