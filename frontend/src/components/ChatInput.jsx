import React, { useState } from 'react';
import { Send, Sparkles } from 'lucide-react';

const ChatInput = ({ onSendMessage, disabled }) => {
    const [input, setInput] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        if (input.trim() && !disabled) {
            onSendMessage(input);
            setInput('');
        }
    };

    return (
        <form onSubmit={handleSubmit} className="relative group">
            <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl blur opacity-20 group-focus-within:opacity-40 transition duration-1000 group-focus-within:duration-200"></div>
            <div className="relative flex items-center bg-[#1e293b]/50 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden focus-within:border-blue-500/50 transition-all">
                <div className="pl-4 text-blue-400">
                    <Sparkles size={20} />
                </div>
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="How can I help you today?"
                    className="flex-1 bg-transparent py-4 px-3 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none disabled:cursor-not-allowed"
                    disabled={disabled}
                />
                <button
                    type="submit"
                    disabled={!input.trim() || disabled}
                    className="p-3 mr-1 rounded-xl bg-blue-600/20 text-blue-400 hover:bg-blue-600/30 hover:text-blue-300 disabled:opacity-50 disabled:hover:bg-transparent transition-all"
                >
                    <Send size={20} />
                </button>
            </div>
        </form>
    );
};

export default ChatInput;
