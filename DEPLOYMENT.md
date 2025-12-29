# GitHub Pages Deployment Guide

This guide explains how to deploy the Albedo landing page to GitHub Pages.

## Quick Start

1. **Enable GitHub Pages**
   - Go to your repository Settings
   - Navigate to Pages (left sidebar)
   - Under "Source", select **"GitHub Actions"**
   - Save the changes

2. **Push to Main Branch**
   - The GitHub Actions workflow will automatically deploy when you push to `main` or `master`
   - You can also manually trigger it from the Actions tab → "Deploy to GitHub Pages" → "Run workflow"

3. **Access Your Site**
   - Your site will be available at: `https://aritrode29.github.io/Albedo/`
   - The site URL is: **https://aritrode29.github.io/Albedo/**

## What Gets Deployed

The workflow deploys everything in the `demo_landing_page/` folder:
- `index.html` - Main HTML file
- `styles.css` - All styles
- `script.js` - Interactive functionality
- `.nojekyll` - Prevents Jekyll processing (important!)

## Workflow Details

The deployment workflow (`.github/workflows/deploy-pages.yml`) does the following:

1. **Triggers**: 
   - On push to `main` or `master` branch
   - Manual trigger via workflow_dispatch

2. **Steps**:
   - Checks out the repository
   - Configures GitHub Pages
   - Uploads the `demo_landing_page` folder as an artifact
   - Deploys to GitHub Pages

## Troubleshooting

### Site Not Updating
- Check the Actions tab for any workflow errors
- Ensure GitHub Pages is set to use "GitHub Actions" as the source
- Verify the `demo_landing_page` folder exists and contains all files

### 404 Errors
- Make sure `.nojekyll` file exists in `demo_landing_page/`
- Check that file paths are relative (not absolute)
- Verify the base URL matches your repository name

### Styling Not Loading
- Ensure `styles.css` is in the `demo_landing_page` folder
- Check browser console for 404 errors
- Verify file paths are relative (e.g., `href="styles.css"` not `href="/styles.css"`)

## Custom Domain (Optional)

To use a custom domain:

1. Add a `CNAME` file to `demo_landing_page/` with your domain:
   ```
   yourdomain.com
   ```

2. Configure DNS:
   - Add a CNAME record pointing to `<username>.github.io`

3. Update GitHub Pages settings:
   - Go to Settings → Pages
   - Enter your custom domain

## Manual Deployment

If you prefer manual deployment:

1. Clone the repository
2. Copy contents of `demo_landing_page/` to a `docs/` folder
3. Go to Settings → Pages
4. Select "Deploy from a branch" → "main" → "docs"
5. Save

**Note**: The GitHub Actions method is recommended as it's automated and easier to maintain.

## Testing Locally

Before deploying, test locally:

```bash
cd demo_landing_page
python -m http.server 8000
```

Then open `http://localhost:8000` in your browser.

## File Structure

```
repository/
├── .github/
│   └── workflows/
│       └── deploy-pages.yml    # GitHub Actions workflow
├── demo_landing_page/
│   ├── index.html              # Main HTML
│   ├── styles.css              # Styles
│   ├── script.js               # JavaScript
│   ├── .nojekyll               # Disable Jekyll
│   └── README.md               # Landing page docs
└── README.md                   # Main project README
```

## Support

For issues or questions:
- Check GitHub Actions logs in the Actions tab
- Review the workflow file: `.github/workflows/deploy-pages.yml`
- See `demo_landing_page/README.md` for landing page specific docs

