# GitHub Actions Workflows

This directory contains GitHub Actions workflows for automated deployment and CI/CD.

## Workflows

### `deploy-pages.yml`

Automatically deploys the `demo_landing_page` folder to GitHub Pages whenever changes are pushed to the `main` or `master` branch.

**Features:**
- Automatic deployment on push to main/master
- Manual trigger via workflow_dispatch
- Uses GitHub Pages Actions v4
- Deploys from `demo_landing_page` directory

**Setup:**
1. Ensure your repository has GitHub Pages enabled
2. Go to Settings → Pages
3. Select "GitHub Actions" as the source
4. Push to main/master branch to trigger deployment

**URL:**
Your site will be available at: `https://aritrode29.github.io/Albedo/`

