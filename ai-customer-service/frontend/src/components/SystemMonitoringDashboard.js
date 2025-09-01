import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  LinearProgress,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Tooltip,
  Alert,
  Divider,
  Switch,
  FormControlLabel,
  TextField,
  MenuItem,
  Select,
  FormControl,
  InputLabel
} from '@mui/material';
import {
  Timeline,
  TimelineItem,
  TimelineOppositeContent,
  TimelineSeparator,
  TimelineDot,
  TimelineConnector,
  TimelineContent
} from '@mui/lab';
import {
  Refresh,
  Settings,
  TrendingUp,
  TrendingDown,
  Warning,
  CheckCircle,
  Error,
  Info,
  Memory,
  Storage,
  Speed,
  NetworkCheck,
  People,
  Chat,
  Assessment,
  Security
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

// Enhanced System Monitoring Dashboard
const SystemMonitoringDashboard = () => {
  const [metrics, setMetrics] = useState({
    system: {
      cpu: 45,
      memory: 68,
      disk: 72,
      network: 89
    },
    api: {
      responseTime: 125,
      requestsPerSecond: 234,
      errorRate: 0.5,
      activeConnections: 456
    },
    ai: {
      tokenUsage: 15432,
      modelLatency: 890,
      accuracy: 94.5,
      conversationsActive: 23
    }
  });

  const [alerts, setAlerts] = useState([
    {
      id: 1,
      type: 'warning',
      title: 'High Memory Usage',
      message: 'Memory usage is above 65%',
      timestamp: new Date().toISOString(),
      acknowledged: false
    },
    {
      id: 2,
      type: 'info',
      title: 'Model Updated',
      message: 'AI model v2.1.0 deployed successfully',
      timestamp: new Date().toISOString(),
      acknowledged: true
    }
  ]);

  const [performanceData, setPerformanceData] = useState([
    { time: '00:00', responseTime: 120, requests: 180, errors: 2 },
    { time: '01:00', responseTime: 115, requests: 195, errors: 1 },
    { time: '02:00', responseTime: 125, requests: 210, errors: 3 },
    { time: '03:00', responseTime: 130, requests: 225, errors: 2 },
    { time: '04:00', responseTime: 118, requests: 240, errors: 1 },
    { time: '05:00', responseTime: 122, requests: 220, errors: 4 }
  ]);

  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(30);
  const [selectedTimeRange, setSelectedTimeRange] = useState('24h');

  // Simulate real-time data updates
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      setMetrics(prev => ({
        ...prev,
        system: {
          cpu: Math.max(0, Math.min(100, prev.system.cpu + (Math.random() - 0.5) * 10)),
          memory: Math.max(0, Math.min(100, prev.system.memory + (Math.random() - 0.5) * 5)),
          disk: Math.max(0, Math.min(100, prev.system.disk + (Math.random() - 0.5) * 2)),
          network: Math.max(0, Math.min(100, prev.system.network + (Math.random() - 0.5) * 15))
        },
        api: {
          responseTime: Math.max(50, prev.api.responseTime + (Math.random() - 0.5) * 20),
          requestsPerSecond: Math.max(0, prev.api.requestsPerSecond + (Math.random() - 0.5) * 50),
          errorRate: Math.max(0, Math.min(5, prev.api.errorRate + (Math.random() - 0.5) * 0.5)),
          activeConnections: Math.max(0, prev.api.activeConnections + Math.floor((Math.random() - 0.5) * 20))
        }
      }));
    }, refreshInterval * 1000);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval]);

  const getStatusColor = (value, thresholds) => {
    if (value >= thresholds.danger) return 'error';
    if (value >= thresholds.warning) return 'warning';
    return 'success';
  };

  const getAlertIcon = (type) => {
    switch (type) {
      case 'error': return <Error color="error" />;
      case 'warning': return <Warning color="warning" />;
      case 'info': return <Info color="info" />;
      default: return <CheckCircle color="success" />;
    }
  };

  const acknowledgeAlert = (alertId) => {
    setAlerts(prev => 
      prev.map(alert => 
        alert.id === alertId 
          ? { ...alert, acknowledged: true }
          : alert
      )
    );
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          System Monitoring Dashboard
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <FormControlLabel
            control={
              <Switch
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
            }
            label="Auto Refresh"
          />
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Interval</InputLabel>
            <Select
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(e.target.value)}
              label="Interval"
            >
              <MenuItem value={10}>10s</MenuItem>
              <MenuItem value={30}>30s</MenuItem>
              <MenuItem value={60}>1m</MenuItem>
              <MenuItem value={300}>5m</MenuItem>
            </Select>
          </FormControl>
          <IconButton>
            <Refresh />
          </IconButton>
        </Box>
      </Box>

      {/* System Metrics Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Memory color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">CPU Usage</Typography>
              </Box>
              <Typography variant="h4" color={getStatusColor(metrics.system.cpu, { warning: 70, danger: 90 })}>
                {metrics.system.cpu.toFixed(1)}%
              </Typography>
              <LinearProgress
                variant="determinate"
                value={metrics.system.cpu}
                color={getStatusColor(metrics.system.cpu, { warning: 70, danger: 90 })}
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Storage color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Memory</Typography>
              </Box>
              <Typography variant="h4" color={getStatusColor(metrics.system.memory, { warning: 75, danger: 90 })}>
                {metrics.system.memory.toFixed(1)}%
              </Typography>
              <LinearProgress
                variant="determinate"
                value={metrics.system.memory}
                color={getStatusColor(metrics.system.memory, { warning: 75, danger: 90 })}
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Speed color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Response Time</Typography>
              </Box>
              <Typography variant="h4" color={getStatusColor(metrics.api.responseTime, { warning: 200, danger: 500 })}>
                {Math.round(metrics.api.responseTime)}ms
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Avg last 5 minutes
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <NetworkCheck color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Active Users</Typography>
              </Box>
              <Typography variant="h4" color="primary">
                {metrics.api.activeConnections}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Connected now
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Performance Charts */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Performance Metrics
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={performanceData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis yAxisId="left" />
                  <YAxis yAxisId="right" orientation="right" />
                  <RechartsTooltip />
                  <Legend />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="responseTime"
                    stroke="#8884d8"
                    strokeWidth={2}
                    name="Response Time (ms)"
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="requests"
                    stroke="#82ca9d"
                    strokeWidth={2}
                    name="Requests/min"
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                System Health
              </Typography>
              <Box sx={{ space: 2 }}>
                {[
                  { label: 'API Gateway', status: 'healthy', uptime: '99.9%' },
                  { label: 'Database', status: 'healthy', uptime: '99.8%' },
                  { label: 'AI Service', status: 'warning', uptime: '98.5%' },
                  { label: 'Cache', status: 'healthy', uptime: '99.9%' }
                ].map((service, index) => (
                  <Box key={index} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', py: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <Box
                        sx={{
                          width: 10,
                          height: 10,
                          borderRadius: '50%',
                          backgroundColor: service.status === 'healthy' ? 'success.main' : 'warning.main',
                          mr: 1
                        }}
                      />
                      <Typography variant="body2">{service.label}</Typography>
                    </Box>
                    <Typography variant="body2" color="text.secondary">
                      {service.uptime}
                    </Typography>
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Alerts Section */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            System Alerts
          </Typography>
          {alerts.length === 0 ? (
            <Alert severity="success">No active alerts</Alert>
          ) : (
            <Box>
              {alerts.map((alert) => (
                <Alert
                  key={alert.id}
                  severity={alert.type}
                  action={
                    !alert.acknowledged && (
                      <Button
                        color="inherit"
                        size="small"
                        onClick={() => acknowledgeAlert(alert.id)}
                      >
                        Acknowledge
                      </Button>
                    )
                  }
                  sx={{ mb: 1 }}
                >
                  <Typography variant="subtitle2">{alert.title}</Typography>
                  <Typography variant="body2">{alert.message}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {new Date(alert.timestamp).toLocaleString()}
                  </Typography>
                </Alert>
              ))}
            </Box>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default SystemMonitoringDashboard;
