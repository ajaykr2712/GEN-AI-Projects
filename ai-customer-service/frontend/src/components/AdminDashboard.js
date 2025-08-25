import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  LinearProgress,
  Alert,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Tooltip,
  CircularProgress,
  Switch,
  FormControlLabel
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Speed as SpeedIcon,
  Security as SecurityIcon,
  Chat as ChatIcon,
  People as PeopleIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Settings as SettingsIcon
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import { useAppState } from '../context/AppContext';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

function TabPanel({ children, value, index, ...other }) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`dashboard-tabpanel-${index}`}
      aria-labelledby={`dashboard-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export default function AdminDashboard() {
  const { state, services, apiService } = useAppState();
  const [tabValue, setTabValue] = useState(0);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(30000); // 30 seconds

  // Fetch dashboard data
  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [healthData, metricsData] = await Promise.all([
        services.checkSystemHealth(),
        apiService.getMetrics()
      ]);
      
      setMetrics(metricsData);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Auto-refresh effect
  useEffect(() => {
    fetchDashboardData();
    
    if (autoRefresh) {
      const interval = setInterval(fetchDashboardData, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval]);

  // System health status
  const systemHealthStatus = useMemo(() => {
    if (!state.systemHealth) return { status: 'unknown', color: 'default' };
    
    switch (state.systemHealth.status) {
      case 'healthy':
        return { status: 'Healthy', color: 'success', icon: <CheckCircleIcon /> };
      case 'degraded':
        return { status: 'Degraded', color: 'warning', icon: <WarningIcon /> };
      case 'unhealthy':
        return { status: 'Unhealthy', color: 'error', icon: <ErrorIcon /> };
      default:
        return { status: 'Unknown', color: 'default', icon: <WarningIcon /> };
    }
  }, [state.systemHealth]);

  // Mock data for demonstration (in real app, this would come from API)
  const performanceData = useMemo(() => {
    const now = new Date();
    return Array.from({ length: 24 }, (_, i) => ({
      time: new Date(now.getTime() - (23 - i) * 60 * 60 * 1000).toLocaleTimeString('en-US', { hour: '2-digit' }),
      responseTime: Math.random() * 500 + 100,
      requests: Math.floor(Math.random() * 100) + 50,
      errors: Math.floor(Math.random() * 10),
      activeUsers: Math.floor(Math.random() * 50) + 20
    }));
  }, []);

  const conversationData = useMemo(() => [
    { name: 'General Support', value: 45, color: COLORS[0] },
    { name: 'Technical Issues', value: 30, color: COLORS[1] },
    { name: 'Billing', value: 15, color: COLORS[2] },
    { name: 'Other', value: 10, color: COLORS[3] }
  ], []);

  const renderSystemOverview = () => (
    <Grid container spacing={3}>
      {/* System Health Card */}
      <Grid item xs={12} md={3}>
        <Card>
          <CardContent>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box>
                <Typography color="textSecondary" gutterBottom>
                  System Health
                </Typography>
                <Typography variant="h5" component="div">
                  {systemHealthStatus.status}
                </Typography>
              </Box>
              <Chip
                icon={systemHealthStatus.icon}
                label={systemHealthStatus.status}
                color={systemHealthStatus.color}
                variant="outlined"
              />
            </Box>
          </CardContent>
        </Card>
      </Grid>

      {/* Active Conversations */}
      <Grid item xs={12} md={3}>
        <Card>
          <CardContent>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box>
                <Typography color="textSecondary" gutterBottom>
                  Active Conversations
                </Typography>
                <Typography variant="h5" component="div">
                  {state.conversations?.length || 0}
                </Typography>
              </Box>
              <ChatIcon color="primary" sx={{ fontSize: 40 }} />
            </Box>
            <Box mt={2}>
              <Typography variant="body2" color="textSecondary">
                <TrendingUpIcon sx={{ fontSize: 16, mr: 0.5 }} />
                +12% from yesterday
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </Grid>

      {/* Response Time */}
      <Grid item xs={12} md={3}>
        <Card>
          <CardContent>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box>
                <Typography color="textSecondary" gutterBottom>
                  Avg Response Time
                </Typography>
                <Typography variant="h5" component="div">
                  {metrics?.metrics?.performance?.['request_duration.success']?.avg?.toFixed(2) || '1.2'}s
                </Typography>
              </Box>
              <SpeedIcon color="secondary" sx={{ fontSize: 40 }} />
            </Box>
            <LinearProgress 
              variant="determinate" 
              value={75} 
              sx={{ mt: 2 }}
              color="secondary"
            />
          </CardContent>
        </Card>
      </Grid>

      {/* Error Rate */}
      <Grid item xs={12} md={3}>
        <Card>
          <CardContent>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box>
                <Typography color="textSecondary" gutterBottom>
                  Error Rate
                </Typography>
                <Typography variant="h5" component="div">
                  0.5%
                </Typography>
              </Box>
              <SecurityIcon color="success" sx={{ fontSize: 40 }} />
            </Box>
            <Box mt={2}>
              <Typography variant="body2" color="success.main">
                <TrendingDownIcon sx={{ fontSize: 16, mr: 0.5 }} />
                -2% from yesterday
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </Grid>

      {/* Performance Chart */}
      <Grid item xs={12} md={8}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              System Performance (24h)
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
                  name="Requests/hour"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>

      {/* Conversation Categories */}
      <Grid item xs={12} md={4}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Conversation Categories
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={conversationData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {conversationData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <RechartsTooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );

  const renderAnalytics = () => (
    <Grid container spacing={3}>
      {/* User Analytics */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              User Activity
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={performanceData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <RechartsTooltip />
                <Area
                  type="monotone"
                  dataKey="activeUsers"
                  stroke="#8884d8"
                  fill="#8884d8"
                  fillOpacity={0.6}
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>

      {/* Error Analytics */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Error Trends
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={performanceData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <RechartsTooltip />
                <Bar dataKey="errors" fill="#ff7300" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>

      {/* Alerts Table */}
      <Grid item xs={12}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Recent Alerts
            </Typography>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Time</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Message</TableCell>
                    <TableCell>Severity</TableCell>
                    <TableCell>Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {metrics?.alerts?.slice(0, 10).map((alert, index) => (
                    <TableRow key={index}>
                      <TableCell>{new Date(alert.timestamp).toLocaleString()}</TableCell>
                      <TableCell>{alert.metric}</TableCell>
                      <TableCell>{alert.level} threshold exceeded</TableCell>
                      <TableCell>
                        <Chip
                          label={alert.level}
                          color={alert.level === 'critical' ? 'error' : 'warning'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Chip label="Active" color="error" size="small" />
                      </TableCell>
                    </TableRow>
                  )) || (
                    <TableRow>
                      <TableCell colSpan={5} align="center">
                        No alerts to display
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );

  const renderSystemStatus = () => (
    <Grid container spacing={3}>
      {/* Service Status */}
      <Grid item xs={12}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Service Health Checks
            </Typography>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Service</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Last Check</TableCell>
                    <TableCell>Response Time</TableCell>
                    <TableCell>Details</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {state.systemHealth?.checks && Object.entries(state.systemHealth.checks).map(([serviceName, check]) => (
                    <TableRow key={serviceName}>
                      <TableCell>{serviceName}</TableCell>
                      <TableCell>
                        <Chip
                          icon={check.status === 'healthy' ? <CheckCircleIcon /> : <ErrorIcon />}
                          label={check.status}
                          color={check.status === 'healthy' ? 'success' : 'error'}
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>{new Date(check.timestamp).toLocaleString()}</TableCell>
                      <TableCell>{check.duration?.toFixed(3)}s</TableCell>
                      <TableCell>
                        {check.error ? (
                          <Tooltip title={check.error}>
                            <ErrorIcon color="error" />
                          </Tooltip>
                        ) : (
                          <CheckCircleIcon color="success" />
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      </Grid>

      {/* System Metrics */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Request Metrics
            </Typography>
            {metrics?.metrics?.counters && (
              <Box>
                {Object.entries(metrics.metrics.counters).map(([key, value]) => (
                  <Box key={key} display="flex" justifyContent="space-between" mb={1}>
                    <Typography variant="body2">{key}:</Typography>
                    <Typography variant="body2" fontWeight="bold">{value}</Typography>
                  </Box>
                ))}
              </Box>
            )}
          </CardContent>
        </Card>
      </Grid>

      {/* Performance Metrics */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Performance Metrics
            </Typography>
            {metrics?.metrics?.performance && (
              <Box>
                {Object.entries(metrics.metrics.performance).map(([key, metric]) => (
                  <Box key={key} mb={2}>
                    <Typography variant="subtitle2">{key}</Typography>
                    <Box ml={2}>
                      <Typography variant="body2">Count: {metric.count}</Typography>
                      <Typography variant="body2">Average: {metric.avg?.toFixed(3)}s</Typography>
                      <Typography variant="body2">Min: {metric.min?.toFixed(3)}s</Typography>
                      <Typography variant="body2">Max: {metric.max?.toFixed(3)}s</Typography>
                    </Box>
                  </Box>
                ))}
              </Box>
            )}
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );

  return (
    <Box sx={{ width: '100%' }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          System Dashboard
        </Typography>
        <Box display="flex" alignItems="center" gap={2}>
          <FormControlLabel
            control={
              <Switch
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
            }
            label="Auto Refresh"
          />
          <Button
            variant="outlined"
            startIcon={loading ? <CircularProgress size={16} /> : <RefreshIcon />}
            onClick={fetchDashboardData}
            disabled={loading}
          >
            Refresh
          </Button>
          <IconButton>
            <SettingsIcon />
          </IconButton>
        </Box>
      </Box>

      {/* Connection Status Alert */}
      {!state.isConnected && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          Connection lost. Some data may be outdated.
        </Alert>
      )}

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tabValue} onChange={(e, newValue) => setTabValue(newValue)}>
          <Tab label="Overview" />
          <Tab label="Analytics" />
          <Tab label="System Status" />
        </Tabs>
      </Box>

      {/* Tab Panels */}
      <TabPanel value={tabValue} index={0}>
        {renderSystemOverview()}
      </TabPanel>
      <TabPanel value={tabValue} index={1}>
        {renderAnalytics()}
      </TabPanel>
      <TabPanel value={tabValue} index={2}>
        {renderSystemStatus()}
      </TabPanel>
    </Box>
  );
}
