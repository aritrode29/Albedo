# Quick Start Guide - Backend & Frontend Integration

## 🚀 Start Everything in 2 Steps

### Option 1: Local Development (Backend only accessible locally)

**Step 1: Start Backend**
```bash
python start_backend.py
```
Backend runs on: `http://localhost:5000`

**Step 2: Open Frontend**
Open `demo_landing_page/index.html` directly in browser
Or use local server:
```bash
cd demo_landing_page
python -m http.server 8000
```

### Option 2: Public Access with ngrok (For demos/sharing)

**Step 1: Start Backend + ngrok**
```bash
python start_with_ngrok.py
```
This will:
- Start your backend
- Create public ngrok URL
- Show you the URL to use

**Step 2: Update Config (if needed)**
The script tries to auto-update, but if not:
```bash
python update_ngrok_url.py
```

**Step 3: Open Frontend**
Open `demo_landing_page/index.html` or visit: https://aritrode29.github.io/Albedo/

## ✅ Verify It Works

1. **Check Backend:**
   - Open: http://localhost:5000/api/status
   - Should see: `{"status": "healthy", ...}`

2. **Test Frontend:**
   - Open the frontend page
   - Type in chatbot: "List all credits"
   - Should get a list of LEED credits

## 🔧 Configuration

### Change API URL

Edit `demo_landing_page/config.js`:
```javascript
production: 'https://your-backend-url.com'
```

### Change Backend Port

```bash
export PORT=5001
python start_backend.py
```

Then update `config.js`:
```javascript
local: 'http://localhost:5001'
```

## 📚 Full Documentation

See `BACKEND_INTEGRATION.md` for complete integration guide.

## 🐛 Troubleshooting

**Backend won't start?**
- Check if port 5000 is in use
- Make sure models exist: `ls models/*.faiss`
- Install dependencies: `pip install -r requirements.txt`

**Frontend can't connect?**
- Check browser console (F12) for errors
- Verify backend is running: `curl http://localhost:5000/api/status`
- Check `config.js` has correct URL

**CORS errors?**
- Backend already has CORS enabled
- Make sure `flask-cors` is installed: `pip install flask-cors`

## 🎯 Next Steps

1. ✅ Backend and frontend are integrated
2. 🔄 Test all features (upload, query, analyze)
3. 🔄 Deploy backend to cloud (optional)
4. 🔄 Update production URL in config.js
5. 🎉 Enjoy your integrated app!

