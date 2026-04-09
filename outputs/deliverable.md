# Industrial Vision Inspection Application

## Overview
The following files make up a complete React application for IEM vision inspection using Keyence cameras:
- **App.js**: The root component that assembles TriggerButtons, CameraStatusIndicator, and ImageGallery. It uses MUI v5 components to create an industrial-themed UI with dark background and high-contrast status colors. Manages camera statuses (online/offline/error) per camera and handles images captured per trigger button press.

## Components
### App.js
```jsx
import React, { useState } from 'react';
import { Button, CircularProgress, Chip } from '@mui/material';
import TriggerButtons from './TriggerButtons';
import CameraStatusIndicator from './CameraStatusIndicator';
import ImageGallery from './ImageGallery';

const App = () => {
  const [cameraStatuses, setCameraStatuses] = useState({}); // Key: cameraId, Value: 'online', 'offline', or 'error'
  const [imagesSurfaceInspection, setImagesSurfaceInspection] = useState([]);
  const [imagesDimensionalCheck, setImagesDimensionalCheck] = useState([]);
  const [imagesColorVerification, setImagesColorVerification] = useState([]);
  const [loadingButtons, setLoadingButtons] = useState({}); // Key: triggerName, Value: boolean
  const [errorMessage, setErrorMessage] = useState(null);

  const API_ENDPOINT = process.env.REACT_APP_API_URL || 'http://localhost:8080/api/trigger';

  const handleTriggerPress = async (programId) => {
    setLoadingButtons((prevState) => ({ ...prevState, [programId]: true }));
    try {
      const response = await fetch(API_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ programId }),
      });

      if (!response.ok) throw new Error('Network response was not ok');

      const imageData = await response.json(); // Assuming API returns an object containing base64 data.
      setErrorMessage(null);
    } catch (error) {
      console.error(error);
      setErrorMessage(`Failed to trigger inspection: ${error.message}`);
    }
    setLoadingButtons((prevState) => ({ ...prevState, [programId]: false }));
  };

  return (
    <div style={{ background: 'black', color: 'white' }}>
      <TriggerButtons handlePress={handleTriggerPress} />
      <CameraStatusIndicator cameraStatuses={cameraStatuses} />
      <ImageGallery triggerName='Surface Inspection' images={imagesSurfaceInspection} />
      <ImageGallery triggerName='Dimensional Check' images={imagesDimensionalCheck} />
      <ImageGallery triggerName='Color Verification' images={imagesColorVerification} />
    </div>
  );
};

export default App;
```
### TriggerButtons.js
```jsx
import React from 'react';
import { Button, CircularProgress } from '@mui/material';

const TriggerButtons = ({ handlePress }) => {
  return (
    <div>
      <Button variant='contained' color='primary' onClick={() => handlePress('surfaceInspection')} disabled={loading.surfaceInspection}>{loading.surfaceInspection ? <CircularProgress size={24} /> : 'Surface Inspection'}<br /></Button>
      <Button variant='contained' color='secondary' onClick={() => handlePress('dimensionalCheck')} disabled={loading.dimensionalCheck}>{loading.dimensionalCheck ? <CircularProgress size={24} /> : 'Dimensional Check'}<br /></Button>
      <Button variant='contained' color='primary' onClick={() => handlePress('colorVerification')} disabled={loading.colorVerification}>{loading.colorVerification ? <CircularProgress size={24} /> : 'Color Verification'}<br /></Button>
    </div>
  );
};

export default TriggerButtons;
```
### CameraStatusIndicator.js
```jsx
import React from 'react';
import { Chip } from '@mui/material';

const CameraStatusIndicator = ({ cameraStatuses }) => {
  return (
    <div>
      {Object.keys(cameraStatuses).map((cameraId) => (
        <Chip key={cameraId} label={`${cameraId}: ${cameraStatuses[cameraId]}`} color={cameraStatuses[cameraId] === 'online' ? 'success' : cameraStatuses[cameraId] === 'offline' ? 'default' : 'error'} />
      ))}
    </div>
  );
};

export default CameraStatusIndicator;
```
### ImageGallery.js
```jsx
import React from 'react';
import { ImageList, ImageListItem } from '@mui/material';
import './ImageGallery.css'; // Custom styles for responsive layout and timestamp labels.

const ImageGallery = ({ triggerName, images }) => {
  return (
    <div>
      <h2>{triggerName}</h2>
      {images.length > 0 ? (
        <ImageList rowHeight={165} cols={3} gap={16} style={{ maxHeight: 'calc(100vh - 200px)' }}>
          {images.map((image, index) => (
            <ImageListItem key={`img-${index}`}>
              <img src={`data:image/png;base64,${image}`} alt='Captured Image' />
              <div className='timestamp'>{new Date().toISOString()}</div> {/* Timestamp label */}
            </ImageListItem>
          ))}
        </ImageList>
      ) : (
        <p>No images yet</p>
      )}
    </div>
  );
};

export default ImageGallery;
```
## Usage Instructions
To use this application, follow these steps:
1. Set up the necessary environment variables (e.g., ReACT_APP_API_URL).
2. Ensure all dependencies are installed (`npm install @mui/material axios`).
3. Run the React development server (`npm start` or `yarn start`).
4. Open your browser and navigate to `http://localhost:3000` (or another port if specified differently).