import { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { MessageCircle, X, Send } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { APIService } from "@/services/api.service";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface FloatingChatbotProps {
  sessionId?: string;
}

export function FloatingChatbot({ sessionId }: FloatingChatbotProps) {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isInitializing, setIsInitializing] = useState(false);

  // Prevent body scroll when chat is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  // Load conversation history when opening chat
  useEffect(() => {
    if (!isOpen) return;

    const loadHistory = async () => {
      setIsInitializing(true);
      try {
        // Prefer using the provided sessionId, otherwise use lastSessionId from localStorage
        const targetSessionId = sessionId || localStorage.getItem("lastSessionId");
        if (!targetSessionId) {
          setMessages([
            {
              role: "assistant",
              content: t("chatbot.welcome"),
            },
          ]);
          return;
        }

        const history = await APIService.getConversation(targetSessionId);
        if (history?.messages?.length > 0) {
          setMessages(
            history.messages
              .filter(
                (msg: any) => msg.sender === "user" || msg.sender === "assistant"
              ) // 🚀 filter out system messages
              .map((msg: any) => ({
                role: msg.sender as "user" | "assistant",
                content: msg.content,
              }))
          );
        } else {
          setMessages([
            {
              role: "assistant",
              content: t("chatbot.welcome"),
            },
          ]);
        }
      } catch (error) {
        console.error("Failed to load conversation:", error);
        setMessages([
          {
            role: "assistant",
            content: t("chatbot.welcome"),
          },
        ]);
      } finally {
        setIsInitializing(false);
      }
    };

    loadHistory();
  }, [isOpen, t, sessionId]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  // Auto scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView();
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    try {
      // Prefer using the provided sessionId, otherwise use lastSessionId from localStorage
      const targetSessionId = sessionId || localStorage.getItem("lastSessionId");

      try {
        const response = await APIService.sendChatMessage(
          userMessage,
          targetSessionId || "global_chat"
        );
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: response || t("common.error") },
        ]);
      } catch (error) {
        const assistantReply = generateSmartReply(userMessage);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: assistantReply },
        ]);
      }
    } catch (error) {
      console.error("Chat error:", error);
      const smartReply = generateSmartReply(userMessage);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: smartReply },
      ]);
      toast({
        title: t("chatbot.connectionFailed"),
        description: t("chatbot.localReplyEnabled"),
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const generateSmartReply = (question: string) => {
    const q = question.toLowerCase();

    if (q.includes("company") && q.includes("risk")) {
      return "Based on analyzed company reports, high-risk companies mainly have the following issues: 1) Excessive vague statements 2) Lack of quantitative metrics 3) Insufficient third-party verification. Focus on these aspects.";
    }

    if (q.includes("greenwash") || q.includes("greenwashing")) {
      return "Greenwashing detection focuses on five dimensions: vague statements, lack of metrics, misleading terms, insufficient third-party verification, and unclear scope. Each dimension is scored 0-100 to assess greenwashing risk.";
    }

    if (q.includes("report") && (q.includes("upload") || q.includes("analyze"))) {
      return "You can submit ESG reports on the upload page for analysis. The system will automatically extract key statements, assess risks, and generate a detailed greenwashing analysis report.";
    }

    if (q.includes("score") || q.includes("rating")) {
      return "The scoring system uses a 0-100 scale, with scores above 70 considered high risk. Scores are based on AI analysis combined with external verification, including news and Wikirate database checks.";
    }

    if (q.includes("recommendation")) {
      return "Based on the analysis, recommendations include: 1) Increase specific quantitative targets 2) Provide third-party certifications 3) Clearly disclose scope and boundaries 4) Avoid vague statements 5) Regularly update data and maintain transparency.";
    }

    return "I can help answer questions related to ESG analysis, greenwashing detection, and company risk assessment. You can also inquire about specific company analysis results or upload new reports for analysis.";
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
                      {t("chatbot.title")}
                    </h2>
                    <p className="text-muted-foreground">
                      {t("chatbot.explainableAi")}
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
              <div
                className="h-full overflow-y-auto space-y-6 pr-2"
                onWheel={(e) => e.stopPropagation()}
              >
                {messages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex ${
                      msg.role === "user" ? "justify-end" : "justify-start"
                    }`}
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
                        {t("chatbot.analyzing")}
                      </span>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
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
                    placeholder={t("chatbot.placeholder")}
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
                <span>{t("chatbot.enterTip")}</span>
                <span>{t("chatbot.connectedToDb")}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
