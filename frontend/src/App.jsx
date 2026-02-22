import React, { useState, useEffect } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import Auth from './components/Auth';
import { sendPipelineMessage, sendMessage as sendBasicMessage, getUserHistory } from './api/client';
import logger from './utils/logger';

const App = () => {
  const [conversations, setConversations] = useState([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [user, setUser] = useState(null);

  // Check for existing session
  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }
  }, []);

  // Initialize first conversation
  useEffect(() => {
    const saved = localStorage.getItem('conversations');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.length > 0) {
          setConversations(parsed);
          return;
        }
      } catch (e) {
        logger.error('Failed to parse saved conversations', e);
      }
    }
    createNewChat();
  }, []);

  // Save to localStorage
  useEffect(() => {
    if (conversations.length > 0) {
      localStorage.setItem('conversations', JSON.stringify(conversations));
    }
  }, [conversations]);

  const createNewChat = () => {
    const newChat = {
      conversation_id: `conv_${Date.now()}`,
      title: `Chat ${conversations.length + 1}`,
      messages: [],
      status: 'active',
      created_at: new Date().toISOString()
    };
    setConversations(prev => [...prev, newChat]);
    setActiveIndex(conversations.length);
    logger.info('Created new chat', newChat.conversation_id);
    toast.success('New chat started');
  };

  const selectChat = (index) => {
    setActiveIndex(index);
    logger.info('Selected chat', conversations[index].conversation_id);
  };

  const deleteChat = (index) => {
    const convId = conversations[index].conversation_id;
    const newConvs = conversations.filter((_, i) => i !== index);
    if (newConvs.length === 0) {
      createNewChat();
    } else {
      setConversations(newConvs);
      setActiveIndex(Math.max(0, index - 1));
    }
    logger.warn('Deleted chat', convId);
    toast.error('Chat deleted');
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    setConversations([]);
    createNewChat();
    toast.success('Logged out successfully');
  };

  const handleAuthSuccess = async (userData) => {
    setUser(userData);
    setIsLoading(true);
    try {
      const history = await getUserHistory(userData.email);
      if (history && history.length > 0) {
        // Group by conversation_id
        const grouped = history.reduce((acc, msg) => {
          const cid = msg.conversation_id;
          if (!acc[cid]) {
            acc[cid] = {
              conversation_id: cid,
              title: `Chat ${Object.keys(acc).length + 1}`,
              messages: [],
              status: 'active',
              created_at: new Date().toISOString()
            };
          }
          acc[cid].messages.push({
            role: msg.role,
            content: msg.content,
            timestamp: new Date().toISOString()
          });

          // Update title based on first user message
          if (msg.role === 'user' && acc[cid].messages.length <= 2) {
            acc[cid].title = msg.content.substring(0, 30) + (msg.content.length > 30 ? '...' : '');
          }

          return acc;
        }, {});

        const convArray = Object.values(grouped);
        setConversations(convArray);
        setActiveIndex(convArray.length - 1);
        logger.info('Restored chat history', convArray.length);
      } else {
        createNewChat();
      }
    } catch (error) {
      logger.error('Failed to load history', error);
      toast.error('Could not load chat history');
      createNewChat();
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async (content) => {
    const activeConv = conversations[activeIndex];
    const userEmail = user?.email; // Link message to authenticated user
    const userMsg = {
      role: 'user',
      content,
      timestamp: new Date().toISOString()
    };

    // Update local state immediately
    const updatedConvs = [...conversations];
    updatedConvs[activeIndex].messages.push(userMsg);
    setConversations(updatedConvs);

    setIsLoading(true);
    try {
      // Determine which endpoint to use (simplified logic from Streamlit version)
      let response;
      if (activeConv.status === 'awaiting_confirmation') {
        response = await sendBasicMessage(activeConv.conversation_id, content, userEmail);
      } else {
        response = await sendPipelineMessage(activeConv.conversation_id, content, userEmail);
      }

      const assistantMsg = {
        role: 'assistant',
        content: response.reply || response.resolution_output?.message || 'I processed your request.',
        pipeline_data: response,
        timestamp: new Date().toISOString()
      };

      const finalConvs = [...conversations];
      finalConvs[activeIndex].messages.push(assistantMsg);
      finalConvs[activeIndex].status = response.status || 'active';

      // Update title if it's the first message
      if (finalConvs[activeIndex].messages.length === 2) {
        finalConvs[activeIndex].title = content.substring(0, 30) + (content.length > 30 ? '...' : '');
      }

      setConversations(finalConvs);
      logger.info('Received assistant response', assistantMsg);
    } catch (error) {
      logger.error('Failed to send message', error);
      toast.error('Failed to send message. Please try again.');

      const errorMsg = {
        role: 'assistant',
        content: 'Sorry, I encountered an error connecting to the support system.',
        timestamp: new Date().toISOString()
      };
      const errorConvs = [...conversations];
      errorConvs[activeIndex].messages.push(errorMsg);
      setConversations(errorConvs);
    } finally {
      setIsLoading(false);
    }
  };

  const handleMyOrders = () => {
    handleSendMessage('List my orders');
  };

  if (!user) {
    return (
      <>
        <Toaster position="top-right" />
        <Auth onAuthSuccess={handleAuthSuccess} />
      </>
    );
  }

  if (conversations.length === 0) return null;

  return (
    <div className="flex h-screen w-full bg-[#0f172a] text-slate-200 overflow-hidden font-sans">
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: 'rgba(30, 41, 59, 0.8)',
            color: '#fff',
            backdropFilter: 'blur(8px)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
          },
        }}
      />

      <Sidebar
        conversations={conversations}
        activeIndex={activeIndex}
        onNewChat={createNewChat}
        onSelectChat={selectChat}
        onDeleteChat={deleteChat}
        user={user}
        onLogout={handleLogout}
        onMyOrders={handleMyOrders}
      />

      <main className="flex-1 relative">
        {/* Background decorative elements */}
        <div className="absolute top-[-10%] right-[-10%] w-[50%] h-[50%] bg-blue-600/10 rounded-full blur-[120px] pointer-events-none"></div>
        <div className="absolute bottom-[-10%] left-[-10%] w-[50%] h-[50%] bg-purple-600/10 rounded-full blur-[120px] pointer-events-none"></div>

        <ChatWindow
          messages={conversations[activeIndex].messages}
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          handoffStatus={conversations[activeIndex].status}
        />
      </main>
    </div>
  );
};

export default App;
