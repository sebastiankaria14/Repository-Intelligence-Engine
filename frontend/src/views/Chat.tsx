import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, FileCode, GitBranch } from 'lucide-react';

import NoRepository from '../components/NoRepository';
import { useCurrentRepoId } from '../hooks/useRepository';
import { repositoryApi } from '../lib/api';
import type { ChatMessage, Citation } from '../types/api';

interface Message extends ChatMessage {
  citations?: Citation[];
}

const suggestedQuestions = [
  'Explain what this repository is about',
  'How do I run or setup this project?',
  'Why is the health score what it is?',
  'What architecture pattern does this codebase follow?',
  'Show me security findings and hardcoded secrets',
  'What are the main performance bottlenecks?',
  'List all discovered API endpoints',
  'Are there any circular dependency cycles?',
];

export default function Chat() {
  const repoId = useCurrentRepoId();
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content:
        "I'm your AI code intelligence assistant. I can explain what this repository is about, how to run it, analyze architecture, detect security vulnerabilities, inspect database models, and explain health metrics. What would you like to know?",
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading || !repoId) return;

    const userMsg: ChatMessage = { role: 'user', content: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);
    setError(null);

    try {
      const history = messages
        .filter((m) => m.role === 'user' || m.role === 'assistant')
        .map((m) => ({ role: m.role, content: m.content })) as ChatMessage[];

      const { data: res } = await repositoryApi.chat(repoId, {
        message: userMsg.content,
        history,
      });

      const assistantMsg: ChatMessage & { citations?: any } = {
        role: 'assistant',
        content: res.answer,
        citations: res.citations,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Failed to send message';
      setError(message);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Sorry, I encountered an error: ${message}.`,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuggestedClick = (question: string) => {
    setInput(question);
  };

  if (!repoId) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div>
          <h2 className="text-2xl font-bold gradient-text">AI Chat</h2>
          <p className="text-[var(--text-muted)] text-sm mt-1">
            Ask questions grounded in the knowledge graph
          </p>
        </div>
        <NoRepository />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-7rem)] animate-fade-in">
      <div className="mb-4">
        <h2 className="text-2xl font-bold gradient-text">AI Chat</h2>
        <p className="text-[var(--text-muted)] text-sm mt-1">
          Ask questions grounded in codebase AST, documentation, and architecture
        </p>
      </div>

      <div className="flex-1 flex flex-col lg:flex-row gap-4 min-h-0">
        {/* Chat Area */}
        <div className="flex-1 flex flex-col glass-card overflow-hidden">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}
              >
                {msg.role === 'assistant' && (
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ background: 'var(--gradient-primary)' }}
                  >
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                )}
                <div
                  className={`chat-message ${
                    msg.role === 'user' ? 'chat-message-user' : 'chat-message-assistant'
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap leading-relaxed font-sans">{msg.content}</p>
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-[var(--border-color)]">
                      <p className="text-xs font-semibold text-[var(--text-muted)] mb-2">
                        Grounded Knowledge Sources:
                      </p>
                      <div className="space-y-1.5">
                        {msg.citations.map((cite, ci) => (
                          <div
                            key={ci}
                            className="flex items-center gap-2 text-xs text-[var(--accent-cyan)] bg-[rgba(6,182,212,0.06)] p-2 rounded border border-[rgba(6,182,212,0.15)]"
                          >
                            {cite.type === 'file' ? (
                              <FileCode className="w-3.5 h-3.5 flex-shrink-0" />
                            ) : (
                              <GitBranch className="w-3.5 h-3.5 flex-shrink-0" />
                            )}
                            <span className="font-mono font-medium truncate">{cite.reference}</span>
                            {cite.snippet && (
                              <span className="text-[var(--text-muted)] truncate">
                                — {cite.snippet}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
                {msg.role === 'user' && (
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-[var(--accent-blue)]">
                    <User className="w-4 h-4 text-white" />
                  </div>
                )}
              </div>
            ))}
            {isLoading && (
              <div className="flex gap-3">
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center"
                  style={{ background: 'var(--gradient-primary)' }}
                >
                  <Bot className="w-4 h-4 text-white animate-pulse" />
                </div>
                <div className="chat-message chat-message-assistant">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-[var(--text-muted)]">Traversing knowledge graph & codebase documentation…</span>
                    <div className="flex gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent-blue)] animate-bounce" />
                      <span
                        className="w-1.5 h-1.5 rounded-full bg-[var(--accent-blue)] animate-bounce"
                        style={{ animationDelay: '0.15s' }}
                      />
                      <span
                        className="w-1.5 h-1.5 rounded-full bg-[var(--accent-blue)] animate-bounce"
                        style={{ animationDelay: '0.3s' }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-4 border-t border-[var(--border-color)] bg-[var(--bg-secondary)]">
            <div className="flex items-center gap-3">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Ask about project purpose, setup, architecture, security, performance..."
                className="flex-1 px-4 py-3 rounded-xl bg-[var(--bg-primary)] border border-[var(--border-color)] text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-blue)] transition-colors"
                disabled={isLoading}
              />
              <button
                onClick={handleSend}
                disabled={isLoading || !input.trim()}
                className="btn-primary py-3 px-5 rounded-xl text-sm"
                style={{ border: 'none' }}
              >
                <Send className="w-4 h-4" />
                <span>Send</span>
              </button>
            </div>
            {error && <p className="text-xs text-[var(--accent-rose)] mt-2">{error}</p>}
          </div>
        </div>

        {/* Suggested Questions Sidebar */}
        <div className="w-full lg:w-72 space-y-3 flex-shrink-0">
          <div className="glass-card p-4">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-4 h-4 text-[var(--accent-amber)]" />
              <h3 className="text-sm font-semibold">Suggested Questions</h3>
            </div>
            <div className="space-y-2">
              {suggestedQuestions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => handleSuggestedClick(q)}
                  className="w-full text-left p-3 rounded-lg text-xs text-[var(--text-secondary)] bg-white/[0.03] hover:bg-white/[0.08] hover:text-[var(--text-primary)] transition-all cursor-pointer shadow-sm border-none"
                  style={{ border: 'none' }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
