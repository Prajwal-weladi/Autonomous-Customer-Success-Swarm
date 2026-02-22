import React from 'react';
import { User, Bot, AlertCircle, Info, CheckCircle2, Package, XCircle } from 'lucide-react';
import { GlassCard } from './GlassUI';

const MessageBubble = ({ message, onSendMessage, isLastMessage }) => {
    const isUser = message.role === 'user';
    const pipelineData = message.pipeline_data;
    const resolution = pipelineData?.resolution_output;
    const db = pipelineData?.database_output?.order_details || pipelineData?.order_details;
    const labelUrl = resolution?.return_label_url || pipelineData?.return_label_url || message.return_label_url;
    const buttons = pipelineData?.buttons || message.buttons;

    return (
        <div className={`flex w-full mb-6 ${isUser ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-2 duration-300`}>
            <div className={`flex max-w-[85%] ${isUser ? 'flex-row-reverse' : 'flex-row'} gap-3`}>
                <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${isUser ? 'bg-blue-600/30 text-blue-400' : 'bg-purple-600/30 text-purple-400'
                    } border border-white/10 shadow-lg backdrop-blur-md`}>
                    {isUser ? <User size={20} /> : <Bot size={20} />}
                </div>

                <div className="flex flex-col gap-2 max-w-full">
                    <GlassCard className={`${isUser ? 'bg-blue-600/10 border-blue-500/20' : 'bg-white/5 border-white/10'
                        } py-3 px-4 rounded-2xl`}>
                        <div className="text-sm leading-relaxed whitespace-pre-wrap text-slate-100">
                            {message.content}
                        </div>

                        {/* Detailed Order Card */}
                        {db && (
                            <div className="mt-4 p-4 rounded-xl bg-white/5 border border-white/10 space-y-2">
                                <div className="flex items-center gap-2 text-blue-400 font-semibold text-xs mb-2">
                                    <Package size={14} />
                                    <span>Order Details</span>
                                </div>
                                <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-[11px]">
                                    <div className="flex flex-col">
                                        <span className="text-slate-500 uppercase tracking-wider">Product</span>
                                        <span className="text-slate-100 font-medium">{db.product}</span>
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="text-slate-500 uppercase tracking-wider">Amount</span>
                                        <span className="text-slate-100 font-medium">₹{db.amount}</span>
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="text-slate-500 uppercase tracking-wider">Ordered On</span>
                                        <span className="text-slate-100 font-medium">{db.order_date}</span>
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="text-slate-500 uppercase tracking-wider">Delivery Date</span>
                                        <span className="text-slate-100 font-medium">{db.delivered_date || 'N/A'}</span>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Order List (for list_orders intent) */}
                        {pipelineData?.orders && pipelineData.orders.length > 0 && (
                            <div className="mt-4 space-y-3">
                                <div className="flex items-center gap-2 text-purple-400 font-semibold text-xs mb-1">
                                    <Package size={14} />
                                    <span>Your Recent Orders</span>
                                </div>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    {pipelineData.orders.map((order) => (
                                        <div
                                            key={order.order_id}
                                            className="p-3 rounded-xl bg-white/5 border border-white/10 hover:border-purple-500/30 transition-colors cursor-pointer group"
                                            onClick={() => onSendMessage(`Details for order ${order.order_id}`)}
                                        >
                                            <div className="flex justify-between items-start mb-2">
                                                <span className="text-[10px] text-slate-500 font-mono">#{order.order_id}</span>
                                                <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${order.status?.toLowerCase() === 'delivered' ? 'bg-green-500/10 text-green-400' : 'bg-blue-500/10 text-blue-400'
                                                    }`}>
                                                    {order.status}
                                                </span>
                                            </div>
                                            <p className="text-xs font-medium text-slate-200 truncate group-hover:text-purple-400 transition-colors">{order.product}</p>
                                            <p className="text-[10px] text-slate-500 mt-1">₹{order.amount} • {order.order_date}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Interactive Buttons */}
                        {buttons && buttons.length > 0 && isLastMessage && (
                            <div className="flex flex-wrap gap-3 mt-4 animate-in zoom-in-95 duration-200 delay-150">
                                {buttons.map((btn, idx) => {
                                    const isYes = btn.value.toLowerCase() === 'yes';
                                    const isNo = btn.value.toLowerCase() === 'no';

                                    return (
                                        <button
                                            key={idx}
                                            onClick={() => onSendMessage(btn.value)}
                                            className={`flex items-center gap-2 py-2 px-5 rounded-xl border transition-all duration-300 font-semibold text-sm shadow-lg
                                                ${isYes ? 'bg-green-600/20 border-green-500/30 text-green-400 hover:bg-green-600/40 hover:scale-105 active:scale-95' :
                                                    isNo ? 'bg-red-600/20 border-red-500/30 text-red-400 hover:bg-red-600/40 hover:scale-105 active:scale-95' :
                                                        'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10 hover:scale-105 active:scale-95'}`}
                                        >
                                            {isYes && <CheckCircle2 size={16} />}
                                            {isNo && <XCircle size={16} />}
                                            {btn.label}
                                        </button>
                                    );
                                })}
                            </div>
                        )}

                        {/* Label Download Button */}
                        {labelUrl && (
                            <div className="mt-4">
                                <a
                                    href={labelUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="w-full py-3 px-4 rounded-xl bg-green-600/20 border border-green-500/30 text-green-400 flex items-center justify-center gap-2 hover:bg-green-600/30 transition-all duration-300 group"
                                >
                                    <Info size={18} className="animate-pulse" />
                                    <span className="font-semibold text-sm">Download Return Label</span>
                                </a>
                                <p className="text-[10px] text-green-500/60 mt-2 text-center">
                                    Click to open and print your return label.
                                </p>
                            </div>
                        )}

                        {pipelineData && (
                            <div className="mt-4 pt-3 border-t border-white/10 flex flex-wrap gap-2">
                                {pipelineData.triage_output?.intent && (
                                    <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-blue-500/10 text-[10px] text-blue-400 border border-blue-500/20">
                                        <Info size={10} /> {pipelineData.triage_output.intent}
                                    </span>
                                )}
                                {pipelineData.triage_output?.urgency && (
                                    <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-orange-500/10 text-[10px] text-orange-400 border border-orange-500/20">
                                        <AlertCircle size={10} /> {pipelineData.triage_output.urgency}
                                    </span>
                                )}
                                {pipelineData.database_output?.order_found && (
                                    <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-green-500/10 text-[10px] text-green-400 border border-green-500/20">
                                        <Package size={10} /> Sync Verified
                                    </span>
                                )}
                                {pipelineData.policy_output?.policy_checked && (
                                    <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md ${pipelineData.policy_output.allowed ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
                                        } text-[10px] border ${pipelineData.policy_output.allowed ? 'border-green-500/20' : 'border-red-500/20'}`}>
                                        <CheckCircle2 size={10} /> {pipelineData.policy_output.allowed ? 'Policy Clear' : 'Policy Denied'}
                                    </span>
                                )}
                            </div>
                        )}
                    </GlassCard>

                    {message.timestamp && (
                        <span className={`text-[10px] text-slate-500 ${isUser ? 'text-right' : 'text-left'}`}>
                            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
};

export default MessageBubble;
