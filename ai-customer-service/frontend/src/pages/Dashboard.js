import React, { useState, useEffect, useContext } from 'react';
import { w3cwebsocket as W3CWebSocket } from "websocket";
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  Typography,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  IconButton,
  Avatar,
  Menu,
  MenuItem,
  Divider,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Chat as ChatIcon,
  Assignment as LogsIcon,
  Dashboard as DashboardIcon,
  Help as HelpIcon,
  AccountCircle as AccountIcon,
  Logout as LogoutIcon,
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import ChatInterface from '../components/ChatInterface';
import LogsManager from '../components/LogsManager';
import SystemMonitoringDashboard from '../components/SystemMonitoringDashboard';
import { AuthContext } from '../contexts/AuthContext';

const drawerWidth = 240;

const Dashboard = () => {
  const [activeTab, setActiveTab] = useState('chat');
  const [mobileOpen, setMobileOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState(null);
  const { user, logout } = useAuth();
  const [telemetryData, setTelemetryData] = useState(null);
  const [logs, setLogs] = useState([]);
  
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  useEffect(() => {
    if (user && user.id) {
        const client = new W3CWebSocket(`ws://localhost:8000/ws/${user.id}`);

        client.onopen = () => {
            console.log('WebSocket Client Connected');
        };

        client.onmessage = (message) => {
            const data = JSON.parse(message.data);
            if (data.type === 'telemetry') {
                setTelemetryData(data.payload);
            } else if (data.type === 'log') {
                setLogs(prevLogs => [...prevLogs, data.payload]);
            } else if (data.status === 'processing') {
                console.log('Processing request...');
            } else if (data.status === 'complete') {
                console.log('Response received:', data.response);
            }
        };

        client.onclose = () => {
            console.log('WebSocket Client Disconnected');
        };

        return () => {
            client.close();
        };
    }
  }, [user]);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleProfileMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleProfileMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    handleProfileMenuClose();
    logout();
  };

  const menuItems = [
    { id: 'chat', label: 'AI Chat', icon: <ChatIcon /> },
    { id: 'logs', label: 'Customer Logs', icon: <LogsIcon /> },
    { id: 'dashboard', label: 'Analytics', icon: <DashboardIcon /> },
    { id: 'help', label: 'Help & FAQ', icon: <HelpIcon /> },
  ];

  const drawer = (
    <Box>
      <Toolbar>
        <Typography variant="h6" noWrap component="div">
          AI Assistant
        </Typography>
      </Toolbar>
      <Divider />
      <List>
        {menuItems.map((item) => (
          <ListItem
            button
            key={item.id}
            selected={activeTab === item.id}
            onClick={() => {
              setActiveTab(item.id);
              if (isMobile) {
                setMobileOpen(false);
              }
            }}
          >
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText primary={item.label} />
          </ListItem>
        ))}
      </List>
    </Box>
  );

  const renderContent = () => {
    switch (activeTab) {
      case 'chat':
        return <ChatInterface />;
      case 'logs':
        return <LogsManager logs={logs} />;
      case 'dashboard':
        return <SystemMonitoringDashboard data={telemetryData} />;
      default:
        return <ChatInterface />;
    }
  };

  return (
    <Box sx={{ display: 'flex', height: '100vh' }}>
      <AppBar
        position="fixed"
        sx={{
          width: { md: `calc(100% - ${drawerWidth}px)` },
          ml: { md: `${drawerWidth}px` },
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { md: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            {menuItems.find(item => item.id === activeTab)?.label || 'Dashboard'}
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="body2">{user?.full_name || user?.username}</Typography>
            <IconButton
              size="large"
              aria-label="account of current user"
              aria-controls="profile-menu"
              aria-haspopup="true"
              onClick={handleProfileMenuOpen}
              color="inherit"
            >
              <Avatar sx={{ width: 32, height: 32 }}>
                <AccountIcon />
              </Avatar>
            </IconButton>
          </Box>
        </Toolbar>
      </AppBar>

      <Box
        component="nav"
        sx={{ width: { md: drawerWidth }, flexShrink: { md: 0 } }}
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true,
          }}
          sx={{
            display: { xs: 'block', md: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', md: 'block' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          width: { md: `calc(100% - ${drawerWidth}px)` },
          height: '100vh',
          overflow: 'auto',
        }}
      >
        <Toolbar />
        {renderContent()}
      </Box>

      <Menu
        id="profile-menu"
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleProfileMenuClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
      >
        <MenuItem onClick={handleProfileMenuClose}>
          <ListItemIcon>
            <AccountIcon fontSize="small" />
          </ListItemIcon>
          Profile
        </MenuItem>
        <Divider />
        <MenuItem onClick={handleLogout}>
          <ListItemIcon>
            <LogoutIcon fontSize="small" />
          </ListItemIcon>
          Logout
        </MenuItem>
      </Menu>
    </Box>
  );
};

export default Dashboard;
