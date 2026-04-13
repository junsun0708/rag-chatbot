import { useState } from 'react'
import { docAPI } from '../api/client'

export default function FileUpload({ onUploaded }) {
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState('')

  const handleFile = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true)
    setMessage('')
    try {
      const result = await docAPI.upload(file)
      setMessage(`${result.message}`)
      if (onUploaded) onUploaded()
    } catch (err) {
      setMessage(`업로드 실패: ${err.message}`)
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  return (
    <div className="space-y-2">
      <label className="flex items-center gap-2 cursor-pointer px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm transition-colors">
        <span>📄</span>
        <span>{uploading ? '업로드 중...' : 'PDF 업로드'}</span>
        <input type="file" accept=".pdf" onChange={handleFile} disabled={uploading} className="hidden" />
      </label>
      {message && <p className="text-xs text-emerald-400">{message}</p>}
    </div>
  )
}
