import React, { createContext, useContext, useReducer, useEffect } from 'react';
import axios from 'axios';

// Enhanced State Management with Context and Reducer
const initialState = {
  user: null,
  conversations: [],
  activeConversation: null,
  messages: [],
  isLoading: false,
  error: null,
  isConnected: true,
  typing: false,
  unreadCount: 0,
  theme: 'light',
  notifications: [],
  systemHealth: null
};

const actionTypes = {
  SET_USER: 'SET_USER',
  SET_CONVERSATIONS: 'SET_CONVERSATIONS',
  SET_ACTIVE_CONVERSATION: 'SET_ACTIVE_CONVERSATION',
  ADD_MESSAGE: 'ADD_MESSAGE',
  UPDATE_MESSAGE: 'UPDATE_MESSAGE',
  SET_MESSAGES: 'SET_MESSAGES',
  SET_LOADING: 'SET_LOADING',
  SET_ERROR: 'SET_ERROR',
  SET_CONNECTION_STATUS: 'SET_CONNECTION_STATUS',
  SET_TYPING: 'SET_TYPING',
  SET_UNREAD_COUNT: 'SET_UNREAD_COUNT',
  SET_THEME: 'SET_THEME',
  ADD_NOTIFICATION: 'ADD_NOTIFICATION',
  REMOVE_NOTIFICATION: 'REMOVE_NOTIFICATION',
  SET_SYSTEM_HEALTH: 'SET_SYSTEM_HEALTH',
  RESET_STATE: 'RESET_STATE'
};

function appReducer(state, action) {
  switch (action.type) {
    case actionTypes.SET_USER:
      return { ...state, user: action.payload };
    
    case actionTypes.SET_CONVERSATIONS:
      return { ...state, conversations: action.payload };
    
    case actionTypes.SET_ACTIVE_CONVERSATION:
      return { 
        ...state, 
        activeConversation: action.payload,
        unreadCount: 0
      };
    
    case actionTypes.ADD_MESSAGE:
      return {
        ...state,
        messages: [...state.messages, action.payload],
        unreadCount: action.payload.role === 'assistant' ? state.unreadCount + 1 : state.unreadCount
      };
    
    case actionTypes.UPDATE_MESSAGE:
      return {
        ...state,
        messages: state.messages.map(msg => 
          msg.id === action.payload.id ? { ...msg, ...action.payload } : msg
        )
      };
    
    case actionTypes.SET_MESSAGES:
      return { ...state, messages: action.payload };
    
    case actionTypes.SET_LOADING:
      return { ...state, isLoading: action.payload };
    
    case actionTypes.SET_ERROR:
      return { ...state, error: action.payload };
    
    case actionTypes.SET_CONNECTION_STATUS:
      return { ...state, isConnected: action.payload };
    
    case actionTypes.SET_TYPING:
      return { ...state, typing: action.payload };
    
    case actionTypes.SET_UNREAD_COUNT:
      return { ...state, unreadCount: action.payload };
    
    case actionTypes.SET_THEME:
      localStorage.setItem('theme', action.payload);
      return { ...state, theme: action.payload };
    
    case actionTypes.ADD_NOTIFICATION:
      return {
        ...state,
        notifications: [...state.notifications, { ...action.payload, id: Date.now() }]
      };
    
    case actionTypes.REMOVE_NOTIFICATION:
      return {
        ...state,
        notifications: state.notifications.filter(notif => notif.id !== action.payload)
      };
    
    case actionTypes.SET_SYSTEM_HEALTH:
      return { ...state, systemHealth: action.payload };
    
    case actionTypes.RESET_STATE:
      return { ...initialState, theme: state.theme };
    
    default:
      return state;
  }
}

// Context creation
const AppContext = createContext();

// Custom hooks for context
export const useAppState = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppState must be used within an AppProvider');
  }
  return context;
};

// Enhanced API service with interceptors and error handling
class ApiService {
  constructor() {
    this.baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  setupInterceptors() {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('authToken');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        
        // Add request ID for tracking
        config.headers['X-Request-ID'] = this.generateRequestId();
        
        console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        console.error('Request interceptor error:', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        const requestId = response.headers['x-request-id'];
        console.log(`API Response: ${response.status} - Request ID: ${requestId}`);
        return response;
      },
      (error) => {
        const { response } = error;
        
        if (response?.status === 401) {
          // Handle unauthorized access
          localStorage.removeItem('authToken');
          window.location.href = '/login';
          return Promise.reject(new Error('Session expired. Please login again.'));
        }
        
        if (response?.status === 429) {
          // Handle rate limiting
          const retryAfter = response.headers['retry-after'] || 60;
          return Promise.reject(new Error(`Rate limit exceeded. Try again in ${retryAfter} seconds.`));
        }
        
        if (response?.status >= 500) {
          // Handle server errors
          return Promise.reject(new Error('Server error. Please try again later.'));
        }
        
        // Handle network errors
        if (!response) {
          return Promise.reject(new Error('Network error. Please check your connection.'));
        }
        
        return Promise.reject(error);
      }
    );
  }

