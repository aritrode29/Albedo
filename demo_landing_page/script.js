// Wrap initialization in DOMContentLoaded to ensure elements exist (robust for different load scenarios)
document.addEventListener('DOMContentLoaded', () => {
  // Calculator functionality
  const sizeSlider = document.getElementById('size-slider');
  const sizeValue = document.getElementById('size-value');
  const scoreSlider = document.getElementById('score-slider');
  const scoreValue = document.getElementById('score-value');
  const increaseEl = document.getElementById('increase');
  const timeEl = document.getElementById('time');
  const readinessEl = document.getElementById('readiness');

  function updateCalculator() {
    const size = parseInt(sizeSlider.value);
    const score = parseInt(scoreSlider.value);
    
    sizeValue.textContent = size.toLocaleString();
    scoreValue.textContent = score;
    
    // Mock calculations
    const potentialIncrease = Math.min(25, Math.floor(size / 2000) + Math.floor(score / 10));
    const timeSaved = Math.floor(size / 1000) * 5;
    const readiness = Math.min(95, score + potentialIncrease);
    const newScore = score + potentialIncrease;
    
    increaseEl.textContent = `+${potentialIncrease} points`;
    timeEl.textContent = `${timeSaved} hours`;
    readinessEl.textContent = `${readiness}%`;
    
    // Update progress bars
    const scoreProgress = document.getElementById('score-progress');
    const timeProgress = document.getElementById('time-progress');
    const readinessProgress = document.getElementById('readiness-progress');
    const levelBadge = document.getElementById('level-badge');
    
    if (scoreProgress) scoreProgress.style.width = `${score}%`;
    if (timeProgress) timeProgress.style.width = `${Math.min(100, (timeSaved / 50) * 100)}%`;
    if (readinessProgress) readinessProgress.style.width = `${readiness}%`;
    
    // Update level badge
    if (levelBadge) {
      let level = 'Certified';
      if (newScore >= 80) level = 'Platinum';
      else if (newScore >= 60) level = 'Gold';
      else if (newScore >= 50) level = 'Silver';
      levelBadge.textContent = level;
    }
  }

  if (sizeSlider && scoreSlider) {
    sizeSlider.addEventListener('input', updateCalculator);
    scoreSlider.addEventListener('input', updateCalculator);
    updateCalculator(); // Initial calculation
  }

  // Problem expand buttons
  const expandBtns = document.querySelectorAll('.expand-btn');
  expandBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const solution = btn.nextElementSibling;
      if (solution.classList.contains('hidden')) {
        solution.classList.remove('hidden');
        btn.textContent = 'Click to hide solution';
      } else {
        solution.classList.add('hidden');
        btn.textContent = 'Click to see solution';
      }
    });
  });

  // RAG API configuration
  const RAG_API_URL = 'http://localhost:5000';
  let uploadedDocument = null;
  let apiHealthy = false;

  async function checkApiStatus() {
    try {
      const res = await fetch(`${RAG_API_URL}/api/status`, { method: 'GET' });
      apiHealthy = res.ok;
    } catch (e) {
      apiHealthy = false;
    }
    return apiHealthy;
  }

  const messagesEl = document.getElementById('messages');
  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-input');
  const sendBtn = document.getElementById('send-btn');
  const fileInput = document.getElementById('file-input-hidden');
  const attachBtn = document.getElementById('attach-btn');
  const clearBtn = document.getElementById('clear-chat');
  const openDemoBtn = document.getElementById('open-demo');
  const tryDemoBtn = document.getElementById('try-demo');
  const quickSuggestions = document.getElementById('quick-suggestions');
  const suggestionChips = document.querySelectorAll('.suggestion-chip');

  if(!messagesEl || !form || !input || !sendBtn) {
    console.error('Demo init: missing required DOM elements. Aborting script to avoid errors.');
    if(messagesEl) messagesEl.textContent = '⚠️ Demo script could not initialize: missing UI elements.';
    return;
  }

  function appendMessage(text, cls='bot'){
    const div = document.createElement('div');
    div.className = 'message ' + (cls==='user' ? 'user' : 'bot');
    
    if (cls === 'bot') {
      // Replace emojis with SVG icons
      let processedText = text
        .replace(/🔍/g, '<svg class="inline-icon-small" width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="5" stroke="#BF5700" stroke-width="1.5"/><path d="M12 12L15 15" stroke="#BF5700" stroke-width="1.5" stroke-linecap="round"/></svg>')
        .replace(/✅/g, '<svg class="inline-icon-small" width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" fill="#BF5700" opacity="0.1"/><path d="M5 8L7 10L11 6" stroke="#BF5700" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>')
        .replace(/❌/g, '<svg class="inline-icon-small" width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" fill="#BF5700" opacity="0.1"/><path d="M6 6L10 10M10 6L6 10" stroke="#BF5700" stroke-width="2" stroke-linecap="round"/></svg>')
        .replace(/📋/g, '<svg class="inline-icon-small" width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="2" y="2" width="12" height="12" rx="1" fill="#BF5700" opacity="0.1"/><path d="M5 5H11M5 7H11M5 9H9" stroke="#BF5700" stroke-width="1.5" stroke-linecap="round"/></svg>')
        .replace(/📄/g, '<svg class="inline-icon-small" width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="2" y="3" width="12" height="10" rx="1" fill="#BF5700" opacity="0.1"/><path d="M4 6H12M4 8H10M4 10H12" stroke="#BF5700" stroke-width="1.5" stroke-linecap="round"/></svg>');
      
      div.innerHTML = `<div class="message-content"><div class="bot-avatar"><svg width="20" height="20" viewBox="0 0 32 32" fill="none"><rect x="6" y="8" width="20" height="18" rx="2" fill="white"/><rect x="10" y="12" width="12" height="2" fill="#BF5700"/><rect x="10" y="16" width="8" height="2" fill="#BF5700"/><circle cx="16" cy="22" r="3" fill="#BF5700"/><rect x="8" y="6" width="16" height="2" rx="1" fill="#BF5700"/></svg></div><div>${processedText.replace(/\n/g, '<br>')}</div></div>`;
    } else {
      // Replace emojis in user messages too
      let processedText = text
        .replace(/📄/g, '<svg class="inline-icon-small" width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="2" y="3" width="12" height="10" rx="1" fill="#BF5700" opacity="0.1"/><path d="M4 6H12M4 8H10M4 10H12" stroke="#BF5700" stroke-width="1.5" stroke-linecap="round"/></svg>');
      div.innerHTML = processedText;
    }
    
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    
    // Hide quick suggestions after first message
    if (quickSuggestions && messagesEl.children.length > 1) {
      quickSuggestions.style.display = 'none';
    }
  }

  async function queryRAGAPI(query) {
    try {
      const response = await fetch(`${RAG_API_URL}/api/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query,
          limit: 3
        })
      });
      
      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
      }
      
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('RAG API Error:', error);
      return { error: true, message: `${error}` };
    }
  }

  async function analyzeDocument(documentText) {
    try {
      const response = await fetch(`${RAG_API_URL}/api/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          document_text: documentText,
          project_type: 'NC',
          target_credits: ['EA', 'WE', 'SS', 'EQ', 'MR']
        })
      });
      
      if (!response.ok) {
        throw new Error(`Analysis API request failed: ${response.status}`);
      }
      
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Analysis API Error:', error);
      return null;
    }
  }

  async function fetchCredits() {
    try {
      const res = await fetch(`${RAG_API_URL}/api/credits`, { method: 'GET' });
      if (!res.ok) throw new Error(`Credits API failed: ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error('Credits API Error:', e);
      return { error: true, message: `${e}` };
    }
  }

  async function botReply(prompt, uploadedFileSummary){
    const p = (prompt || '').toLowerCase();
    
    if(uploadedFileSummary){
      appendMessage(`Received file: ${uploadedFileSummary}`);
    }
    
    // Show typing indicator
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot typing';
    typingDiv.innerHTML = '<div class="message-content"><div class="bot-avatar"><svg width="20" height="20" viewBox="0 0 32 32" fill="none"><rect x="6" y="8" width="20" height="18" rx="2" fill="white"/><rect x="10" y="12" width="12" height="2" fill="#BF5700"/><rect x="10" y="16" width="8" height="2" fill="#BF5700"/><circle cx="16" cy="22" r="3" fill="#BF5700"/><rect x="8" y="6" width="16" height="2" rx="1" fill="#BF5700"/></svg></div><div><svg class="inline-icon-small" width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" fill="#BF5700" opacity="0.1"/><circle cx="8" cy="8" r="4" stroke="#BF5700" stroke-width="1.5"/><path d="M8 4V8L10 10" stroke="#BF5700" stroke-width="1.5" stroke-linecap="round"/></svg> Searching LEED knowledge base</div></div>';
    messagesEl.appendChild(typingDiv);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    
    try {
      // Command: list credits
      if (/(^|\b)(list|show) (all )?credits(\b|$)/i.test(prompt)) {
        const resp = await fetchCredits();
        if (resp && !resp.error && resp.credits && resp.credits.length) {
          appendMessage(`Found ${resp.total_count} credits. Showing first 20:`);
          resp.credits.slice(0, 20).forEach((c, i) => {
            appendMessage(`${i + 1}. ${c.code || 'N/A'} — ${c.name || 'Unnamed'} (${c.type || 'Credit'})`);
          });
          appendMessage('Tip: ask for a specific credit (e.g., "EA Optimize Energy Performance").');
        } else {
          const healthy = await checkApiStatus();
          if (!healthy) {
            appendMessage('❌ Backend API is not reachable. Start it: python src/leed_rag_api.py');
          } else {
            appendMessage('No credit list available.');
          }
        }
        return;
      }

      if(p.includes('analy') || p.includes('scan')){
        if (uploadedDocument) {
          appendMessage('Analyzing uploaded document against LEED requirements...');
          
          const analysisData = await analyzeDocument(uploadedDocument);
          if (analysisData && !analysisData.error) {
            appendMessage(`Analysis complete for ${analysisData.analysis_results.length} credit categories:`);
            
            analysisData.analysis_results.forEach(result => {
              appendMessage(`\n📋 ${result.credit_code} Credit:`);
              if (result.relevant_info && result.relevant_info.length > 0) {
                const topResult = result.relevant_info[0];
                appendMessage(`   Requirements: ${topResult.text.substring(0, 200)}...`);
                appendMessage(`   Relevance Score: ${topResult.score.toFixed(3)}`);
              }
            });
          } else {
            appendMessage('❌ Analysis failed. API may be offline.');
            appendMessage('Tip: Start the API: python src/leed_rag_api.py');
          }
        } else {
          appendMessage('Please upload a document first, then ask me to analyze it.');
        }
      } else if(p.includes('recommend')){
        const ragData = await queryRAGAPI('LEED credit recommendations and best practices');
        if (ragData && !ragData.error && ragData.results) {
          appendMessage('Top LEED recommendations:');
          ragData.results.forEach((result, index) => {
            if (index < 2) {
              appendMessage(`\n${index + 1}. ${result.metadata.credit_name || 'Credit'}:`);
              appendMessage(`   ${result.text.substring(0, 150)}...`);
            }
          });
        } else {
          appendMessage('❌ Unable to get recommendations. API may be offline.');
          appendMessage('Tip: Start the API: python src/leed_rag_api.py');
        }
      } else if(p.includes('energy')){
        const ragData = await queryRAGAPI('energy efficiency requirements LEED credits');
        if (ragData && !ragData.error && ragData.results) {
          appendMessage('Energy efficiency requirements:');
          ragData.results.forEach((result, index) => {
            if (index < 2) {
              appendMessage(`\n${index + 1}. ${result.metadata.credit_name || 'Credit'}:`);
              appendMessage(`   ${result.text.substring(0, 150)}...`);
            }
          });
        } else {
          appendMessage('❌ Unable to get energy information. API may be offline.');
          appendMessage('Tip: Start the API: python src/leed_rag_api.py');
        }
      } else if(p.includes('hello') || p.includes('hi')){
        appendMessage('Hello! I\'m Albedo with AI-powered LEED knowledge. Upload a document or ask me about LEED credits!');
      } else {
        // General query to RAG API
        const ragData = await queryRAGAPI(prompt);
        if (ragData && !ragData.error && ragData.results) {
          let response = `Found ${ragData.results.length} relevant result${ragData.results.length > 1 ? 's' : ''}:\n\n`;
          ragData.results.forEach((result, index) => {
            if (index < 3) {
              response += `📋 **${result.metadata.credit_name || 'Credit'}**\n`;
              response += `${result.text.substring(0, 250)}${result.text.length > 250 ? '...' : ''}\n\n`;
            }
          });
          appendMessage(response);
        } else {
          const healthy = await checkApiStatus();
          if (!healthy) {
            appendMessage('❌ Backend API is not reachable.\n\n**Tip:** Start the API server:\n```bash\npython src/leed_rag_api.py\n```\nThen reload this page and try again.');
          } else {
            appendMessage('I couldn\'t find specific information about that. Try asking:\n• "List all LEED credits"\n• "Energy efficiency requirements"\n• "Water efficiency credits"\n• Or upload a document for analysis');
          }
        }
      }
    } catch (error) {
      appendMessage('❌ Error processing request. Please try again.');
      console.error('Bot reply error:', error);
    } finally {
      // Remove typing indicator
      const typingElements = messagesEl.querySelectorAll('.typing');
      typingElements.forEach(el => el.remove());
    }
  }

  form.addEventListener('submit', (e)=>{
    e.preventDefault();
    const text = input.value.trim();
    if(!text) return;
    appendMessage(text, 'user');
    input.value='';
    botReply(text);
  });

  sendBtn.addEventListener('click', ()=>{ 
    if (typeof form.requestSubmit === 'function') {
      form.requestSubmit();
    } else {
      // fallback for older browsers
      form.submit();
    }
  });

  // Attach button click handler
  attachBtn && attachBtn.addEventListener('click', () => {
    fileInput && fileInput.click();
  });

  fileInput && fileInput.addEventListener('change', (e)=>{
    const f = e.target.files && e.target.files[0];
    if(!f) return;
    
    appendMessage(`📄 Uploaded: ${f.name} (${Math.round(f.size/1024)} KB)`, 'user');
    
    // Show loading state
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message bot typing';
    loadingDiv.innerHTML = '<div class="message-content"><div class="bot-avatar"><svg width="20" height="20" viewBox="0 0 32 32" fill="none"><rect x="6" y="8" width="20" height="18" rx="2" fill="white"/><rect x="10" y="12" width="12" height="2" fill="#BF5700"/><rect x="10" y="16" width="8" height="2" fill="#BF5700"/><circle cx="16" cy="22" r="3" fill="#BF5700"/><rect x="8" y="6" width="16" height="2" rx="1" fill="#BF5700"/></svg></div><div>Processing document...</div></div>';
    messagesEl.appendChild(loadingDiv);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    
    // Store document for analysis
    const reader = new FileReader();
    reader.onload = () => {
      uploadedDocument = reader.result || '';
      loadingDiv.remove();
      appendMessage('✅ Document loaded successfully! I can now analyze it. Try asking: "Analyze this document" or "What credits does this document cover?"');
    };
    reader.onerror = () => {
      loadingDiv.remove();
      appendMessage('❌ Failed to read the uploaded file. Try a different file or use a plain text file.');
    };
    try {
      reader.readAsText(f.slice(0,20000));
    } catch (err) {
      console.error('File read error:', err);
      loadingDiv.remove();
      appendMessage('❌ Failed to read the uploaded file. Try a different file or use a plain text file.');
    }
  });

  // Suggestion chips click handlers
  suggestionChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const query = chip.getAttribute('data-query');
      if (query) {
        input.value = query;
        input.focus();
        // Auto-submit after a short delay for better UX
        setTimeout(() => {
          form.dispatchEvent(new Event('submit'));
        }, 100);
      }
    });
  });

  clearBtn && clearBtn.addEventListener('click', ()=>{
    messagesEl.innerHTML = '';
    uploadedDocument = null;
    if (quickSuggestions) quickSuggestions.style.display = 'flex';
    
    // Restore welcome message
    const welcomeMsg = document.createElement('div');
    welcomeMsg.className = 'message bot welcome-message';
    welcomeMsg.innerHTML = `
      <div class="message-content">
        <div class="bot-avatar"><svg width="20" height="20" viewBox="0 0 32 32" fill="none"><rect x="6" y="8" width="20" height="18" rx="2" fill="white"/><rect x="10" y="12" width="12" height="2" fill="#BF5700"/><rect x="10" y="16" width="8" height="2" fill="#BF5700"/><circle cx="16" cy="22" r="3" fill="#BF5700"/><rect x="8" y="6" width="16" height="2" rx="1" fill="#BF5700"/></svg></div>
        <div>
          <strong>Hi! I'm Albedo</strong>
          <p>Your AI-powered LEED assistant. I can help you with:</p>
          <ul class="help-list">
            <li><svg class="list-icon" width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="2" y="3" width="12" height="10" rx="1" fill="#BF5700" opacity="0.1"/><path d="M4 6H12M4 8H10M4 10H12" stroke="#BF5700" stroke-width="1.5" stroke-linecap="round"/></svg> Analyze LEED documents</li>
            <li><svg class="list-icon" width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="2" y="2" width="12" height="12" rx="1" fill="#BF5700" opacity="0.1"/><path d="M5 5H11M5 7H11M5 9H9" stroke="#BF5700" stroke-width="1.5" stroke-linecap="round"/></svg> List and explain credits</li>
            <li><svg class="list-icon" width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="5" fill="#BF5700" opacity="0.1"/><path d="M8 4V8L10 10" stroke="#BF5700" stroke-width="1.5" stroke-linecap="round"/><circle cx="8" cy="8" r="1" fill="#BF5700"/></svg> Provide recommendations</li>
            <li><svg class="list-icon" width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" fill="#BF5700" opacity="0.1"/><circle cx="8" cy="5" r="1" fill="#BF5700"/><path d="M8 7V11M8 12V13" stroke="#BF5700" stroke-width="1.5" stroke-linecap="round"/></svg> Answer compliance questions</li>
          </ul>
          <p class="suggestion-text">Try asking me something or upload a document to get started!</p>
        </div>
      </div>
    `;
    messagesEl.appendChild(welcomeMsg);
  });

  openDemoBtn && openDemoBtn.addEventListener('click', ()=>{
    const demoEl = document.querySelector('#demo');
    demoEl && demoEl.scrollIntoView({behavior:'smooth'});
  });

  tryDemoBtn && tryDemoBtn.addEventListener('click', ()=>{
    const demoEl = document.querySelector('#demo');
    demoEl && demoEl.scrollIntoView({behavior:'smooth'});
  });

  // small accessibility: allow Enter in input to send
  input.addEventListener('keydown', (e)=>{
    if(e.key === 'Enter' && !e.shiftKey){
      e.preventDefault(); 
      if (typeof form.requestSubmit === 'function') form.requestSubmit();
      else form.submit();
    }
  });

});
