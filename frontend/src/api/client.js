import axios from 'axios';
import logger from '../utils/logger';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000/v1';

const apiClient = axios.create({
    baseURL: BACKEND_URL,
    timeout: 120000,
});

// Add a request interceptor to include the JWT token
apiClient.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

export const login = async (email, password) => {
    logger.info(`Attempting login for ${email}`);
    try {
        const response = await apiClient.post('/auth/login', { email, password });
        if (response.data.access_token) {
            localStorage.setItem('token', response.data.access_token);
            localStorage.setItem('user', JSON.stringify(response.data));
        }
        return response.data;
    } catch (error) {
        logger.error(`Login failed: ${error.message}`);
        throw error;
    }
};

export const signup = async (email, password, fullName) => {
    logger.info(`Attempting signup for ${email}`);
    try {
        const response = await apiClient.post('/auth/signup', {
            email,
            password,
            full_name: fullName
        });
        if (response.data.access_token) {
            localStorage.setItem('token', response.data.access_token);
            localStorage.setItem('user', JSON.stringify(response.data));
        }
        return response.data;
    } catch (error) {
        logger.error(`Signup failed: ${error.message}`);
        throw error;
    }
};

export const getUserHistory = async (email) => {
    logger.info(`Fetching history for ${email}`);
    try {
        const response = await apiClient.get('/auth/history', {
            params: { email }
        });
        return response.data;
    } catch (error) {
        logger.error(`Failed to fetch history: ${error.message}`);
        throw error;
    }
};

export const sendMessage = async (conversationId, message, userEmail = null) => {
    logger.info(`Sending message to basic endpoint: ${message} (Conversation: ${conversationId})`);
    try {
        const response = await apiClient.post('/message', {
            conversation_id: conversationId,
            message: message,
            user_email: userEmail
        });
        logger.info(`Received response from basic endpoint`);
        return response.data;
    } catch (error) {
        logger.error(`Error in sendMessage: ${error.message}`);
        throw error;
    }
};

export const sendPipelineMessage = async (conversationId, message, userEmail = null) => {
    logger.info(`Sending message to pipeline endpoint: ${message} (Conversation: ${conversationId})`);
    try {
        const response = await apiClient.post('/pipeline', {
            conversation_id: conversationId,
            message: message,
            user_email: userEmail
        });
        logger.info(`Received response from pipeline endpoint`);
        return response.data;
    } catch (error) {
        logger.error(`Error in sendPipelineMessage: ${error.message}`);
        throw error;
    }
};

export default apiClient;
