import { useState, useRef, useEffect } from "react";
import { MessageCircle, X, Send, Bot, User, Loader2, Sparkles } from "lucide-react";
import { apiClient } from "../services/api";
import { colors } from "../constants/theme";
import Markdown from "./Markdown";

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  agentsInvoked?: string[];
  processingTime?: number;
  timestamp: Date;
}

const SUGGESTED_QUERIES = [
  "What is the current health of my crops?",
  "Show me today's mandi prices for wheat",
  "Which government schemes am I eligible for?",
  "What is the weather forecast for my farm?",
  "When should I harvest my crops?",
];

export default function Chatbot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "system",
      content:
        "Namaste! I'm your KrishiMandal AI assistant. I can help you with crop health, mandi prices, government schemes, weather forecasts, and more. Ask me anything!",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (isOpen) inputRef.current?.focus();
  }, [isOpen]);

  const sendMessage = async (text?: string) => {
    const query = (text || input).trim();
    if (!query || isLoading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: query,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const farmerId = localStorage.getItem("farmer_id") || "F1001";
      const res = await apiClient.post<{
        final_response: string;
        agents_invoked: string[];
        processing_time_ms: number;
      }>("/query", {
        query,
        farmer_id: farmerId,
        language: "en",
      });

      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: res.final_response,
        agentsInvoked: res.agents_invoked,
        processingTime: res.processing_time_ms,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content:
            "Sorry, I couldn't process your request. Please try again later.",
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <>
      {/* Floating button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-24 md:bottom-6 right-6 z-[100] w-14 h-14 rounded-full shadow-lg flex items-center justify-center border-none cursor-pointer transition-transform hover:scale-110"
          style={{ backgroundColor: colors.primary }}
          aria-label="Open chat"
        >
          <MessageCircle size={26} color="#fff" />
        </button>
      )}

      {/* Chat window */}
      {isOpen && (
        <div className="fixed bottom-24 md:bottom-6 right-4 md:right-6 z-[100] w-[calc(100vw-2rem)] md:w-[420px] h-[70vh] max-h-[600px] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-gray-200">
          {/* Header */}
          <div
            className="flex items-center gap-3 px-4 py-3 text-white shrink-0"
            style={{ backgroundColor: colors.primary }}
          >
            <div className="w-9 h-9 rounded-full bg-white/20 flex items-center justify-center">
              <Bot size={20} />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-bold m-0 leading-tight">
                KrishiMandal AI
              </h3>
              <p className="text-[11px] opacity-80 m-0">
                Multi-Agent Farm Assistant
              </p>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="w-8 h-8 rounded-full bg-white/15 flex items-center justify-center border-none cursor-pointer hover:bg-white/25 transition-colors"
              aria-label="Close chat"
            >
              <X size={18} color="#fff" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-2 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.role !== "user" && (
                  <div
                    className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5"
                    style={{
                      backgroundColor: colors.primaryLight,
                      color: colors.primary,
                    }}
                  >
                    <Bot size={16} />
                  </div>
                )}
                <div
                  className={`max-w-[80%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "text-white rounded-br-sm"
                      : "bg-white text-gray-800 rounded-bl-sm shadow-sm border border-gray-100"
                  }`}
                  style={
                    msg.role === "user"
                      ? { backgroundColor: colors.primary }
                      : undefined
                  }
                >
                  {msg.role === "user" ? (
                    <p className="m-0 whitespace-pre-wrap">{msg.content}</p>
                  ) : (
                    <Markdown>{msg.content}</Markdown>
                  )}
                  {msg.agentsInvoked && msg.agentsInvoked.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-gray-100 flex flex-wrap gap-1">
                      <Sparkles
                        size={12}
                        className="mt-0.5"
                        style={{ color: colors.amber[500] }}
                      />
                      {msg.agentsInvoked.map((agent) => (
                        <span
                          key={agent}
                          className="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
                          style={{
                            backgroundColor: colors.primaryLight,
                            color: colors.primary,
                          }}
                        >
                          {agent}
                        </span>
                      ))}
                      {msg.processingTime && (
                        <span className="text-[10px] text-gray-400 ml-auto">
                          {(msg.processingTime / 1000).toFixed(1)}s
                        </span>
                      )}
                    </div>
                  )}
                </div>
                {msg.role === "user" && (
                  <div className="w-7 h-7 rounded-full bg-gray-200 flex items-center justify-center shrink-0 mt-0.5">
                    <User size={16} className="text-gray-600" />
                  </div>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="flex gap-2 items-center">
                <div
                  className="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
                  style={{
                    backgroundColor: colors.primaryLight,
                    color: colors.primary,
                  }}
                >
                  <Bot size={16} />
                </div>
                <div className="bg-white rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm border border-gray-100">
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <Loader2
                      size={14}
                      className="animate-spin"
                      style={{ color: colors.primary }}
                    />
                    <span>Agents are working on your query...</span>
                  </div>
                </div>
              </div>
            )}

            {/* Suggested queries - only show at start */}
            {messages.length === 1 && !isLoading && (
              <div className="space-y-1.5 pt-2">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide m-0">
                  Try asking
                </p>
                {SUGGESTED_QUERIES.map((q) => (
                  <button
                    key={q}
                    onClick={() => sendMessage(q)}
                    className="block w-full text-left text-sm px-3 py-2 rounded-lg bg-white border border-gray-200 text-gray-700 hover:border-[#2D5F2E] hover:bg-[#E8F5E9] cursor-pointer transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-3 bg-white border-t border-gray-200 shrink-0">
            <div className="flex items-center gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about crops, prices, schemes..."
                disabled={isLoading}
                className="flex-1 px-3.5 py-2.5 rounded-full border border-gray-300 text-sm outline-none focus:border-[#2D5F2E] focus:ring-1 focus:ring-[#2D5F2E] disabled:opacity-50 disabled:bg-gray-50"
              />
              <button
                onClick={() => sendMessage()}
                disabled={!input.trim() || isLoading}
                className="w-10 h-10 rounded-full flex items-center justify-center border-none cursor-pointer transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                style={{
                  backgroundColor:
                    input.trim() && !isLoading
                      ? colors.primary
                      : colors.gray[200],
                  color:
                    input.trim() && !isLoading ? "#fff" : colors.gray[400],
                }}
                aria-label="Send"
              >
                <Send size={18} />
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
