'use client'
import {ChatInterface} from '@lp/features/chat/components/ChatInterface'

export default function TestChatPage() {
  // 测试数据 - 包含多种消息类型
  const testMessages = [
    {
      role: 'system', 
      content: '## 分析报告\n\n**公司名称**: 测试公司\n\n### 主要发现\n1. 环境指标: 达标 ✅\n2. 社会责任: 部分达标 ⚠️\n3. 公司治理: 未达标 ❌\n\n有问题可以随时问我'
    },
    {
      role: 'user',
      content: '为什么社会责任只是部分达标？'
    },
    {
      role: 'system',
      content: '社会责任部分得分较低主要是因为:\n- 员工福利政策不完善\n- 社区参与度不足\n- 供应链透明度不够'
    }
  ]

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      <h1 className="text-2xl font-bold mb-6">ChatInterface 测试页面</h1>
      <div className="max-w-4xl mx-auto">
        <ChatInterface 
          sessionId="test_session_123"
          initialMessages={testMessages}
          companyName="测试公司"
          onHeaderVisibility={() => {}}
        />
      </div>
    </div>
  )
}
