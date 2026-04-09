import React from 'react';
import { Button, CircularProgress, Stack } from '@mui/material';
import CameraAltIcon from '@mui/icons-material/CameraAlt';

/**
 * TriggerButtons
 *
 * Props:
 *   triggers  — array of { id: string, label: string }
 *   loading   — object keyed by trigger id: { surfaceInspection: bool, ... }
 *   onTrigger — (programId: string) => void  called on button press
 *
 * Each button disables and shows a spinner while its trigger is in-flight.
 * Buttons are independent — pressing one does not block the others.
 */
const TriggerButtons = ({ triggers, loading, onTrigger }) => {
  return (
    <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap>
      {triggers.map(({ id, label }) => {
        const isLoading = Boolean(loading[id]);
        return (
          <Button
            key={id}
            variant="contained"
            color="primary"
            size="large"
            disabled={isLoading}
            onClick={() => onTrigger(id)}
            startIcon={
              isLoading
                ? <CircularProgress size={18} color="inherit" />
                : <CameraAltIcon />
            }
            sx={{
              minWidth: 200,
              fontFamily: '"Roboto Mono", monospace',
              fontWeight: 600,
              letterSpacing: 1,
              bgcolor: isLoading ? '#1a3a5c' : undefined,
            }}
          >
            {isLoading ? 'Triggering…' : label}
          </Button>
        );
      })}
    </Stack>
  );
};

export default TriggerButtons;
