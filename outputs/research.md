# Research Report
## Background
The goal is to develop a React application for industrial vision inspection using Keyence cameras. The application will include components like TriggerButtons, CameraStatusIndicator, and ImageGallery. It must communicate with an API at `http://localhost:8080/api/trigger`, manage state for camera statuses and images captured per trigger event, and use MUI v5 (Material-UI) components.
## Best Practices
1. **Component Separation:** Break the application into discrete React components to enhance maintainability.
2. **State Management:** Use React's useState hook for managing component states such as camera status and image data arrays.
3. **Error Handling:** Implement proper error handling mechanisms, particularly for network requests made via `fetch()`.
## Tools & References
1. **MUI v5 Components:**
   - **Button:** https://mui.com/material-ui/api/button/
   - **CircularProgress:** https://mui.com/material-ui/api/circular-progress/
   - **Chip:** https://mui.com/material-ui/api/chip/
   - **ImageList:** https://mui.com/material-ui/react-image-list/
2. **API Documentation:** Directly test or consult documentation for the `http://localhost:8080/api/trigger` endpoint to know the structure of returned data.
3. **Base64 Encoding Reference:** GeeksforGeeks - Base64 Encoding Guide (https://www.geeksforgeeks.org/base64-encoding-how-to-use-it/)
## Pitfalls
1. **Incorrect MUI v5 Imports:** Ensure to import from `@mui/material` instead of the deprecated `@material-ui/core`.
2. **API Endpoint Unavailability:** Setup local testing or mock data if direct API calls are not possible.
3. **Image Data Handling:** Properly handle and decode base64 strings returned by the API.
## Summary
- Ensure proper state management using React hooks for camera status and images captured per trigger event.
- Implement loading spinners during API requests with MUI v5 components.
- Use appropriate MUI v5 components for buttons, status indicators, and image galleries.
- Test API response structure directly or use mock data if unavailable.