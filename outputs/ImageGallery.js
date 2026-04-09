import React from 'react';
import {
  Box,
  Typography,
  ImageList,
  ImageListItem,
  ImageListItemBar,
  Paper,
} from '@mui/material';
import PhotoLibraryIcon from '@mui/icons-material/PhotoLibrary';

/**
 * ImageGallery
 *
 * Props:
 *   triggerName — string  label shown above the gallery (e.g. "Surface Inspection")
 *   images      — array of { data: string, timestamp: string }
 *                 data      : base64-encoded image string (no data URI prefix)
 *                 timestamp : ISO 8601 string set at capture time
 *
 * Shows "No images yet" when images array is empty.
 * Displays images in a responsive 3-column MUI ImageList with capture timestamp.
 */
const ImageGallery = ({ triggerName, images }) => {
  return (
    <Box>
      {/* Gallery header */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <PhotoLibraryIcon sx={{ color: '#555', fontSize: 18 }} />
        <Typography
          variant="overline"
          sx={{ color: '#aaa', letterSpacing: 2, lineHeight: 1 }}
        >
          {triggerName}
        </Typography>
        <Typography variant="caption" sx={{ color: '#555', ml: 1 }}>
          ({images.length} image{images.length !== 1 ? 's' : ''})
        </Typography>
      </Box>

      {images.length === 0 ? (
        <Paper
          variant="outlined"
          sx={{
            p: 3,
            textAlign: 'center',
            borderColor: '#2a2a2a',
            bgcolor: '#111',
            color: '#444',
          }}
        >
          <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
            No images yet — press trigger to capture
          </Typography>
        </Paper>
      ) : (
        <ImageList
          cols={3}
          gap={8}
          sx={{ maxHeight: 340, overflowY: 'auto', bgcolor: '#111', p: 1, borderRadius: 1 }}
        >
          {images.map((image, index) => {
            // Format timestamp for display: "HH:MM:SS · YYYY-MM-DD"
            const dt = new Date(image.timestamp);
            const timeLabel = isNaN(dt)
              ? image.timestamp
              : `${dt.toLocaleTimeString()} · ${dt.toLocaleDateString()}`;

            return (
              <ImageListItem key={`${triggerName}-${index}`}>
                <img
                  src={`data:image/png;base64,${image.data}`}
                  alt={`${triggerName} capture ${index + 1}`}
                  loading="lazy"
                  style={{ width: '100%', height: 160, objectFit: 'cover', display: 'block' }}
                />
                <ImageListItemBar
                  title={`#${index + 1}`}
                  subtitle={timeLabel}
                  sx={{
                    '& .MuiImageListItemBar-title': { fontSize: '0.7rem' },
                    '& .MuiImageListItemBar-subtitle': {
                      fontSize: '0.6rem',
                      fontFamily: 'monospace',
                    },
                  }}
                />
              </ImageListItem>
            );
          })}
        </ImageList>
      )}
    </Box>
  );
};

export default ImageGallery;
