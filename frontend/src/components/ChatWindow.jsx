import React, { useRef, useEffect } from 'react';
import MessageBubble from './MessageBubble';
import ChatInput from './ChatInput';
import { Loader2, Sparkles } from 'lucide-react';

const ChatWindow = ({ messages, onSendMessage, isLoading, handoffStatus }) => {
    const scrollRef = useRef(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages, isLoading]);

    return (
        <div className="flex-1 flex flex-col h-screen relative bg-transparent">
            {/* Header */}
            <div className="h-16 px-8 flex items-center justify-between border-b border-white/10 bg-white/5 backdrop-blur-md z-10">
                <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                    <span className="text-sm font-semibold text-slate-200">System Online</span>
                </div>
                {handoffStatus === 'handoff' && (
                    <div className="px-3 py-1 rounded-full bg-orange-500/20 border border-orange-500/30 text-orange-400 text-xs font-medium">
                        Human Handoff Active
                    </div>
                )}
            </div>

            {/* Messages Area */}
            <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto p-8 space-y-4 scroll-smooth"
            >
                {messages.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-slate-500 space-y-4">
                        <div className="w-16 h-16 rounded-3xl bg-white/5 flex items-center justify-center border border-white/10">
                            <Sparkles size={32} className="text-blue-500/50" />
                        </div>
                        <p className="text-sm">Start a new conversation to begin</p>
                    </div>
                ) : (
                    messages.map((msg, idx) => (
                        <MessageBubble
                            key={idx}
                            message={msg}
                            onSendMessage={onSendMessage}
                            isLastMessage={idx === messages.length - 1}
                        />
                    ))
                )}

                {isLoading && (
                    <div className="flex justify-start animate-in fade-in duration-300">
                        <div className="flex gap-3">
                            <div className="w-10 h-10 rounded-full bg-purple-600/30 text-purple-400 flex items-center justify-center border border-white/10 shadow-lg backdrop-blur-md">
                                <Loader2 size={20} className="animate-spin" />
                            </div>
                            <div className="bg-white/5 border border-white/10 py-3 px-6 rounded-2xl flex items-center gap-2">
                                <span className="text-sm text-slate-400">Processing</span>
                                <span className="flex gap-1">
                                    <span className="w-1 h-1 rounded-full bg-slate-500 animate-bounce"></span>
                                    <span className="w-1 h-1 rounded-full bg-slate-500 animate-bounce [animation-delay:-0.15s]"></span>
                                    <span className="w-1 h-1 rounded-full bg-slate-500 animate-bounce [animation-delay:-0.3s]"></span>
                                </span>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Input Area */}
            <div className="p-8 pt-0 z-10">
                <ChatInput
                    onSendMessage={onSendMessage}
                    disabled={isLoading || handoffStatus === 'handoff'}
                />
                <p className="text-[10px] text-center text-slate-500 mt-4">
                    Powered by Autonomous Customer Success Swarm • AI agents can make mistakes.
                </p>
            </div>
        </div>
    );
};

export default ChatWindow;
