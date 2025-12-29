# PowerShell script to start the LEED RAG API backend
# Run this script to start the backend server

Write-Host "=" * 60
Write-Host "🚀 Starting Albedo LEED RAG API Backend"
Write-Host "=" * 60
Write-Host ""

# Navigate to project directory
$projectPath = "G:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool"
Set-Location $projectPath

# Check if models exist
$modelsExist = (Test-Path "models\index_all.faiss") -or (Test-Path "models\index_credits.faiss") -or (Test-Path "models\leed_knowledge_base.faiss")

if (-not $modelsExist) {
    Write-Host "⚠️  Warning: RAG model files not found!" -ForegroundColor Yellow
    Write-Host "   The API will start but won't be able to answer queries."
    Write-Host "   To build the models, run: python src/deploy_rag_system.py"
    Write-Host ""
}

Write-Host "📡 Starting Flask server on http://localhost:5000" -ForegroundColor Green
Write-Host "   Frontend should connect automatically if running on localhost"
Write-Host ""
Write-Host "💡 Tips:"
Write-Host "   - Open http://localhost:5000/api/status in browser to verify it's running"
Write-Host "   - Open demo_landing_page/index.html for the frontend"
Write-Host "   - Press Ctrl+C to stop the server"
Write-Host ""
Write-Host "=" * 60
Write-Host ""

# Start the Flask server
try {
    python src/leed_rag_api.py
} catch {
    Write-Host "❌ Error starting server: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:"
    Write-Host "1. Make sure Python is installed and in PATH"
    Write-Host "2. Install dependencies: pip install -r requirements.txt"
    Write-Host "3. Check if port 5000 is already in use"
    Write-Host ""
    Read-Host "Press Enter to exit"
}


