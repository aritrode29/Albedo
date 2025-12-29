// Albedo Frontend Configuration
// This file allows easy configuration of the API endpoint

window.ALBEDO_CONFIG = {
  // API Configuration
  api: {
    // Local development URL
    local: 'http://localhost:5000',
    
    // Production URL - Update this with your deployed backend URL
    // Examples:
    // - Heroku: 'https://your-app.herokuapp.com'
    // - Railway: 'https://your-app.railway.app'
    // - Render: 'https://your-app.onrender.com'
    // - Custom domain: 'https://api.yourdomain.com'
    production: window.ALBEDO_API_URL || 'http://localhost:5000',
    
    // Auto-detect: uses local for localhost, production otherwise
    autoDetect: true
  },
  
  // Feature flags
  features: {
    enableFileUpload: true,
    enableDocumentAnalysis: true,
    enableCreditLookup: true,
    showApiStatus: true
  },
  
  // UI Configuration
  ui: {
    maxFileSize: 5 * 1024 * 1024, // 5MB
    typingDelay: 500, // ms
    animationDuration: 300 // ms
  }
};

// Helper function to get API URL
window.getApiUrl = function() {
  const config = window.ALBEDO_CONFIG;
  if (config.api.autoDetect) {
    const isLocal = window.location.hostname === 'localhost' || 
                   window.location.hostname === '127.0.0.1' ||
                   window.location.hostname === '';
    return isLocal ? config.api.local : config.api.production;
  }
  return config.api.production;
};





