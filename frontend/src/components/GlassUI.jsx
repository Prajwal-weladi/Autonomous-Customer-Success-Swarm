import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
    return twMerge(clsx(inputs));
}

export const GlassCard = ({ children, className, noPadding = false }) => {
    return (
        <div className={cn(
            "glass-card rounded-2xl overflow-hidden",
            !noPadding && "p-6",
            className
        )}>
            {children}
        </div>
    );
};

export const GlassPanel = ({ children, className }) => {
    return (
        <div className={cn(
            "bg-white/5 backdrop-blur-md border border-white/10",
            className
        )}>
            {children}
        </div>
    );
};
