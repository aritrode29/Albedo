# GitHub Pages Setup for Albedo

## Repository: aritrode29/Albedo

Your site will be live at: **https://aritrode29.github.io/Albedo/**

## Quick Setup Steps

### 1. Enable GitHub Pages

1. Go to: https://github.com/aritrode29/Albedo/settings/pages
2. Under "Source", you'll see workflow options:
   - **Select "Static HTML"** (the one that says "Deploy static files in a repository without a build")
   - Click on it to use this workflow
3. The workflow will automatically detect and use `.github/workflows/deploy-pages.yml`

**OR** if you see a dropdown:

1. Click the dropdown under "Source"
2. Select **"GitHub Actions"**
3. Choose **"Static HTML"** workflow
4. Click **Save**

### 2. Push Your Code

```bash
git add .
git commit -m "Setup GitHub Pages deployment"
git push origin main
```

### 3. Monitor Deployment

1. Go to: https://github.com/aritrode29/Albedo/actions
2. You'll see the "Deploy Static HTML to GitHub Pages" workflow running
3. Wait for it to complete (usually takes 1-2 minutes)
4. Once complete, your site is live!

### 4. Access Your Site

Visit: **https://aritrode29.github.io/Albedo/**

## What Gets Deployed

The workflow automatically deploys the `demo_landing_page/` folder, which includes:
- `index.html` - Main landing page
- `styles.css` - All styling
- `script.js` - Interactive features
- `.nojekyll` - Ensures proper file serving

## Troubleshooting

### Site Not Showing Up?

1. **Check Actions Tab**: https://github.com/aritrode29/Albedo/actions
   - Look for any failed workflows
   - Check the logs for errors

2. **Verify Settings**: https://github.com/aritrode29/Albedo/settings/pages
   - Ensure "Source" shows "Static HTML" or "GitHub Actions"
   - If it says "None", select "Static HTML" workflow

3. **Wait a Few Minutes**
   - First deployment can take 2-5 minutes
   - Subsequent updates are usually faster

4. **Clear Browser Cache**
   - Hard refresh: Ctrl+F5 (Windows) or Cmd+Shift+R (Mac)

### Common Issues

**404 Error:**
- Make sure `.nojekyll` file exists in `demo_landing_page/`
- Verify all file paths are relative (not absolute)

**Styling Not Loading:**
- Check browser console for 404 errors
- Ensure `styles.css` is in `demo_landing_page/` folder

**Workflow Failing:**
- Check Actions tab for error messages
- Ensure `demo_landing_page/` folder exists
- Verify all required files are present

**"No workflow found" error:**
- Make sure `.github/workflows/deploy-pages.yml` exists
- Push the file to GitHub if you created it locally
- Try selecting "Static HTML" from the suggested workflows

## Manual Trigger

You can manually trigger deployment:

1. Go to: https://github.com/aritrode29/Albedo/actions
2. Click "Deploy Static HTML to GitHub Pages"
3. Click "Run workflow" → "Run workflow"

## File Structure

```
Albedo/
├── .github/
│   └── workflows/
│       └── deploy-pages.yml    # Deployment workflow
├── demo_landing_page/
│   ├── index.html              # Main page
│   ├── styles.css              # Styles
│   ├── script.js               # JavaScript
│   ├── .nojekyll               # GitHub Pages config
│   └── README.md               # Landing page docs
└── README.md                   # Project README
```

## Next Steps

After deployment:

1. ✅ Test your site: https://aritrode29.github.io/Albedo/
2. ✅ Share the URL with others
3. ✅ Make updates and push - they'll deploy automatically!

## Support

- **Repository**: https://github.com/aritrode29/Albedo
- **Actions**: https://github.com/aritrode29/Albedo/actions
- **Pages Settings**: https://github.com/aritrode29/Albedo/settings/pages

---

**Your site URL**: https://aritrode29.github.io/Albedo/
