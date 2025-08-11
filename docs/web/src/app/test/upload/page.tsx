'use client'
import {UploadForm} from '@lp/features/upload/components/UploadForm'

export default function TestUploadPage() {
  // 测试回调函数
  const handleUploadSuccess = (data: any) => {
    console.log('上传成功:', data)
    alert('文件分析完成')
  }

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      <h1 className="text-2xl font-bold mb-6">UploadForm 测试页面</h1>
      <div className="max-w-4xl mx-auto">
        <UploadForm 
          sessionId="test_session_123"
          onUploadSuccess={handleUploadSuccess}
        />
      </div>
    </div>
  )
}
