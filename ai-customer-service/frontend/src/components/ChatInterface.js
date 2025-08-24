import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  List,
  ListItem,
  Avatar,
  Chip,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  Send as SendIcon,
  Person as PersonIcon,
  SmartToy as BotIcon,
} from '@mui/icons-material';
import axios from 'axios';
import { format } from 'date-fns';

const ChatInterface = () => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [error, setError] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages]);

  // Load existing conversation or create new one
  useEffect(() => {
    const loadConversations = async () => {
      try {
        const response = await axios.get('/api/v1/chat/conversations');
        if (response.data.length > 0) {
          const latestConversation = response.data[0];
          setConversationId(latestConversation.id);
          
          // Load messages from the latest conversation
          const convResponse = await axios.get(
            `/api/v1/chat/conversations/${latestConversation.id}`
          );
          setMessages(convResponse.data.messages || []);
        }
      } catch (error) {
        console.error('Failed to load conversations:', error);
      }
    };

    loadConversations();
  }, []);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || loading) return;

    const userMessage = {
      content: inputMessage,
      role: 'user',
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage('');
    setLoading(true);
    setError('');

    try {
      const response = await axios.post('/api/v1/chat/chat', {
        message: inputMessage,
        conversation_id: conversationId,
      });

      const aiMessage = {
        content: response.data.response,
        role: 'assistant',
        timestamp: new Date().toISOString(),
        tokens_used: response.data.tokens_used,
        response_time: response.data.response_time,
      };

      setMessages((prev) => [...prev, aiMessage]);
      setConversationId(response.data.conversation_id);
    } catch (error) {
      console.error('Failed to send message:', error);
      setError('Failed to send message. Please try again.');
      
      // Remove the user message that failed to send
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  };

  const MessageBubble = ({ message }) => {
    const isUser = message.role === 'user';
    
    return (
      <ListItem
        sx={{
          display: 'flex',
          flexDirection: isUser ? 'row-reverse' : 'row',
          alignItems: 'flex-start',
          gap: 1,
        }}
      >
        <Avatar sx={{ bgcolor: isUser ? 'primary.main' : 'secondary.main' }}>
          {isUser ? <PersonIcon /> : <BotIcon />}
        </Avatar>
        <Box
          sx={{
            maxWidth: '70%',
            bgcolor: isUser ? 'primary.main' : 'grey.100',
            color: isUser ? 'white' : 'text.primary',
            p: 2,
            borderRadius: 2,
            borderTopLeftRadius: isUser ? 2 : 0.5,
            borderTopRightRadius: isUser ? 0.5 : 2,
          }}
        >
          <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
            {message.content}
          </Typography>
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              mt: 1,
              gap: 1,
            }}
          >
            <Typography variant="caption" sx={{ opacity: 0.7 }}>
              {format(new Date(message.timestamp), 'HH:mm')}
            </Typography>
            {message.tokens_used && (
              <Chip
                label={`${message.tokens_used} tokens`}
                size="small"
                variant="outlined"
                sx={{ opacity: 0.7 }}
              />
            )}
            {message.response_time && (
              <Chip
                label={`${message.response_time}ms`}
                size="small"
                variant="outlined"
                sx={{ opacity: 0.7 }}
              />
            )}
          </Box>
        </Box>
      </ListItem>
    );
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Typography variant="h6" sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        AI Customer Service Assistant
      </Typography>

      {error && (
        <Alert severity="error" onClose={() => setError('')} sx={{ m: 2 }}>
          {error}
        </Alert>
      )}

      <Paper
        sx={{
          flex: 1,
          overflow: 'auto',
          m: 2,
          mb: 0,
        }}
      >
        <List sx={{ p: 0 }}>
          {messages.length === 0 ? (
            <ListItem sx={{ justifyContent: 'center', py: 4 }}>
              <Typography variant="body2" color="textSecondary">
                Start a conversation with your AI assistant!
              </Typography>
            </ListItem>
          ) : (
            messages.map((message, index) => (
              <MessageBubble key={index} message={message} />
            ))
          )}
          {loading && (
            <ListItem sx={{ justifyContent: 'center' }}>
              <CircularProgress size={24} />
            </ListItem>
          )}
          <div ref={messagesEndRef} />
        </List>
      </Paper>

      <Box
        component="form"
        onSubmit={sendMessage}
        sx={{
          p: 2,
          borderTop: 1,
          borderColor: 'divider',
          display: 'flex',
          gap: 1,
        }}
      >
        <TextField
          fullWidth
          placeholder="Type your message..."
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          disabled={loading}
          multiline
          maxRows={4}
        />
        <Button
          type="submit"
          variant="contained"
          disabled={loading || !inputMessage.trim()}
          sx={{ minWidth: 'auto', px: 2 }}
        >
          <SendIcon />
        </Button>
      </Box>
    </Box>
  );
};

export default ChatInterface;
