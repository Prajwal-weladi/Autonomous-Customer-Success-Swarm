import React from 'react';
import { MessageCircle, Plus, Trash2, Settings } from 'lucide-react';
import { GlassPanel } from './GlassUI';

const Sidebar = ({ conversations, activeIndex, onNewChat, onSelectChat, onDeleteChat }) => {
    return (
        <GlassPanel className="w-80 h-screen flex flex-col border-r border-white/10 shadow-2xl">
            <div className="p-6">
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent flex items-center gap-2">
                    <MessageCircle size={24} className="text-blue-400" />
                    Swarm Support
                </h1>
            </div>

            <div className="px-4 mb-6">
                <button
                    onClick={onNewChat}
                    className="w-full py-3 px-4 rounded-xl bg-blue-600/20 border border-blue-500/30 text-blue-100 flex items-center justify-center gap-2 hover:bg-blue-600/30 transition-all duration-300 group"
                >
                    <Plus size={20} className="group-hover:rotate-90 transition-transform duration-300" />
                    New Conversation
                </button>
            </div>

            <div className="flex-1 overflow-y-auto px-4 space-y-2">
                {conversations.map((chat, idx) => (
                    <div
                        key={chat.conversation_id}
                        onClick={() => onSelectChat(idx)}
                        className={`group relative p-4 rounded-xl cursor-pointer transition-all duration-300 ${activeIndex === idx
                                ? 'bg-white/10 border-white/20 shadow-lg'
                                : 'hover:bg-white/5 border-transparent'
                            } border`}
                    >
                        <div className="flex items-center justify-between">
                            <span className={`text-sm font-medium ${activeIndex === idx ? 'text-white' : 'text-slate-400'}`}>
                                {chat.title || `Chat ${idx + 1}`}
                            </span>
                            {conversations.length > 1 && (
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onDeleteChat(idx);
                                    }}
                                    className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 transition-opacity"
                                >
                                    <Trash2 size={14} />
                                </button>
                            )}
                        </div>
                        {chat.messages.length > 0 && (
                            <p className="text-xs text-slate-500 mt-1 truncate">
                                {chat.messages[chat.messages.length - 1].content}
                            </p>
                        )}
                    </div>
                ))}
            </div>

            <div className="p-4 border-t border-white/10">
                <div className="flex items-center gap-3 p-3 rounded-lg hover:bg-white/5 transition-colors cursor-pointer text-slate-400 hover:text-white">
                    <Settings size={20} />
                    <span className="text-sm font-medium">Settings</span>
                </div>
            </div>
        </GlassPanel>
    );
};

export default Sidebar;
