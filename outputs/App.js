import React, { useState } from 'react';
import { Box, Typography, Alert, Divider, CssBaseline } from '@mui/material';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import TriggerButtons from './TriggerButtons';
import CameraStatusIndicator from './CameraStatusIndicator';
import ImageGallery from './ImageGallery';

// ---------------------------------------------------------------------------
// Theme — dark industrial look
// ---------------------------------------------------------------------------
const theme = createTheme({
  palette: {
    mode: 'dark',
    background: { default: '#0d0d0d', paper: '#1a1a1a' },
    primary:   { main: '#1976d2' },
    secondary: { main: '#ff9800' },
    success:   { main: '#4caf50' },
    error:     { main: '#f44336' },
  },
  typography: {
    fontFamily: '"Roboto Mono", "Roboto", monospace',
  },
});

// ---------------------------------------------------------------------------
// API config — override with REACT_APP_API_URL env var
// ---------------------------------------------------------------------------
const API_ENDPOINT = process.env.REACT_APP_API_URL || 'http://localhost:8080/api/trigger';

// Maps programId → per-trigger image state key
const TRIGGERS = [
  { id: 'surfaceInspection',  label: 'Surface Inspection'  },
  { id: 'dimensionalCheck',   label: 'Dimensional Check'   },
  { id: 'colorVerification',  label: 'Color Verification'  },
];

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------
const App = () => {
  // camera status: { cameraId: 'online' | 'offline' | 'error' }
  const [cameraStatuses, setCameraStatuses] = useState({
    'Camera 1': 'online',
    'Camera 2': 'online',
    'Camera 3': 'offline',
  });

  // per-trigger image arrays: [{ data: base64String, timestamp: isoString }]
  const [images, setImages] = useState({
    surfaceInspection: [],
    dimensionalCheck:  [],
    colorVerification: [],
  });

  // loading state per trigger
  const [loading, setLoading] = useState({
    surfaceInspection: false,
    dimensionalCheck:  false,
    colorVerification: false,
  });

  const [errorMessage, setErrorMessage] = useState(null);

  // -------------------------------------------------------------------------
  // Trigger handler — POSTs programId, appends returned image to that
  // trigger's gallery. Expects API response: { image: "<base64>" }
  // -------------------------------------------------------------------------
  const handleTrigger = async (programId) => {
    setLoading((prev) => ({ ...prev, [programId]: true }));
    setErrorMessage(null);

    try {
      const response = await fetch(API_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ programId }),
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      // API must return { image: "<base64 string>" }
      if (data.image) {
        setImages((prev) => ({
          ...prev,
          [programId]: [
            ...prev[programId],
            { data: data.image, timestamp: new Date().toISOString() },
          ],
        }));
      }

      // Optionally update camera status from response
      if (data.cameraStatus) {
        setCameraStatuses((prev) => ({ ...prev, ...data.cameraStatus }));
      }
    } catch (err) {
      console.error('[App] Trigger failed:', err);
      setErrorMessage(`Trigger failed (${programId}): ${err.message}`);
    } finally {
      setLoading((prev) => ({ ...prev, [programId]: false }));
    }
  };

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ minHeight: '100vh', bgcolor: 'background.default', p: 3 }}>

        {/* Header */}
        <Typography variant="h5" sx={{ mb: 1, letterSpacing: 2, color: '#90caf9' }}>
          IEM VISION INSPECTION SYSTEM
        </Typography>
        <Typography variant="caption" sx={{ color: '#666', letterSpacing: 1 }}>
          KEYENCE CAMERA CONTROL INTERFACE
        </Typography>

        <Divider sx={{ my: 2, borderColor: '#333' }} />

        {/* Camera Status Row */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="overline" sx={{ color: '#888', display: 'block', mb: 1 }}>
            Camera Status
          </Typography>
          <CameraStatusIndicator cameraStatuses={cameraStatuses} />
        </Box>

        <Divider sx={{ my: 2, borderColor: '#333' }} />

        {/* Trigger Buttons */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="overline" sx={{ color: '#888', display: 'block', mb: 1 }}>
            Inspection Programs
          </Typography>
          <TriggerButtons
            triggers={TRIGGERS}
            loading={loading}
            onTrigger={handleTrigger}
          />
        </Box>

        {/* Error Banner */}
        {errorMessage && (
          <Alert severity="error" onClose={() => setErrorMessage(null)} sx={{ mb: 3 }}>
            {errorMessage}
          </Alert>
        )}

        <Divider sx={{ my: 2, borderColor: '#333' }} />

        {/* Per-trigger Image Galleries */}
        {TRIGGERS.map(({ id, label }) => (
          <Box key={id} sx={{ mb: 4 }}>
            <ImageGallery
              triggerName={label}
              images={images[id]}
            />
          </Box>
        ))}

      </Box>
    </ThemeProvider>
  );
};

export default App;
