# Backend-Frontend Integration Guide

This guide explains how to integrate the Albedo backend API with the frontend.

## Quick Start

### 1. Start the Backend Server

**Option A: Using the start script (recommended)**
```bash
python start_backend.py
```

**Option B: Direct Python execution**
```bash
python src/leed_rag_api.py
```

**Option C: Using Flask directly**
```bash
cd src
flask run --host=0.0.0.0 --port=5000
```

The backend will start on `http://localhost:5000`

### 2. Open the Frontend

**Local Development:**
- Simply open `demo_landing_page/index.html` in your browser
- Or use a local server:
  ```bash
  cd demo_landing_page
  python -m http.server 8000
  ```
- Then open `http://localhost:8000`

**GitHub Pages:**
- The frontend is already deployed at: https://aritrode29.github.io/Albedo/
- Update `config.js` with your backend URL (see Production Deployment below)

## API Endpoints

The backend provides these endpoints:

### `GET /api/status`
Check API health and status
```json
{
  "status": "healthy",
  "chunks_loaded": 1234,
  "system_ready": true,
  "available_sources": ["credits", "guide", "forms"]
}
```

### `POST /api/query`
Query the LEED knowledge base
```json
{
  "query": "What are energy efficiency requirements?",
  "limit": 3,
  "sources": ["credits", "guide"]  // optional
}
```

### `GET /api/credits`
Get list of available LEED credits
```json
{
  "credits": [
    {
      "code": "EA-Credit-1",
      "name": "Optimize Energy Performance",
      "type": "Credit",
      "points_min": 1,
      "points_max": 20
    }
  ],
  "total_count": 50
}
```

### `POST /api/analyze`
Analyze a document against LEED requirements
```json
{
  "document_text": "Project description...",
  "project_type": "NC",
  "target_credits": ["EA", "WE", "SS"]
}
```

## Configuration

### Frontend Configuration

Edit `demo_landing_page/config.js` to configure the API URL:

```javascript
window.ALBEDO_CONFIG = {
  api: {
    local: 'http://localhost:5000',           // Local development
    production: 'https://your-backend.com',  // Production backend URL
    autoDetect: true                          // Auto-detect environment
  }
};
```

### Backend Configuration

The backend uses environment variables:

```bash
# Set port (default: 5000)
export PORT=5000

# Enable debug mode
export DEBUG=true

# Run the server
python src/leed_rag_api.py
```

## Production Deployment

### Deploy Backend to Cloud

**Option 1: Heroku**
```bash
# Create Procfile
echo "web: python src/leed_rag_api.py" > Procfile

# Deploy
git push heroku main
```

**Option 2: Railway**
```bash
railway up
```

**Option 3: Render**
- Connect your GitHub repository
- Set build command: `pip install -r requirements.txt`
- Set start command: `python src/leed_rag_api.py`
- Set PORT environment variable

### Update Frontend Config

Once your backend is deployed, update `demo_landing_page/config.js`:

```javascript
production: 'https://your-backend.herokuapp.com'
```

Then push to GitHub Pages - the frontend will automatically use the production URL.

## CORS Configuration

The backend already has CORS enabled:

```python
from flask_cors import CORS
app = Flask(__name__)
CORS(app)  # Allows all origins
```

For production, you may want to restrict CORS:

```python
CORS(app, origins=["https://aritrode29.github.io"])
```

## Testing the Integration

1. **Start the backend:**
   ```bash
   python start_backend.py
   ```

2. **Open the frontend:**
   - Local: Open `demo_landing_page/index.html`
   - Or: Visit https://aritrode29.github.io/Albedo/

3. **Test the chatbot:**
   - Type: "List all credits"
   - Upload a document and ask: "Analyze this document"
   - Ask: "What are energy efficiency requirements?"

## Troubleshooting

### Backend not connecting

1. **Check if backend is running:**
   ```bash
   curl http://localhost:5000/api/status
   ```

2. **Check browser console:**
   - Open DevTools (F12)
   - Look for CORS errors or connection errors

3. **Verify API URL:**
   - Check `config.js` for correct URL
   - Check browser console for logged API URL

### CORS Errors

If you see CORS errors:
- Make sure `flask-cors` is installed: `pip install flask-cors`
- Verify CORS is enabled in `src/leed_rag_api.py`
- Check that backend allows your frontend origin

### Models Not Found

If backend says "RAG system not loaded":
```bash
# Build the RAG models first
python src/deploy_rag_system.py
```

### Port Already in Use

If port 5000 is busy:
```bash
# Use a different port
export PORT=5001
python src/leed_rag_api.py
```

Then update `config.js`:
```javascript
local: 'http://localhost:5001'
```

## Development Workflow

1. **Terminal 1 - Backend:**
   ```bash
   python start_backend.py
   ```

2. **Terminal 2 - Frontend (if using local server):**
   ```bash
   cd demo_landing_page
   python -m http.server 8000
   ```

3. **Browser:**
   - Open `http://localhost:8000`
   - Make changes to frontend files
   - Refresh browser to see changes
   - Backend changes require restart

## File Structure

```
project/
├── src/
│   └── leed_rag_api.py          # Backend API server
├── demo_landing_page/
│   ├── index.html                # Frontend HTML
│   ├── styles.css               # Frontend styles
│   ├── script.js                 # Frontend JavaScript
│   └── config.js                 # Frontend configuration
├── start_backend.py              # Backend startup script
└── BACKEND_INTEGRATION.md        # This file
```

## Next Steps

1. ✅ Backend and frontend are integrated
2. 🔄 Deploy backend to cloud (Heroku/Railway/Render)
3. 🔄 Update `config.js` with production URL
4. 🔄 Push frontend changes to GitHub Pages
5. 🎉 Your full-stack app is live!

## Support

- **Backend Issues**: Check `src/leed_rag_api.py` logs
- **Frontend Issues**: Check browser console (F12)
- **API Docs**: Visit `http://localhost:5000/` when backend is running

