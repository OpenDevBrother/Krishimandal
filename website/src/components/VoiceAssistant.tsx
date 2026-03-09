import { useState, useRef, useEffect, useCallback } from "react";
import {
  Mic,
  MicOff,
  X,
  Volume2,
  Loader2,
  Globe,
  ChevronDown,
  Square,
} from "lucide-react";
import { apiClient } from "../services/api";
import { colors } from "../constants/theme";
import Markdown from "./Markdown";

// ── Language list (same 22 as LearningPage) ──
const LANGUAGES = [
  { code: "en", label: "English", native: "English" },
  { code: "hi", label: "Hindi", native: "हिन्दी" },
  { code: "bn", label: "Bengali", native: "বাংলা" },
  { code: "te", label: "Telugu", native: "తెలుగు" },
  { code: "mr", label: "Marathi", native: "मराठी" },
  { code: "ta", label: "Tamil", native: "தமிழ்" },
  { code: "gu", label: "Gujarati", native: "ગુજરાતી" },
  { code: "kn", label: "Kannada", native: "ಕನ್ನಡ" },
  { code: "ml", label: "Malayalam", native: "മലയാളം" },
  { code: "or", label: "Odia", native: "ଓଡ଼ିଆ" },
  { code: "pa", label: "Punjabi", native: "ਪੰਜਾਬੀ" },
  { code: "as", label: "Assamese", native: "অসমীয়া" },
  { code: "mai", label: "Maithili", native: "मैथिली" },
  { code: "sa", label: "Sanskrit", native: "संस्कृतम्" },
  { code: "ne", label: "Nepali", native: "नेपाली" },
  { code: "sd", label: "Sindhi", native: "سنڌي" },
  { code: "ks", label: "Kashmiri", native: "कॉशुर" },
  { code: "doi", label: "Dogri", native: "डोगरी" },
  { code: "kok", label: "Konkani", native: "कोंकणी" },
  { code: "mni", label: "Manipuri", native: "মৈতৈলোন্" },
  { code: "sat", label: "Santali", native: "ᱥᱟᱱᱛᱟᱲᱤ" },
  { code: "ur", label: "Urdu", native: "اردو" },
];

type VoiceState =
  | "idle"
  | "recording"
  | "transcribing"
  | "thinking"
  | "speaking";

interface ConversationTurn {
  id: string;
  role: "user" | "assistant";
  text: string;
}