  generateRequestId() {
    return Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
  }

  // Authentication methods
  async login(credentials) {
    const response = await this.client.post('/api/v1/auth/login', credentials);
    const { access_token } = response.data;
    localStorage.setItem('authToken', access_token);
    return response.data;
  }

  async register(userData) {
    const response = await this.client.post('/api/v1/auth/register', userData);
    return response.data;
  }

  async logout() {
    try {
      await this.client.post('/api/v1/auth/logout');
    } finally {
      localStorage.removeItem('authToken');
    }
  }

  // Chat methods
  async sendMessage(message, conversationId = null) {
    const response = await this.client.post('/api/v1/chat/chat', {
      message,
      conversation_id: conversationId
    });
    return response.data;
  }

  async getConversations() {
    const response = await this.client.get('/api/v1/chat/conversations');
    return response.data;
  }

  async getConversationHistory(conversationId) {
    const response = await this.client.get(`/api/v1/chat/conversations/${conversationId}/messages`);
    return response.data;
  }

  async createConversation(title) {
    const response = await this.client.post('/api/v1/chat/conversations', { title });
    return response.data;
  }

  async deleteConversation(conversationId) {
    const response = await this.client.delete(`/api/v1/chat/conversations/${conversationId}`);
    return response.data;
  }

  // System methods
  async getSystemHealth() {
    const response = await this.client.get('/health');
    return response.data;
  }

  async getMetrics() {
    const response = await this.client.get('/metrics');
    return response.data;
  }

  // User methods
  async getCurrentUser() {
    const response = await this.client.get('/api/v1/auth/me');
    return response.data;
  }

  async updateUserProfile(userData) {
    const response = await this.client.put('/api/v1/auth/profile', userData);
    return response.data;
  }
}

const apiService = new ApiService();

// WebSocket service for real-time communication
class WebSocketService {
  constructor() {
    this.socket = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectInterval = 1000;
    this.listeners = new Map();
  }

  connect(token) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      return;
    }

    const wsUrl = `${process.env.REACT_APP_WS_URL || 'ws://localhost:8000'}/ws?token=${token}`;
    
    try {
      this.socket = new WebSocket(wsUrl);
      
      this.socket.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.emit('connection', { status: 'connected' });
      };

      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.emit(data.type, data.payload);
        } catch (error) {
          console.error('WebSocket message parsing error:', error);
        }
      };

      this.socket.onclose = () => {
        console.log('WebSocket disconnected');
        this.emit('connection', { status: 'disconnected' });
        this.attemptReconnect(token);
      };

      this.socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.emit('error', error);
      };
    } catch (error) {
      console.error('WebSocket connection error:', error);
      this.emit('error', error);
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  send(type, payload) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ type, payload }));
    } else {
      console.warn('WebSocket not connected. Message not sent:', { type, payload });
    }
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event);
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => callback(data));
    }
  }

  attemptReconnect(token) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      
      setTimeout(() => {
        this.connect(token);
      }, this.reconnectInterval * this.reconnectAttempts);
    } else {
      console.error('Max reconnection attempts reached');
      this.emit('maxReconnectAttemptsReached');
    }
  }
}

const wsService = new WebSocketService();

