# ngrok Setup Guide for Albedo Backend

This guide shows you how to expose your local backend to the internet using ngrok - perfect for academic demos!

## 🎯 Why ngrok?

- ✅ **Free** - Perfect for academic projects
- ✅ **Quick Setup** - 5 minutes to get started
- ✅ **Public URL** - Share your backend with anyone
- ✅ **HTTPS** - Secure connection included
- ✅ **No Deployment** - Run everything locally

## 📥 Step 1: Install ngrok

### Windows:

1. **Download ngrok:**
   - Go to: https://ngrok.com/download
   - Download the Windows version (ZIP file)

2. **Extract ngrok:**
   - Extract `ngrok.exe` to a folder (e.g., `C:\ngrok\`)
   - Or extract to your project folder

3. **Add to PATH (optional but recommended):**
   - Add ngrok folder to your Windows PATH
   - Or just use full path: `C:\ngrok\ngrok.exe`

### Mac/Linux:

```bash
# Using Homebrew (Mac)
brew install ngrok/ngrok/ngrok

# Or download from https://ngrok.com/download
```

## 🔑 Step 2: Sign Up & Get Auth Token

1. **Sign up for free account:**
   - Go to: https://dashboard.ngrok.com/signup
   - Use your email (GitHub, Google, or email)

2. **Get your authtoken:**
   - After signup, go to: https://dashboard.ngrok.com/get-started/your-authtoken
   - Copy your authtoken

3. **Configure ngrok:**
   ```bash
   ngrok config add-authtoken YOUR_AUTH_TOKEN_HERE
   ```

## 🚀 Step 3: Start Backend with ngrok

### Option A: Using the Helper Script (Recommended)

```bash
python start_with_ngrok.py
```

This script will:
- ✅ Check if ngrok is installed
- ✅ Start your Flask backend
- ✅ Start ngrok tunnel
- ✅ Show you the public URL
- ✅ Optionally update config.js

### Option B: Manual Setup

**Terminal 1 - Start Backend:**
```bash
python start_backend.py
# Or: python src/leed_rag_api.py
```

**Terminal 2 - Start ngrok:**
```bash
ngrok http 5000
```

You'll see output like:
```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:5000
```

Copy the `https://` URL - that's your public backend URL!

## 🔧 Step 4: Update Frontend Config

Edit `demo_landing_page/config.js`:

```javascript
production: 'https://abc123.ngrok-free.app'  // Your ngrok URL
```

**Important:** ngrok URLs change each time you restart ngrok (unless you have a paid plan). You'll need to update this each time.

## 🌐 Step 5: Test Your Setup

1. **Check backend is running:**
   ```bash
   curl http://localhost:5000/api/status
   ```

2. **Check ngrok tunnel:**
   - Open: http://localhost:4040 (ngrok dashboard)
   - You'll see all requests there

3. **Test public URL:**
   ```bash
   curl https://your-ngrok-url.ngrok-free.app/api/status
   ```

4. **Open frontend:**
   - Open `demo_landing_page/index.html`
   - Or visit: https://aritrode29.github.io/Albedo/
   - Try the chatbot - it should connect!

## 📋 Quick Reference

### Start Everything:
```bash
python start_with_ngrok.py
```

### Manual Start:
```bash
# Terminal 1
python src/leed_rag_api.py

# Terminal 2
ngrok http 5000
```

### Get ngrok URL:
- Check terminal output
- Or visit: http://localhost:4040

### Stop Everything:
- Press `Ctrl+C` in both terminals
- Or close the terminal windows

## ⚠️ Important Notes

### ngrok Limitations (Free Tier):

1. **URL Changes:** Your URL changes each restart
   - Solution: Update `config.js` each time
   - Or use ngrok paid plan for static domains

2. **Connection Limits:** 40 connections/minute
   - Usually fine for demos
   - If exceeded, wait 1 minute

3. **Session Timeout:** 2 hours
   - After 2 hours, ngrok stops
   - Just restart: `python start_with_ngrok.py`

4. **Warning Page:** First visit shows ngrok warning
   - Click "Visit Site" to continue
   - This is normal for free tier

### Tips:

- ✅ Keep terminal windows open while demoing
- ✅ Use ngrok dashboard (localhost:4040) to monitor requests
- ✅ For permanent URL, consider deploying to Render
- ✅ Test locally first before sharing ngrok URL

## 🐛 Troubleshooting

### "ngrok: command not found"
- Make sure ngrok is installed
- Check PATH or use full path to ngrok.exe
- Windows: Try `.\ngrok.exe` if in same folder

### "authtoken required"
- Run: `ngrok config add-authtoken YOUR_TOKEN`
- Get token from: https://dashboard.ngrok.com/get-started/your-authtoken

### "port 5000 already in use"
- Stop other Flask servers
- Or use different port: `ngrok http 5001`
- Update backend port: `export PORT=5001`

### "Backend not connecting"
- Check backend is running: `curl http://localhost:5000/api/status`
- Check ngrok is running: Visit http://localhost:4040
- Verify ngrok URL in config.js matches terminal output

### CORS Errors
- Backend already has CORS enabled
- Make sure backend is running
- Check ngrok URL is correct

## 🎓 For Academic Demos

### Best Practices:

1. **Before Demo:**
   - Start backend + ngrok: `python start_with_ngrok.py`
   - Test connection: Visit ngrok URL + `/api/status`
   - Update config.js with ngrok URL
   - Push config.js to GitHub (if using GitHub Pages)

2. **During Demo:**
   - Keep terminal windows visible (or minimized)
   - Have ngrok dashboard open: http://localhost:4040
   - Monitor requests in real-time

3. **After Demo:**
   - Stop services (Ctrl+C)
   - Note: ngrok URL won't work after stopping

## 🚀 Next Steps

Once you're comfortable with ngrok:

1. **For Permanent URL:** Deploy to Render (free tier)
2. **For Production:** Use Railway or Fly.io
3. **For Static Domain:** Upgrade ngrok plan ($8/month)

## 📚 Resources

- **ngrok Docs:** https://ngrok.com/docs
- **ngrok Dashboard:** https://dashboard.ngrok.com
- **ngrok Status:** https://status.ngrok.com

---

**Ready to start?** Run: `python start_with_ngrok.py`





