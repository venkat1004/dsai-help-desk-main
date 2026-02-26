import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Chip,
  Grid,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import ConfirmationNumberIcon from '@mui/icons-material/ConfirmationNumber';

const TicketDashboard = () => {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [filterTier, setFilterTier] = useState('All');
  const [filterStatus, setFilterStatus] = useState('All');
  const [filterPriority, setFilterPriority] = useState('All');

  // 🔥 FETCH FROM BACKEND
  useEffect(() => {
    const fetchTickets = async () => {
      try {
        setLoading(true);

        const response = await fetch("https://dsai-help-desk-main.onrender.com/api/tickets");

        if (!response.ok) {
          throw new Error("Failed to fetch tickets");
        }

        const data = await response.json();

        // Normalize backend structure
        const formattedTickets = data.tickets.map(ticket => ({
          id: ticket.ticket_id,
          title: ticket.message || "No description provided",
          priority: ticket.severity,
          tier: ticket.tier?.replace("_", " "),
          status: ticket.status,
          createdAt: new Date(ticket.created_at).toLocaleString(),
        }));

        setTickets(formattedTickets);

      } catch (err) {
        console.error(err);
        setError("Failed to load tickets");
      } finally {
        setLoading(false);
      }
    };

    fetchTickets();
  }, []);

  const filteredTickets = tickets.filter((ticket) => {
    if (filterTier !== 'All' && ticket.tier !== filterTier) return false;
    if (filterStatus !== 'All' && ticket.status !== filterStatus) return false;
    if (filterPriority !== 'All' && ticket.priority !== filterPriority) return false;
    return true;
  });

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'CRITICAL':
        return '#D32F2F';
      case 'HIGH':
        return '#FF9500';
      case 'MEDIUM':
        return '#FBC02D';
      case 'LOW':
        return '#4A7C59';
      default:
        return '#999999';
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'OPEN':
        return '#FF9500';
      case 'IN_PROGRESS':
        return '#2196F3';
      case 'RESOLVED':
        return '#4A7C59';
      default:
        return '#999999';
    }
  };

  return (
    <Box sx={{ p: 4, bgcolor: '#1a1a1a', minHeight: '100vh' }}>

      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <ConfirmationNumberIcon sx={{ fontSize: 40, color: '#D4AF37' }} />
          <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#D4AF37' }}>
            Help Desk Ticket Dashboard
          </Typography>
        </Box>
      </Box>

      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {error && (
        <Typography sx={{ color: 'red', mb: 2 }}>
          {error}
        </Typography>
      )}

      {/* Filters */}
      <Paper sx={{ p: 3, backgroundColor: '#242424', mb: 3 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <FormControl fullWidth size="small">
              <InputLabel>Tier</InputLabel>
              <Select value={filterTier} onChange={(e) => setFilterTier(e.target.value)}>
                <MenuItem value="All">All</MenuItem>
                <MenuItem value="TIER 1">TIER 1</MenuItem>
                <MenuItem value="TIER 2">TIER 2</MenuItem>
                <MenuItem value="TIER 3">TIER 3</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={4}>
            <FormControl fullWidth size="small">
              <InputLabel>Status</InputLabel>
              <Select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
                <MenuItem value="All">All</MenuItem>
                <MenuItem value="OPEN">OPEN</MenuItem>
                <MenuItem value="RESOLVED">RESOLVED</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={4}>
            <FormControl fullWidth size="small">
              <InputLabel>Priority</InputLabel>
              <Select value={filterPriority} onChange={(e) => setFilterPriority(e.target.value)}>
                <MenuItem value="All">All</MenuItem>
                <MenuItem value="CRITICAL">CRITICAL</MenuItem>
                <MenuItem value="HIGH">HIGH</MenuItem>
                <MenuItem value="MEDIUM">MEDIUM</MenuItem>
                <MenuItem value="LOW">LOW</MenuItem>
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </Paper>

      {/* Table */}
      <TableContainer component={Paper} sx={{ backgroundColor: '#242424' }}>
        <Table>
          <TableHead>
            <TableRow sx={{ backgroundColor: '#1a1a1a' }}>
              <TableCell sx={{ color: '#D4AF37' }}>Ticket ID</TableCell>
              <TableCell sx={{ color: '#D4AF37' }}>Title</TableCell>
              <TableCell sx={{ color: '#D4AF37' }}>Priority</TableCell>
              <TableCell sx={{ color: '#D4AF37' }}>Status</TableCell>
              <TableCell sx={{ color: '#D4AF37' }}>Tier</TableCell>
              <TableCell sx={{ color: '#D4AF37' }}>Created At</TableCell>
            </TableRow>
          </TableHead>

          <TableBody>
            {filteredTickets.map((ticket) => (
              <TableRow key={ticket.id}>
                <TableCell sx={{ color: '#D4AF37', fontWeight: 'bold' }}>
                  {ticket.id}
                </TableCell>

                <TableCell sx={{ color: '#ffffff' }}>
                  {ticket.title}
                </TableCell>

                <TableCell>
                  <Chip
                    label={ticket.priority}
                    size="small"
                    sx={{
                      backgroundColor: getPriorityColor(ticket.priority),
                      color: '#ffffff',
                      fontWeight: 'bold',
                    }}
                  />
                </TableCell>

                <TableCell>
                  <Chip
                    label={ticket.status}
                    size="small"
                    sx={{
                      backgroundColor: getStatusColor(ticket.status),
                      color: '#ffffff',
                      fontWeight: 'bold',
                    }}
                  />
                </TableCell>

                <TableCell sx={{ color: '#D4AF37' }}>
                  {ticket.tier}
                </TableCell>

                <TableCell sx={{ color: '#ffffff' }}>
                  {ticket.createdAt}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>

        </Table>
      </TableContainer>
    </Box>
  );
};

export default TicketDashboard;