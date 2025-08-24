import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  List,
  ListItem,
  ListItemText,
  Grid,
  Card,
  CardContent,
} from '@mui/material';
import {
  Add as AddIcon,
  FilterList as FilterIcon,
} from '@mui/icons-material';
import axios from 'axios';
import { format } from 'date-fns';

const LogsManager = () => {
  const [logs, setLogs] = useState([]);
  const [filteredLogs, setFilteredLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [openDialog, setOpenDialog] = useState(false);
  const [summary, setSummary] = useState(null);
  const [filters, setFilters] = useState({
    status: '',
    category: '',
    priority: '',
    hours: 24,
  });

  const [newLog, setNewLog] = useState({
    title: '',
    description: '',
    log_type: 'inquiry',
    priority: 'medium',
    category: '',
  });

  useEffect(() => {
    loadLogs();
    loadSummary();
  }, [filters]);

  const loadLogs = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.status) params.append('status', filters.status);
      if (filters.category) params.append('category', filters.category);
      if (filters.priority) params.append('priority', filters.priority);
      params.append('hours', filters.hours);

      const response = await axios.get(`/api/v1/logs/logs?${params}`);
      setLogs(response.data);
      setFilteredLogs(response.data);
    } catch (error) {
      console.error('Failed to load logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadSummary = async () => {
    try {
      const response = await axios.get(`/api/v1/logs/logs/summary?hours=${filters.hours}`);
      setSummary(response.data);
    } catch (error) {
      console.error('Failed to load summary:', error);
    }
  };

  const createLog = async () => {
    try {
      const response = await axios.post('/api/v1/logs/logs', newLog);
      setLogs([response.data, ...logs]);
      setFilteredLogs([response.data, ...filteredLogs]);
      setOpenDialog(false);
      setNewLog({
        title: '',
        description: '',
        log_type: 'inquiry',
        priority: 'medium',
        category: '',
      });
      loadSummary();
    } catch (error) {
      console.error('Failed to create log:', error);
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      open: 'warning',
      in_progress: 'info',
      resolved: 'success',
      closed: 'default',
    };
    return colors[status] || 'default';
  };

  const getPriorityColor = (priority) => {
    const colors = {
      urgent: 'error',
      high: 'warning',
      medium: 'info',
      low: 'success',
    };
    return colors[priority] || 'default';
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Customer Logs</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setOpenDialog(true)}
        >
          New Log
        </Button>
      </Box>

      {/* Summary Cards */}
      {summary && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6">{summary.total_logs}</Typography>
                <Typography variant="body2" color="textSecondary">
                  Total Logs ({summary.timeframe_hours}h)
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6">
                  {summary.status_breakdown?.open || 0}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  Open Issues
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6">
                  {summary.priority_breakdown?.urgent || 0}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  Urgent Priority
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6">
                  {summary.status_breakdown?.resolved || 0}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  Resolved
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          <FilterIcon sx={{ mr: 1 }} />
          Filters
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={2}>
            <FormControl fullWidth>
              <InputLabel>Status</InputLabel>
              <Select
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                label="Status"
              >
                <MenuItem value="">All</MenuItem>
                <MenuItem value="open">Open</MenuItem>
                <MenuItem value="in_progress">In Progress</MenuItem>
                <MenuItem value="resolved">Resolved</MenuItem>
                <MenuItem value="closed">Closed</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={6} md={2}>
            <FormControl fullWidth>
              <InputLabel>Priority</InputLabel>
              <Select
                value={filters.priority}
                onChange={(e) => setFilters({ ...filters, priority: e.target.value })}
                label="Priority"
              >
                <MenuItem value="">All</MenuItem>
                <MenuItem value="urgent">Urgent</MenuItem>
                <MenuItem value="high">High</MenuItem>
                <MenuItem value="medium">Medium</MenuItem>
                <MenuItem value="low">Low</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={6} md={2}>
            <FormControl fullWidth>
              <InputLabel>Category</InputLabel>
              <Select
                value={filters.category}
                onChange={(e) => setFilters({ ...filters, category: e.target.value })}
                label="Category"
              >
                <MenuItem value="">All</MenuItem>
                <MenuItem value="technical">Technical</MenuItem>
                <MenuItem value="billing">Billing</MenuItem>
                <MenuItem value="account">Account</MenuItem>
                <MenuItem value="product">Product</MenuItem>
                <MenuItem value="general">General</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={6} md={2}>
            <FormControl fullWidth>
              <InputLabel>Timeframe</InputLabel>
              <Select
                value={filters.hours}
                onChange={(e) => setFilters({ ...filters, hours: e.target.value })}
                label="Timeframe"
              >
                <MenuItem value={1}>Last Hour</MenuItem>
                <MenuItem value={24}>Last 24 Hours</MenuItem>
                <MenuItem value={168}>Last Week</MenuItem>
                <MenuItem value={720}>Last Month</MenuItem>
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </Paper>

      {/* Logs List */}
      <Paper>
        <List>
          {filteredLogs.map((log) => (
            <ListItem key={log.id} sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <ListItemText
                primary={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="subtitle1">{log.title}</Typography>
                    <Chip
                      label={log.status}
                      size="small"
                      color={getStatusColor(log.status)}
                    />
                    <Chip
                      label={log.priority}
                      size="small"
                      color={getPriorityColor(log.priority)}
                    />
                    {log.category && (
                      <Chip label={log.category} size="small" variant="outlined" />
                    )}
                  </Box>
                }
                secondary={
                  <Box>
                    <Typography variant="body2" sx={{ mt: 1 }}>
                      {log.description}
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      Created: {format(new Date(log.created_at), 'MMM dd, yyyy HH:mm')}
                    </Typography>
                  </Box>
                }
              />
            </ListItem>
          ))}
          {filteredLogs.length === 0 && (
            <ListItem>
              <ListItemText
                primary="No logs found"
                secondary="Try adjusting your filters or create a new log entry"
              />
            </ListItem>
          )}
        </List>
      </Paper>

      {/* Create Log Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Create New Log Entry</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Title"
            value={newLog.title}
            onChange={(e) => setNewLog({ ...newLog, title: e.target.value })}
            margin="normal"
            required
          />
          <TextField
            fullWidth
            label="Description"
            value={newLog.description}
            onChange={(e) => setNewLog({ ...newLog, description: e.target.value })}
            margin="normal"
            multiline
            rows={4}
          />
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={4}>
              <FormControl fullWidth>
                <InputLabel>Type</InputLabel>
                <Select
                  value={newLog.log_type}
                  onChange={(e) => setNewLog({ ...newLog, log_type: e.target.value })}
                  label="Type"
                >
                  <MenuItem value="inquiry">Inquiry</MenuItem>
                  <MenuItem value="complaint">Complaint</MenuItem>
                  <MenuItem value="support">Support</MenuItem>
                  <MenuItem value="feedback">Feedback</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={4}>
              <FormControl fullWidth>
                <InputLabel>Priority</InputLabel>
                <Select
                  value={newLog.priority}
                  onChange={(e) => setNewLog({ ...newLog, priority: e.target.value })}
                  label="Priority"
                >
                  <MenuItem value="low">Low</MenuItem>
                  <MenuItem value="medium">Medium</MenuItem>
                  <MenuItem value="high">High</MenuItem>
                  <MenuItem value="urgent">Urgent</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={4}>
              <TextField
                fullWidth
                label="Category"
                value={newLog.category}
                onChange={(e) => setNewLog({ ...newLog, category: e.target.value })}
                placeholder="e.g., technical, billing"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button onClick={createLog} variant="contained">Create</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default LogsManager;
