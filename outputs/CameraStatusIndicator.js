import React from 'react';
import { Chip, Stack, Typography } from '@mui/material';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';

/**
 * CameraStatusIndicator
 *
 * Props:
 *   cameraStatuses — object: { [cameraName: string]: 'online' | 'offline' | 'error' }
 *
 * Renders one MUI Chip per camera with a colored dot and the camera name.
 * Colors: online=success (green), offline=default (grey), error=error (red).
 */

const STATUS_COLOR = {
  online:  'success',
  offline: 'default',
  error:   'error',
};

const STATUS_LABEL = {
  online:  'ONLINE',
  offline: 'OFFLINE',
  error:   'ERROR',
};

const CameraStatusIndicator = ({ cameraStatuses }) => {
  const cameras = Object.entries(cameraStatuses);

  if (cameras.length === 0) {
    return (
      <Typography variant="caption" sx={{ color: '#555' }}>
        No cameras configured.
      </Typography>
    );
  }

  return (
    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
      {cameras.map(([name, status]) => (
        <Chip
          key={name}
          icon={
            <FiberManualRecordIcon
              sx={{
                fontSize: 12,
                color:
                  status === 'online'  ? '#4caf50' :
                  status === 'error'   ? '#f44336' :
                  '#666',
              }}
            />
          }
          label={`${name} — ${STATUS_LABEL[status] ?? status.toUpperCase()}`}
          color={STATUS_COLOR[status] ?? 'default'}
          variant="outlined"
          size="small"
          sx={{
            fontFamily: '"Roboto Mono", monospace',
            fontSize: '0.7rem',
            letterSpacing: 0.5,
          }}
        />
      ))}
    </Stack>
  );
};

export default CameraStatusIndicator;