// Main App Provider component
export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(appReducer, {
    ...initialState,
    theme: localStorage.getItem('theme') || 'light'
  });

  // Actions
  const actions = {
    setUser: (user) => dispatch({ type: actionTypes.SET_USER, payload: user }),
    setConversations: (conversations) => dispatch({ type: actionTypes.SET_CONVERSATIONS, payload: conversations }),
    setActiveConversation: (conversation) => dispatch({ type: actionTypes.SET_ACTIVE_CONVERSATION, payload: conversation }),
    addMessage: (message) => dispatch({ type: actionTypes.ADD_MESSAGE, payload: message }),
    updateMessage: (message) => dispatch({ type: actionTypes.UPDATE_MESSAGE, payload: message }),
    setMessages: (messages) => dispatch({ type: actionTypes.SET_MESSAGES, payload: messages }),
    setLoading: (loading) => dispatch({ type: actionTypes.SET_LOADING, payload: loading }),
    setError: (error) => dispatch({ type: actionTypes.SET_ERROR, payload: error }),
    setConnectionStatus: (status) => dispatch({ type: actionTypes.SET_CONNECTION_STATUS, payload: status }),
    setTyping: (typing) => dispatch({ type: actionTypes.SET_TYPING, payload: typing }),
    setUnreadCount: (count) => dispatch({ type: actionTypes.SET_UNREAD_COUNT, payload: count }),
    setTheme: (theme) => dispatch({ type: actionTypes.SET_THEME, payload: theme }),
    addNotification: (notification) => dispatch({ type: actionTypes.ADD_NOTIFICATION, payload: notification }),
    removeNotification: (id) => dispatch({ type: actionTypes.REMOVE_NOTIFICATION, payload: id }),
    setSystemHealth: (health) => dispatch({ type: actionTypes.SET_SYSTEM_HEALTH, payload: health }),
    resetState: () => dispatch({ type: actionTypes.RESET_STATE })
  };

  // Enhanced service methods
  const services = {
    // Authentication
    async login(credentials) {
      try {
        actions.setLoading(true);
        actions.setError(null);
        
        const userData = await apiService.login(credentials);
        actions.setUser(userData.user);
        
        // Connect WebSocket
        wsService.connect(userData.access_token);
        
        actions.addNotification({
          type: 'success',
          message: 'Successfully logged in!'
        });
        
        return userData;
      } catch (error) {
        const errorMessage = error.message || 'Login failed';
        actions.setError(errorMessage);
        actions.addNotification({
          type: 'error',
          message: errorMessage
        });
        throw error;
      } finally {
        actions.setLoading(false);
      }
    },

    async logout() {
      try {
        await apiService.logout();
        wsService.disconnect();
        actions.resetState();
        actions.addNotification({
          type: 'info',
          message: 'Logged out successfully'
        });
      } catch (error) {
        console.error('Logout error:', error);
        // Still reset state even if logout API fails
        actions.resetState();
      }
    },

    // Chat operations
    async sendMessage(message, conversationId = null) {
      try {
        actions.setTyping(true);
        actions.setError(null);

        // Add user message immediately for better UX
        const userMessage = {
          id: `temp-${Date.now()}`,
          content: message,
          role: 'user',
          timestamp: new Date().toISOString(),
          isTemporary: true
        };
        actions.addMessage(userMessage);

        const response = await apiService.sendMessage(message, conversationId);
        
        // Remove temporary message and add real messages
        actions.setMessages(state.messages.filter(msg => !msg.isTemporary));
        actions.addMessage(response.user_message);
        actions.addMessage(response.ai_message);

        return response;
      } catch (error) {
        const errorMessage = error.message || 'Failed to send message';
        actions.setError(errorMessage);
        actions.addNotification({
          type: 'error',
          message: errorMessage
        });
        
        // Remove temporary message on error
        actions.setMessages(state.messages.filter(msg => !msg.isTemporary));
        throw error;
      } finally {
        actions.setTyping(false);
      }
    },

    async loadConversations() {
      try {
        actions.setLoading(true);
        const conversations = await apiService.getConversations();
        actions.setConversations(conversations);
        return conversations;
      } catch (error) {
        actions.setError('Failed to load conversations');
        actions.addNotification({
          type: 'error',
          message: 'Failed to load conversations'
        });
        throw error;
      } finally {
        actions.setLoading(false);
      }
    },

    async loadConversationHistory(conversationId) {
      try {
        actions.setLoading(true);
        const messages = await apiService.getConversationHistory(conversationId);
        actions.setMessages(messages);
        return messages;
      } catch (error) {
        actions.setError('Failed to load conversation history');
        throw error;
      } finally {
        actions.setLoading(false);
      }
    },

    // System monitoring
    async checkSystemHealth() {
      try {
        const health = await apiService.getSystemHealth();
        actions.setSystemHealth(health);
        return health;
      } catch (error) {
        actions.setSystemHealth({ status: 'unhealthy', error: error.message });
        console.error('Health check failed:', error);
      }
    }
  };

  // WebSocket event handlers
  useEffect(() => {
    const handleConnection = (data) => {
      actions.setConnectionStatus(data.status === 'connected');
    };

    const handleNewMessage = (message) => {
      actions.addMessage(message);
    };

    const handleTyping = (data) => {
      actions.setTyping(data.typing);
    };

    const handleError = (error) => {
      console.error('WebSocket error:', error);
      actions.setConnectionStatus(false);
    };

    const handleMaxReconnectAttempts = () => {
      actions.addNotification({
        type: 'error',
        message: 'Connection lost. Please refresh the page.'
      });
    };

    // Register WebSocket event listeners
    wsService.on('connection', handleConnection);
    wsService.on('new_message', handleNewMessage);
    wsService.on('typing', handleTyping);
    wsService.on('error', handleError);
    wsService.on('maxReconnectAttemptsReached', handleMaxReconnectAttempts);

    // Cleanup on unmount
    return () => {
      wsService.off('connection', handleConnection);
      wsService.off('new_message', handleNewMessage);
      wsService.off('typing', handleTyping);
      wsService.off('error', handleError);
      wsService.off('maxReconnectAttemptsReached', handleMaxReconnectAttempts);
    };
  }, []);

  // Auto-remove notifications
  useEffect(() => {
    state.notifications.forEach(notification => {
      if (notification.autoRemove !== false) {
        setTimeout(() => {
          actions.removeNotification(notification.id);
        }, 5000);
      }
    });
  }, [state.notifications]);

  // Periodic health checks
  useEffect(() => {
    const healthCheckInterval = setInterval(() => {
      services.checkSystemHealth();
    }, 60000); // Check every minute

    // Initial health check
    services.checkSystemHealth();

    return () => clearInterval(healthCheckInterval);
  }, []);

  // Theme application
  useEffect(() => {
    document.body.className = state.theme;
  }, [state.theme]);

  const contextValue = {
    state,
    actions,
    services,
    wsService,
    apiService
  };

  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
}

export { apiService, wsService };
