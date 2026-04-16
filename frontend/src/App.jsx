import { useState, useRef, useEffect } from 'react'
import { chatAPI } from './api/client'
import ChatMessage from './components/ChatMessage'
import FileUpload from './components/FileUpload'
import IntegrationPanel from './components/IntegrationPanel'
import WatcherPanel from './components/WatcherPanel'
import SourceList from './components/SourceList'
import './index.css'

export default function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    const q = input.trim()
    if (!q || loading) return

    setMessages(prev => [...prev, { role: 'user', content: q }])
    setInput('')
    setLoading(true)

    try {
      const data = await chatAPI.ask(q)
      setMessages(prev => [...prev, { role: 'assistant', content: data.answer, sources: data.sources }])
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `오류: ${err.message}` }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="h-screen flex">
      {/* 사이드바 */}
      <div className="w-64 bg-slate-900 border-r border-slate-700 p-4 flex flex-col gap-4">
        <h1 className="text-lg font-bold text-white">RAG Chatbot</h1>
        <p className="text-xs text-slate-400">문서를 업로드하고 질문하세요</p>
        <FileUpload onUploaded={() => setRefreshKey(k => k + 1)} />
        <WatcherPanel onChanged={() => setRefreshKey(k => k + 1)} />
        <IntegrationPanel onSynced={() => setRefreshKey(k => k + 1)} />
        <SourceList refreshKey={refreshKey} />
      </div>

      {/* 채팅 영역 */}
      <div className="flex-1 flex flex-col">
        {/* 메시지 목록 */}
        <div className="flex-1 overflow-y-auto p-6">
          {messages.length === 0 && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center text-slate-500">
                <p className="text-4xl mb-4">📄💬</p>
                <p className="text-lg">문서를 업로드하고 질문해보세요</p>
                <p className="text-sm mt-2">PDF, Word, Excel, 한/글, Confluence, Notion 등 지원</p>
              </div>
            </div>
          )}
          {messages.map((msg, i) => (
            <ChatMessage key={i} {...msg} />
          ))}
          {loading && (
            <div className="flex justify-start mb-4">
              <div className="bg-slate-800 rounded-2xl px-4 py-3 text-sm text-slate-400">
                답변 생성 중...
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* 입력 */}
        <div className="border-t border-slate-700 p-4">
          <div className="flex gap-2 max-w-4xl mx-auto">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="문서에 대해 질문하세요..."
              disabled={loading}
              className="flex-1 bg-slate-800 text-white rounded-xl px-4 py-3 text-sm border border-slate-600 focus:border-blue-500 focus:outline-none disabled:opacity-50"
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-semibold border-none disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              전송
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
