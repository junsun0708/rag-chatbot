import { useState } from 'react'
import { integrationAPI } from '../api/client'

export default function IntegrationPanel({ onSynced }) {
  const [activeTab, setActiveTab] = useState(null)

  return (
    <div className="space-y-2">
      <p className="text-xs text-slate-400 font-semibold">🔗 외부 연동</p>
      <div className="flex gap-1">
        <button
          onClick={() => setActiveTab(activeTab === 'confluence' ? null : 'confluence')}
          className={`text-xs px-2 py-1 rounded transition-colors ${activeTab === 'confluence' ? 'bg-blue-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'}`}
        >
          Confluence
        </button>
        <button
          onClick={() => setActiveTab(activeTab === 'notion' ? null : 'notion')}
          className={`text-xs px-2 py-1 rounded transition-colors ${activeTab === 'notion' ? 'bg-blue-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'}`}
        >
          Notion
        </button>
      </div>

      {activeTab === 'confluence' && <ConfluenceForm onSynced={onSynced} />}
      {activeTab === 'notion' && <NotionForm onSynced={onSynced} />}
    </div>
  )
}

function ConfluenceForm({ onSynced }) {
  const [form, setForm] = useState({ url: '', username: '', api_token: '', space_key: '' })
  const [syncing, setSyncing] = useState(false)
  const [message, setMessage] = useState('')

  const handleSync = async () => {
    if (!form.url || !form.username || !form.api_token || !form.space_key) {
      setMessage('모든 필드를 입력해주세요')
      return
    }
    setSyncing(true)
    setMessage('')
    try {
      const result = await integrationAPI.syncConfluence(form)
      setMessage(result.message)
      if (onSynced) onSynced()
    } catch (err) {
      setMessage(`실패: ${err.message}`)
    } finally {
      setSyncing(false)
    }
  }

  return (
    <div className="space-y-2 p-2 bg-slate-800 rounded-lg">
      <input
        placeholder="URL (https://xxx.atlassian.net)"
        value={form.url}
        onChange={e => setForm({ ...form, url: e.target.value })}
        className="w-full bg-slate-700 text-white text-xs rounded px-2 py-1 border border-slate-600 focus:border-blue-500 focus:outline-none"
      />
      <input
        placeholder="이메일"
        value={form.username}
        onChange={e => setForm({ ...form, username: e.target.value })}
        className="w-full bg-slate-700 text-white text-xs rounded px-2 py-1 border border-slate-600 focus:border-blue-500 focus:outline-none"
      />
      <input
        type="password"
        placeholder="API Token"
        value={form.api_token}
        onChange={e => setForm({ ...form, api_token: e.target.value })}
        className="w-full bg-slate-700 text-white text-xs rounded px-2 py-1 border border-slate-600 focus:border-blue-500 focus:outline-none"
      />
      <input
        placeholder="Space Key"
        value={form.space_key}
        onChange={e => setForm({ ...form, space_key: e.target.value })}
        className="w-full bg-slate-700 text-white text-xs rounded px-2 py-1 border border-slate-600 focus:border-blue-500 focus:outline-none"
      />
      <button
        onClick={handleSync}
        disabled={syncing}
        className="w-full text-xs px-2 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded disabled:opacity-50 transition-colors"
      >
        {syncing ? '동기화 중...' : '동기화'}
      </button>
      {message && <p className="text-[10px] text-emerald-400">{message}</p>}
    </div>
  )
}

function NotionForm({ onSynced }) {
  const [form, setForm] = useState({ api_key: '', database_id: '' })
  const [syncing, setSyncing] = useState(false)
  const [message, setMessage] = useState('')

  const handleSync = async () => {
    if (!form.api_key) {
      setMessage('API Key를 입력해주세요')
      return
    }
    setSyncing(true)
    setMessage('')
    try {
      const result = await integrationAPI.syncNotion(form)
      setMessage(result.message)
      if (onSynced) onSynced()
    } catch (err) {
      setMessage(`실패: ${err.message}`)
    } finally {
      setSyncing(false)
    }
  }

  return (
    <div className="space-y-2 p-2 bg-slate-800 rounded-lg">
      <input
        type="password"
        placeholder="Integration Token"
        value={form.api_key}
        onChange={e => setForm({ ...form, api_key: e.target.value })}
        className="w-full bg-slate-700 text-white text-xs rounded px-2 py-1 border border-slate-600 focus:border-blue-500 focus:outline-none"
      />
      <input
        placeholder="Database ID (선택)"
        value={form.database_id}
        onChange={e => setForm({ ...form, database_id: e.target.value })}
        className="w-full bg-slate-700 text-white text-xs rounded px-2 py-1 border border-slate-600 focus:border-blue-500 focus:outline-none"
      />
      <button
        onClick={handleSync}
        disabled={syncing}
        className="w-full text-xs px-2 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded disabled:opacity-50 transition-colors"
      >
        {syncing ? '동기화 중...' : '동기화'}
      </button>
      {message && <p className="text-[10px] text-emerald-400">{message}</p>}
    </div>
  )
}
