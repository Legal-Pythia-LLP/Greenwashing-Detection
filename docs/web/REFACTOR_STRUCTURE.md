web/src/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                 # 入口页面
│   ├── providers.tsx            # 全局Provider（React Query、Theme等）
│   └── components/
│       ├── ExplainableAI.tsx     # 主页面容器（拼接Upload + Chat）
│       ├── UploadSection.tsx     # 上传区域（调用features/upload里的逻辑）
│       └── ChatSection.tsx       # 聊天区域（调用features/chat里的逻辑）
│
├── components/
│   ├── header-context.tsx
│   ├── header-visibility.tsx
│   ├── header.tsx
│   └── ui/                       # 基础UI组件库（无业务逻辑）
│       ├── alert.tsx
│       ├── button.tsx
│       ├── card.tsx
│       ├── chart.tsx
│       ├── form.tsx
│       ├── input.tsx
│       ├── label.tsx
│       ├── piechart.tsx
│       ├── radarchart.tsx
│       ├── select.tsx
│       ├── sidebar.tsx
│       └── tabs.tsx
│
├── features/
│   ├── upload/
│   │   ├── hooks/
│   │   │   ├── useUploadSession.ts   # 上传文件 + 获取分析数据
│   │   │   └── useFileSelect.ts      # 文件选择逻辑（表单验证等）
│   │   └── components/
│   │       ├── FileInput.tsx         # 文件上传输入框
│   │       └── LanguageSelect.tsx    # 语言选择下拉框
│   │
│   ├── chat/
│   │   ├── hooks/
│   │   │   └── useChat.ts            # 聊天状态管理 + 流式消息处理
│   │   └── components/
│   │       ├── ChatWindow.tsx        # 聊天窗口布局（历史消息 + 输入框）
│   │       ├── ChatMessage.tsx       # 单条消息（含Markdown）
│   │       └── ChatInput.tsx         # 底部输入框
│
├── services/
│   ├── api.service.ts                # 封装uploadFile / sendChatMessage
│   └── mockData.ts
│
├── styles/
│   └── globals.css
│
└── utils/
    └── css.ts
