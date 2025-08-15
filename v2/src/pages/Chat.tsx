import TopNav from "@/components/TopNav";
import Seo from "@/components/Seo";
import { useCallback, useMemo, useState } from "react";
import { ChatContainer } from "@/features/chat/components/ChatInterface/ChatContainer";
import type { Message } from "@/features/chat/components/ChatInterface/types";

const Chat = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentMessage, setCurrentMessage] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [sendingMessage, setSendingMessage] = useState(false);
  const [validating] = useState(false);
  const [showValidateButton] = useState(false);
  const [onclick, setOnclick] = useState(false);
  const [graphData, setGraphData] = useState<any>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isError] = useState(false);
  const [error] = useState<any>(null);

  const sessionId = useMemo(() => {
    try {
      return localStorage.getItem('lastSessionId') || "s_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
    } catch {
      return "s_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
    }
  }, []);

  const handleSend = useCallback(async () => {
    if (!input.trim() || sendingMessage) return;

    const userMsg: Message = { role: "user", content: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setSendingMessage(true);

    try {
      const res = await fetch("/v1/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg.content, session_id: sessionId }),
      });
      if (!res.ok || !res.body) {
        throw new Error("聊天接口不可用或缺少分析会话，请先上传报告");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      setCurrentMessage("");

      let acc = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        acc += chunk;
        setCurrentMessage((prev) => (prev ?? "") + chunk);
      }

      setMessages((prev) => [...prev, { role: "assistant", content: acc }]);
      setCurrentMessage(null);
    } catch (e: any) {
      const msg = e?.message || "发送失败";
      setMessages((prev) => [...prev, { role: "assistant", content: `错误：${msg}` }]);
    } finally {
      setSendingMessage(false);
    }
  }, [input, sendingMessage, sessionId]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  const handleValidate = useCallback(() => {
    // 预留校验行为
  }, []);

  return (
    <div className="min-h-screen [background-image:var(--gradient-soft)]">
      <Seo
        title="聊天与分析 | Explainable AI"
        description="上传文档并与 Explainable AI 对话，查看可解释的漂绿分析结果。"
        canonical={typeof window !== 'undefined' ? window.location.href : undefined}
        jsonLd={{
          "@context": "https://schema.org",
          "@type": "WebPage",
          name: "聊天与分析",
          description: "上传文档并与 Explainable AI 对话，查看可解释的漂绿分析结果。",
        }}
      />
      <TopNav />
      <main className="max-w-5xl mx-auto px-4 py-6">
        <header className="mb-4">
          <h1 className="text-2xl font-bold tracking-tight">聊天与分析</h1>
          <p className="text-muted-foreground mt-1">已接入 docs/web 聊天界面（示例数据）。</p>
        </header>
        <section>
          <div className="rounded-md border bg-background/60">
            <ChatContainer
              messages={messages}
              currentMessage={currentMessage}
              input={input}
              setInput={setInput}
              handleSend={handleSend}
              handleKeyDown={handleKeyDown}
              sendingMessage={sendingMessage}
              validating={validating}
              showValidateButton={showValidateButton}
              handleValidate={handleValidate}
              onclick={onclick}
              setOnclick={setOnclick}
              graphData={graphData}
              sidebarOpen={sidebarOpen}
              setSidebarOpen={setSidebarOpen}
              isError={isError}
              error={error}
            />
          </div>
        </section>
      </main>
    </div>
  );
};

export default Chat;

