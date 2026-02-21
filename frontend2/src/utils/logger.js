const logger = {
    info: (message, ...args) => {
        console.log(`[INFO] [${new Date().toLocaleTimeString()}] ${message}`, ...args);
    },
    error: (message, ...args) => {
        console.error(`[ERROR] [${new Date().toLocaleTimeString()}] ${message}`, ...args);
    },
    warn: (message, ...args) => {
        console.warn(`[WARN] [${new Date().toLocaleTimeString()}] ${message}`, ...args);
    },
    debug: (message, ...args) => {
        if (import.meta.env.DEV) {
            console.debug(`[DEBUG] [${new Date().toLocaleTimeString()}] ${message}`, ...args);
        }
    }
};

export default logger;
