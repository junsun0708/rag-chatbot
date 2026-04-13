export default function ChatMessage({ role, content, sources }) {
  const isUser = role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${isUser ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-200'}`}>
        <p className="text-sm whitespace-pre-wrap">{content}</p>
        {sources && sources.length > 0 && (
          <div className="mt-2 pt-2 border-t border-slate-600">
            <p className="text-xs text-slate-400">참고: {sources.join(', ')}</p>
          </div>
        )}
      </div>
    </div>
  )
}