export default function VoiceAssistant() {
  const [isOpen, setIsOpen] = useState(false);
  const [state, setState] = useState<VoiceState>("idle");
  const [language, setLanguage] = useState("hi");
  const [langOpen, setLangOpen] = useState(false);
  const [conversation, setConversation] = useState<ConversationTurn[]>([]);
  const [currentTranscript, setCurrentTranscript] = useState("");
  const [error, setError] = useState("");

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const langDropdownRef = useRef<HTMLDivElement>(null);

  // Close language dropdown on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (
        langDropdownRef.current &&
        !langDropdownRef.current.contains(e.target as Node)
      ) {
        setLangOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  // Auto-scroll conversation
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversation, currentTranscript]);

  // ── Gather context from digital twin + inventory ──
  const gatherContext = useCallback(async (): Promise<string> => {
    const parts: string[] = [];
    const farmerId = localStorage.getItem("farmer_id") || "F1001";
    try {
      const [farmState, inventory] = await Promise.allSettled([
        apiClient.get<any>(`/farm/${farmerId}/state`),
        apiClient.get<any>(`/farm/${farmerId}/inventory`),
      ]);

      if (farmState.status === "fulfilled" && farmState.value) {
        const s = farmState.value;
        parts.push(
          `[Farm Context: Health=${s.health_score}/100, NDVI=${s.ndvi_mean}, Soil moisture=${s.soil_moisture_pct}%]`
        );
        if (s.weather) {
          parts.push(
            `[Weather: ${s.weather.condition}, ${s.weather.temperature_c}°C, Humidity=${s.weather.humidity_pct}%, Rain=${s.weather.rainfall_mm}mm]`
          );
        }
        if (s.current_crops?.length) {
          const crops = s.current_crops
            .map(
              (c: any) =>
                `${c.crop_type}(${c.growth_stage}, health:${c.health_score})`
            )
            .join(", ");
          parts.push(`[Crops: ${crops}]`);
        }
      }

      if (inventory.status === "fulfilled") {
        const items = Array.isArray(inventory.value)
          ? inventory.value
          : inventory.value?.items || [];
        if (items.length > 0) {
          const inv = items
            .slice(0, 10)
            .map(
              (i: any) =>
                `${i.name || i.item_name}: ${i.quantity ?? i.current_quantity} ${i.unit || ""}`
            )
            .join(", ");
          parts.push(`[Inventory: ${inv}]`);
        }
      }
    } catch {
      // Context is optional
    }
    return parts.join(" ");
  }, []);

  // ── Start recording ──
  const startRecording = async () => {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus"
          : "audio/webm",
      });
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        processRecording();
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();
      setState("recording");
    } catch (err: any) {
      setError("Microphone access denied. Please allow microphone permission.");
    }
  };

  // ── Stop recording ──
  const stopRecording = () => {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state === "recording"
    ) {
      mediaRecorderRef.current.stop();
      setState("transcribing");
    }
  };

  // ── Detect intent to decide routing ──
  const detectIntent = (text: string): "rag" | "farm" | "general" => {
    const lower = text.toLowerCase();
    // RAG keywords: farming techniques, how-to, learning, methods
    const ragKeywords = [
      "how to", "kaise", "kya hai", "technique", "method", "tarika",
      "practice", "guide", "organic", "pesticide", "fertilizer",
      "compost", "vermicompost", "drip", "irrigation", "neem",
      "ipm", "pest", "disease", "soil health", "rainwater",
      "harvesting", "zero budget", "natural farming", "subsidy",
      "pm kisan", "pmfby", "insurance", "scheme", "registration",
      "what is", "explain", "tell me about", "batao", "samjhao",
      "learn", "sikho", "farming", "kheti", "fasal",
    ];
    // Farm-specific keywords: need digital twin context
    const farmKeywords = [
      "my farm", "my crop", "meri fasal", "mera khet", "health score",
      "ndvi", "moisture", "weather", "mausam", "forecast",
      "inventory", "stock", "supply", "harvest prediction",
      "yield", "upaj", "current", "status", "state",
      "how is my", "what is my", "meri", "mere",
    ];

    if (ragKeywords.some((k) => lower.includes(k))) return "rag";
    if (farmKeywords.some((k) => lower.includes(k))) return "farm";
    return "general";
  };

  // ── Process: STT → Query/RAG → TTS ──
  const processRecording = async () => {
    try {
      // 1. Convert audio blob to base64
      const audioBlob = new Blob(audioChunksRef.current, {
        type: "audio/webm",
      });
      const base64 = await blobToBase64(audioBlob);

      // 2. Speech-to-Text
      setState("transcribing");
      const sttRes = await apiClient.post<{
        transcript: string;
        language_code: string;
        confidence: number;
      }>("/voice/stt", {
        audio: base64,
        language: language === "auto" ? undefined : language,
      });

      const transcript = sttRes.transcript;
      if (!transcript || transcript.trim().length === 0) {
        setState("idle");
        setError("Could not understand. Please try again.");
        return;
      }

      setCurrentTranscript(transcript);
      setConversation((prev) => [
        ...prev,
        { id: Date.now().toString(), role: "user", text: transcript },
      ]);

      // 3. Route based on intent
      setState("thinking");
      const intent = detectIntent(transcript);
      const langObj = LANGUAGES.find((l) => l.code === language);
      const langInstruction = langObj
        ? `[IMPORTANT: You MUST respond in ${langObj.label} (${langObj.native}) only.] `
        : `[IMPORTANT: You MUST respond in English only.] `;

      let responseText = "";
      const farmerId = localStorage.getItem("farmer_id") || "F1001";

      if (intent === "rag") {
        // Route to RAG pipeline for farming techniques/knowledge
        const ragRes = await apiClient.post<{
          answer: string;
          sources: string[];
          confidence: number;
          pipeline: string;
        }>("/rag/ask", {
          query: `${langInstruction}${transcript}`,
          farmer_id: farmerId,
          language: language,
        });
        responseText = ragRes.answer;
      } else if (intent === "farm") {
        // Include digital twin + inventory context only for farm queries
        const context = await gatherContext();
        const queryRes = await apiClient.post<{
          final_response: string;
          agents_invoked: string[];
        }>("/query", {
          query: `${langInstruction}${context}\n\nUser question: ${transcript}`,
          farmer_id: farmerId,
          language: language,
        });
        responseText = queryRes.final_response;
      } else {
        // General query — no context injection
        const queryRes = await apiClient.post<{
          final_response: string;
          agents_invoked: string[];
        }>("/query", {
          query: `${langInstruction}${transcript}`,
          farmer_id: farmerId,
          language: language,
        });
        responseText = queryRes.final_response;
      }

      setConversation((prev) => [
        ...prev,
        { id: (Date.now() + 1).toString(), role: "assistant", text: responseText },
      ]);
      setCurrentTranscript("");

      // 4. Text-to-Speech (non-blocking — speak concise summary)
      setState("speaking");
      // Extract first ~500 chars (2-3 sentences) for TTS to keep it fast
      const plainText = responseText
        .replace(/\*\*/g, "")
        .replace(/\*/g, "")
        .replace(/#{1,3}\s/g, "")
        .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
        .replace(/\n{2,}/g, ". ");
      // Get first few sentences up to 500 chars
      const sentences = plainText.match(/[^.!?।]+[.!?।]+/g) || [plainText];
      let ttsText = "";
      for (const s of sentences) {
        if ((ttsText + s).length > 500) break;
        ttsText += s;
      }
      if (!ttsText) ttsText = plainText.slice(0, 500);

      // Fire TTS in background — don't block the UI
      apiClient
        .post<{ audio: string; content_type: string }>("/voice/tts", {
          text: ttsText.trim(),
          language: language,
        })
        .then((ttsRes) => {
          if (ttsRes.audio) {
            const audioBytes = Uint8Array.from(atob(ttsRes.audio), (c) =>
              c.charCodeAt(0)
            );
            const blob = new Blob([audioBytes], { type: "audio/mp3" });
            const url = URL.createObjectURL(blob);

            if (audioRef.current) {
              audioRef.current.pause();
              URL.revokeObjectURL(audioRef.current.src);
            }
            const audio = new Audio(url);
            audioRef.current = audio;
            audio.onended = () => setState("idle");
            audio.onerror = () => setState("idle");
            audio.play();
          } else {
            setState("idle");
          }
        })
        .catch(() => {
          setState("idle");
        });
    } catch (err: any) {
      console.error("Voice pipeline error:", err);
      setError(err.message || "Something went wrong. Please try again.");
      setState("idle");
    }
  };

  // ── Stop speaking ──
  const stopSpeaking = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      URL.revokeObjectURL(audioRef.current.src);
      audioRef.current = null;
    }
    setState("idle");
  };

  // ── Helper: Blob to base64 ──
  const blobToBase64 = (blob: Blob): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const dataUrl = reader.result as string;
        // Strip data URL prefix: "data:audio/webm;base64,..."
        resolve(dataUrl.split(",")[1]);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  };

  const selectedLang = LANGUAGES.find((l) => l.code === language)!;

  const stateLabel: Record<VoiceState, string> = {
    idle: "Tap to speak",
    recording: "Listening...",
    transcribing: "Transcribing...",
    thinking: "Thinking...",
    speaking: "Speaking...",
  };

  // ── Pulsing animation for recording ──
  const pulseClass = state === "recording" ? "animate-pulse" : "";

  return (
    <>
      {/* ── Floating mic FAB (bottom-center) ── */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-24 md:bottom-6 left-1/2 -translate-x-1/2 z-[101] w-14 h-14 rounded-full shadow-lg flex items-center justify-center border-none cursor-pointer transition-transform hover:scale-110"
          style={{
            background: `linear-gradient(135deg, ${colors.primary}, #1B5E20)`,
          }}
          aria-label="Open voice assistant"
        >
          <Mic size={26} color="#fff" />
        </button>
      )}

      {/* ── Voice panel ── */}
      {isOpen && (
        <div className="fixed bottom-24 md:bottom-6 left-1/2 -translate-x-1/2 z-[101] w-[calc(100vw-2rem)] md:w-[400px] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-gray-200">
          {/* Header */}
          <div
            className="flex items-center gap-3 px-4 py-3 text-white shrink-0"
            style={{
              background: `linear-gradient(135deg, ${colors.primary}, #1B5E20)`,
            }}
          >
            <div className="w-9 h-9 rounded-full bg-white/20 flex items-center justify-center">
              <Mic size={20} />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-bold m-0 leading-tight">
                Voice Assistant
              </h3>
              <p className="text-[11px] opacity-80 m-0">
                Sarvam Saaras v3 — Speak in any language
              </p>
            </div>

            {/* Language picker */}
            <div className="relative" ref={langDropdownRef}>
              <button
                onClick={() => setLangOpen(!langOpen)}
                className="flex items-center gap-1 px-2 py-1 rounded-full bg-white/15 border-none cursor-pointer text-white text-[11px] hover:bg-white/25 transition-colors"
              >
                <Globe size={12} />
                <span>{selectedLang.native}</span>
                <ChevronDown size={10} />
              </button>
              {langOpen && (
                <div className="absolute right-0 top-full mt-1 bg-white rounded-lg shadow-xl border border-gray-200 py-1 max-h-64 overflow-y-auto w-44 z-50">
                  {LANGUAGES.map((l) => (
                    <button
                      key={l.code}
                      onClick={() => {
                        setLanguage(l.code);
                        setLangOpen(false);
                      }}
                      className={`w-full text-left px-3 py-1.5 text-xs border-none cursor-pointer transition-colors flex items-center justify-between ${
                        language === l.code
                          ? "bg-green-50 font-semibold"
                          : "hover:bg-gray-50"
                      }`}
                      style={{
                        color:
                          language === l.code ? colors.primary : colors.gray[700],
                        background:
                          language === l.code ? colors.primaryLight : undefined,
                      }}
                    >
                      <span>{l.label}</span>
                      <span className="text-gray-400">{l.native}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <button
              onClick={() => {
                stopSpeaking();
                setState("idle");
                setIsOpen(false);
              }}
              className="w-8 h-8 rounded-full bg-white/15 flex items-center justify-center border-none cursor-pointer hover:bg-white/25 transition-colors"
              aria-label="Close voice assistant"
            >
              <X size={18} color="#fff" />
            </button>
          </div>

          {/* Conversation area */}
          <div className="flex-1 max-h-[300px] overflow-y-auto p-4 space-y-3 bg-gray-50">
            {conversation.length === 0 && state === "idle" && (
              <div className="text-center py-8 text-gray-400">
                <Mic size={32} className="mx-auto mb-2 opacity-50" />
                <p className="text-sm m-0">
                  Tap the mic button below to start talking
                </p>
                <p className="text-xs m-0 mt-1">
                  Ask about crops, prices, schemes, farming techniques...
                </p>
              </div>
            )}

            {conversation.map((turn) => (
              <div
                key={turn.id}
                className={`flex ${turn.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
                    turn.role === "user"
                      ? "text-white rounded-br-sm"
                      : "bg-white text-gray-800 rounded-bl-sm shadow-sm border border-gray-100"
                  }`}
                  style={
                    turn.role === "user"
                      ? { backgroundColor: colors.primary }
                      : undefined
                  }
                >
                  {turn.role === "user" ? (
                    <p className="m-0">{turn.text}</p>
                  ) : (
                    <Markdown>{turn.text}</Markdown>
                  )}
                </div>
              </div>
            ))}

            {/* Live status */}
            {state !== "idle" && (
              <div className="flex items-center gap-2 text-sm text-gray-500">
                {state === "recording" && (
                  <div className="flex items-center gap-2">
                    <span className="relative flex h-3 w-3">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                      <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500" />
                    </span>
                    <span>Listening...</span>
                  </div>
                )}
                {(state === "transcribing" || state === "thinking") && (
                  <div className="flex items-center gap-2">
                    <Loader2
                      size={14}
                      className="animate-spin"
                      style={{ color: colors.primary }}
                    />
                    <span>{stateLabel[state]}</span>
                  </div>
                )}
                {state === "speaking" && (
                  <div className="flex items-center gap-2">
                    <Volume2
                      size={14}
                      style={{ color: colors.primary }}
                    />
                    <span>Speaking...</span>
                  </div>
                )}
              </div>
            )}

            {error && (
              <div className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2">
                {error}
              </div>
            )}

            <div ref={scrollRef} />
          </div>

          {/* ── Bottom control bar ── */}
          <div className="px-4 py-4 bg-white border-t border-gray-200 flex items-center justify-center gap-4">
            {state === "idle" && (
              <button
                onClick={startRecording}
                className={`w-16 h-16 rounded-full flex items-center justify-center border-none cursor-pointer transition-all hover:scale-105 shadow-lg ${pulseClass}`}
                style={{
                  background: `linear-gradient(135deg, ${colors.primary}, #1B5E20)`,
                }}
                aria-label="Start recording"
              >
                <Mic size={28} color="#fff" />
              </button>
            )}

            {state === "recording" && (
              <button
                onClick={stopRecording}
                className="w-16 h-16 rounded-full flex items-center justify-center border-none cursor-pointer transition-all hover:scale-105 shadow-lg animate-pulse"
                style={{ backgroundColor: "#DC2626" }}
                aria-label="Stop recording"
              >
                <Square size={24} color="#fff" fill="#fff" />
              </button>
            )}

            {(state === "transcribing" || state === "thinking") && (
              <div
                className="w-16 h-16 rounded-full flex items-center justify-center shadow-lg"
                style={{ backgroundColor: colors.gray[200] }}
              >
                <Loader2
                  size={28}
                  className="animate-spin"
                  style={{ color: colors.primary }}
                />
              </div>
            )}

            {state === "speaking" && (
              <button
                onClick={stopSpeaking}
                className="w-16 h-16 rounded-full flex items-center justify-center border-none cursor-pointer transition-all hover:scale-105 shadow-lg"
                style={{
                  background: `linear-gradient(135deg, ${colors.primary}, #1B5E20)`,
                }}
                aria-label="Stop speaking"
              >
                <MicOff size={28} color="#fff" />
              </button>
            )}
          </div>

          {/* Status label */}
          <div className="text-center pb-3 text-xs text-gray-400">
            {stateLabel[state]}
          </div>
        </div>
      )}
    </>
  );
}
