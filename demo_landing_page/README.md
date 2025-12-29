# Albedo - AI-Powered LEED Pre-Compliance Assistant

A modern, gamified landing page for Albedo, an AI-powered LEED certification assistant.

## Features

- 🎯 **Interactive Calculator** - Calculate potential LEED score improvements and time savings
- 🤖 **AI Chatbot** - Upload documents and ask questions about LEED compliance
- 📊 **Gamified Interface** - Progress bars, badges, and level indicators
- 🎨 **UT Austin Branding** - Burnt Orange and Black color scheme
- 📱 **Responsive Design** - Works on all devices

## Local Development

Simply open `index.html` in your web browser, or use a local server:

```bash
# Python 3
python -m http.server 8000

# Node.js
npx serve

# PHP
php -S localhost:8000
```

Then open `http://localhost:8000` in your browser.

## GitHub Pages Deployment

This site is automatically deployed to GitHub Pages via GitHub Actions. The workflow is configured in `.github/workflows/deploy-pages.yml`.

### Manual Deployment

1. Push your changes to the `main` or `master` branch
2. Go to your repository Settings → Pages
3. Under "Source", select "GitHub Actions"
4. The site will be available at **https://aritrode29.github.io/Albedo/**

### File Structure

```
demo_landing_page/
├── index.html          # Main HTML file
├── styles.css          # All styles
├── script.js           # Interactive functionality
└── .nojekyll           # Prevents Jekyll processing
```

## Customization

### Colors

The site uses UT Austin colors defined in CSS variables:

```css
--accent: #BF5700;        /* Burnt Orange */
--accent-dark: #A04500;    /* Darker Burnt Orange */
--text: #333F48;          /* UT Dark Gray/Black */
```

### API Configuration

The chatbot connects to a backend API. Update the API URL in `script.js`:

```javascript
const RAG_API_URL = 'http://localhost:5000';
```

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## License

See the main repository LICENSE file.
