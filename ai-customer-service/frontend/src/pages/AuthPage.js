import React, { useState } from 'react';
import {
  Container,
  Paper,
  Tabs,
  Tab,
  Box,
  TextField,
  Button,
  Typography,
  Alert,
  CircularProgress,
} from '@mui/material';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

function TabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`auth-tabpanel-${index}`}
      aria-labelledby={`auth-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const AuthPage = () => {
  const [tab, setTab] = useState(0);
  const [loginForm, setLoginForm] = useState({ username: '', password: '' });
  const [registerForm, setRegisterForm] = useState({
    username: '',
    email: '',
    full_name: '',
    password: '',
    confirmPassword: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const { login, register } = useAuth();
  const navigate = useNavigate();

  const handleTabChange = (event, newValue) => {
    setTab(newValue);
    setError('');
    setSuccess('');
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await login(loginForm.username, loginForm.password);

    if (result.success) {
      navigate('/dashboard');
    } else {
      setError(result.error);
    }

    setLoading(false);
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    if (registerForm.password !== registerForm.confirmPassword) {
      setError('Passwords do not match');
      setLoading(false);
      return;
    }

    const { confirmPassword, ...userData } = registerForm;
    const result = await register(userData);

    if (result.success) {
      setSuccess('Registration successful! Please log in.');
      setTab(0);
      setRegisterForm({
        username: '',
        email: '',
        full_name: '',
        password: '',
        confirmPassword: '',
      });
    } else {
      setError(result.error);
    }

    setLoading(false);
  };

  return (
    <Container maxWidth="sm" sx={{ mt: 8 }}>
      <Paper elevation={3}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tab} onChange={handleTabChange} centered>
            <Tab label="Login" />
            <Tab label="Register" />
          </Tabs>
        </Box>

        <TabPanel value={tab} index={0}>
          <Typography variant="h4" align="center" gutterBottom>
            Welcome Back
          </Typography>
          <Typography variant="body2" align="center" color="textSecondary" gutterBottom>
            Sign in to access your AI assistant
          </Typography>

          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}

          <Box component="form" onSubmit={handleLogin}>
            <TextField
              fullWidth
              label="Username"
              value={loginForm.username}
              onChange={(e) =>
                setLoginForm({ ...loginForm, username: e.target.value })
              }
              margin="normal"
              required
            />
            <TextField
              fullWidth
              label="Password"
              type="password"
              value={loginForm.password}
              onChange={(e) =>
                setLoginForm({ ...loginForm, password: e.target.value })
              }
              margin="normal"
              required
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2 }}
              disabled={loading}
            >
              {loading ? <CircularProgress size={24} /> : 'Sign In'}
            </Button>
          </Box>
        </TabPanel>

        <TabPanel value={tab} index={1}>
          <Typography variant="h4" align="center" gutterBottom>
            Create Account
          </Typography>
          <Typography variant="body2" align="center" color="textSecondary" gutterBottom>
            Join our AI customer service platform
          </Typography>

          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

          <Box component="form" onSubmit={handleRegister}>
            <TextField
              fullWidth
              label="Username"
              value={registerForm.username}
              onChange={(e) =>
                setRegisterForm({ ...registerForm, username: e.target.value })
              }
              margin="normal"
              required
            />
            <TextField
              fullWidth
              label="Email"
              type="email"
              value={registerForm.email}
              onChange={(e) =>
                setRegisterForm({ ...registerForm, email: e.target.value })
              }
              margin="normal"
              required
            />
            <TextField
              fullWidth
              label="Full Name"
              value={registerForm.full_name}
              onChange={(e) =>
                setRegisterForm({ ...registerForm, full_name: e.target.value })
              }
              margin="normal"
            />
            <TextField
              fullWidth
              label="Password"
              type="password"
              value={registerForm.password}
              onChange={(e) =>
                setRegisterForm({ ...registerForm, password: e.target.value })
              }
              margin="normal"
              required
            />
            <TextField
              fullWidth
              label="Confirm Password"
              type="password"
              value={registerForm.confirmPassword}
              onChange={(e) =>
                setRegisterForm({ ...registerForm, confirmPassword: e.target.value })
              }
              margin="normal"
              required
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2 }}
              disabled={loading}
            >
              {loading ? <CircularProgress size={24} /> : 'Create Account'}
            </Button>
          </Box>
        </TabPanel>
      </Paper>
    </Container>
  );
};

export default AuthPage;
