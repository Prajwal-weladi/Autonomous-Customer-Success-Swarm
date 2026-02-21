import axios from 'axios';
import logger from '../utils/logger';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000/v1';

const apiClient = axios.create({
    baseURL: BACKEND_URL,
    timeout: 120000,
});

export const sendMessage = async (conversationId, message) => {
    logger.info(`Sending message to basic endpoint: ${message} (Conversation: ${conversationId})`);
    try {
        const response = await apiClient.post('/message', {
            conversation_id: conversationId,
            message: message,
        });
        logger.info(`Received response from basic endpoint`);
        return response.data;
    } catch (error) {
        logger.error(`Error in sendMessage: ${error.message}`);
        throw error;
    }
};

export const sendPipelineMessage = async (conversationId, message) => {
    logger.info(`Sending message to pipeline endpoint: ${message} (Conversation: ${conversationId})`);
    try {
        const response = await apiClient.post('/pipeline', {
            conversation_id: conversationId,
            message: message,
        });
        logger.info(`Received response from pipeline endpoint`);
        return response.data;
    } catch (error) {
        logger.error(`Error in sendPipelineMessage: ${error.message}`);
        throw error;
    }
};

export default apiClient;
