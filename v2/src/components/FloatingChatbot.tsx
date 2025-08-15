import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { MessageCircle, X, Send, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export function FloatingChatbot() {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: t('chatbot.welcome')
    }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    try {
      // Enhanced chatbot logic with access to all reports
      const lastSessionId = localStorage.getItem('lastSessionId');
      
      const response = await fetch("/v1/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMessage,
          session_id: lastSessionId || "global_chat",
          context: "floating_chatbot"
        }),
      });

      if (!response.ok) {
        // Fallback with enhanced context awareness
        const assistantReply = generateSmartReply(userMessage);
        setMessages(prev => [...prev, { role: "assistant", content: assistantReply }]);
      } else {
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        let assistantContent = "";

        if (reader) {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            assistantContent += chunk;
          }
        }

        setMessages(prev => [...prev, { role: "assistant", content: assistantContent || t('common.error') }]);
      }
    } catch (error) {
      console.error("Chat error:", error);
      const smartReply = generateSmartReply(userMessage);
      setMessages(prev => [...prev, { role: "assistant", content: smartReply }]);
      toast({
        title: t('chatbot.connectionFailed'),
        description: t('chatbot.localReplyEnabled'),
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const generateSmartReply = (question: string) => {
    const q = question.toLowerCase();
    
    if (q.includes("公司") && q.includes("风险")) {
      return "根据已分析的公司报告，高风险公司主要存在以下问题：1) 模糊声明过多 2) 缺乏量化指标 3) 第三方验证不足。建议重点关注这些维度。";
    }
    
    if (q.includes("漂绿") || q.includes("greenwash")) {
      return "漂绿识别主要关注五个维度：模糊声明、缺乏指标、误导性术语、第三方验证不足、范围界定不清。每个维度都会给出0-100的评分，综合评估漂绿风险。";
    }
    
    if (q.includes("报告") && (q.includes("上传") || q.includes("分析"))) {
      return "您可以在上传页面提交ESG报告进行分析。系统会自动提取关键声明、进行风险评估，并生成详细的漂绿分析报告。";
    }
    
    if (q.includes("评分") || q.includes("分数")) {
      return "评分系统采用0-100分制，70分以上为高风险。评分基于AI分析结合外部验证结果，包括新闻验证和Wikirate数据库验证。";
    }
    
    if (q.includes("建议") || q.includes("recommendation")) {
      return "基于分析结果，建议：1) 增加具体量化指标 2) 提供第三方认证 3) 明确披露范围和边界 4) 避免使用模糊表述 5) 定期更新数据并保持透明度。";
    }
    
    return "我可以帮您解答ESG分析、漂绿识别、公司风险评估等相关问题。您也可以询问具体公司的分析结果或上传新报告进行分析。";
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      {/* Floating chat trigger */}
      <Button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-8 right-8 h-16 w-16 rounded-2xl shadow-large hover:shadow-large transition-all duration-300 z-40 bg-gradient-to-r from-primary to-accent hover:scale-110"
        size="icon"
      >
        {isOpen ? <X className="h-7 w-7" /> : <MessageCircle className="h-7 w-7" />}
      </Button>

      {/* Full-screen Chat Interface */}
      {isOpen && (
        <div className="fixed inset-0 z-50 glass-effect animate-fade-in">
          <div className="h-full max-w-6xl mx-auto flex flex-col">
            {/* Header */}
            <div className="modern-card m-6 mb-0 p-6 bg-gradient-to-r from-primary/5 to-accent/5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center shadow-medium">
                    <MessageCircle className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold gradient-text">
                      {t('chatbot.title')}
                    </h2>
                    <p className="text-muted-foreground">
                      {t('chatbot.explainableAi')}
                    </p>
                  </div>
                </div>
                <Button
                  onClick={() => setIsOpen(false)}
                  variant="ghost"
                  size="icon"
                  className="h-10 w-10 hover:bg-destructive/20 hover:text-destructive"
                >
                  <X className="h-5 w-5" />
                </Button>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 m-6 mt-4 modern-card p-6 overflow-hidden">
              <div className="h-full overflow-y-auto space-y-6 pr-2">
                {messages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[80%] p-4 rounded-2xl text-sm shadow-medium ${
                        msg.role === "user"
                          ? "bg-gradient-to-br from-primary to-primary/80 text-primary-foreground"
                          : "modern-card border-border/50"
                      }`}
                    >
                      <div className="whitespace-pre-wrap">{msg.content}</div>
                    </div>
                  </div>
                ))}
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="modern-card border-border/50 p-4 rounded-2xl text-sm flex items-center gap-3">
                      <div className="w-6 h-6 rounded-full bg-gradient-to-r from-primary to-accent animate-spin border-2 border-transparent border-t-primary"></div>
                      <span className="gradient-text font-medium">
                        {t('chatbot.analyzing')}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Input */}
            <div className="m-6 mt-0 modern-card p-6 bg-gradient-to-r from-card to-card/90">
              <div className="flex gap-4">
                <div className="flex-1 relative">
                  <Textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={t('chatbot.placeholder')}
                    className="min-h-[60px] max-h-[120px] resize-none bg-background/50 border-border/50 focus:border-primary/50 focus:ring-primary/20 text-base"
                    disabled={isLoading}
                  />
                  <div className="absolute bottom-3 right-3 text-xs text-muted-foreground">
                    {input.length}/500
                  </div>
                </div>
                <Button
                  onClick={handleSend}
                  disabled={!input.trim() || isLoading}
                  size="lg"
                  className="h-[60px] w-[60px] shrink-0 rounded-xl shadow-medium hover:shadow-large hover:scale-105 transition-all duration-200"
                >
                  <Send className="h-5 w-5" />
                </Button>
              </div>
              <div className="flex items-center justify-between mt-4 text-xs text-muted-foreground">
                <span>{t('chatbot.enterTip')}</span>
                <span>{t('chatbot.connectedToDb')}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}