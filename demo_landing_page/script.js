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

  // RAG API configuration - uses config.js for easy customization
  const RAG_API_URL = window.getApiUrl ? window.getApiUrl() : 
    (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
      ? 'http://localhost:5000' 
      : 'http://localhost:5000'); // Default fallback
  
  let uploadedDocument = null;
  let apiHealthy = false;
  
  // Log API configuration for debugging
  console.log('Albedo API URL:', RAG_API_URL);
  console.log('Environment:', window.location.hostname === 'localhost' ? 'Development' : 'Production');

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
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/2627578b-6952-47f1-bd3c-8617269915d9',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'script.js:141',message:'queryRAGAPI entry',data:{query:query},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H7'})}).catch(()=>{});
    // #endregion
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
      
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/2627578b-6952-47f1-bd3c-8617269915d9',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'script.js:154',message:'queryRAGAPI response status',data:{status:response.status,ok:response.ok},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H7'})}).catch(()=>{});
      // #endregion
      
      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
      }
      
      const data = await response.json();
      
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/2627578b-6952-47f1-bd3c-8617269915d9',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'script.js:162',message:'queryRAGAPI response data',data:{hasError:!!data.error,resultsCount:data.results?data.results.length:0,status:data.status,query:data.query},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H7'})}).catch(()=>{});
      // #endregion
      
      return data;
    } catch (error) {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/2627578b-6952-47f1-bd3c-8617269915d9',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'script.js:166',message:'queryRAGAPI error',data:{error:error.message},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H7'})}).catch(()=>{});
      // #endregion
      console.error('RAG API Error:', error);
      return { error: true, message: `${error}` };
    }
  }

  async function queryAssistantAPI(query, evidenceText) {
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/2627578b-6952-47f1-bd3c-8617269915d9',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'script.js:166',message:'queryAssistantAPI entry',data:{query:query,hasEvidence:!!evidenceText},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H7'})}).catch(()=>{});
    // #endregion
    // High-level robust assistant: templates + evidence classifier + strict citations.
    try {
      const response = await fetch(`${RAG_API_URL}/api/assistant`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query,
          evidence_text: evidenceText || null,
          limit: 4
        })
      });

      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/2627578b-6952-47f1-bd3c-8617269915d9',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'script.js:181',message:'queryAssistantAPI response status',data:{status:response.status,ok:response.ok},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H7'})}).catch(()=>{});
      // #endregion

      if (!response.ok && response.status !== 200) {
        // Only return null for actual errors (not 200 with error message)
        console.warn('Assistant API request failed:', response.status);
        return null;
      }

      const data = await response.json();
      
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/2627578b-6952-47f1-bd3c-8617269915d9',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'script.js:192',message:'queryAssistantAPI response data',data:{status:data.status,hasAnswer:!!data.answer,retrievedCount:data.retrieved?data.retrieved.length:0,hasError:!!data.error,fallbackAvailable:data.fallback_available},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H7'})}).catch(()=>{});
      // #endregion
      
      // If assistant returned error but suggests fallback, return null to trigger fallback
      if (data.status !== 'success' || data.fallback_available) {
        console.warn('Assistant API returned non-success status or fallback suggested:', data.status);
        return null;
      }
      return data;
    } catch (error) {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/2627578b-6952-47f1-bd3c-8617269915d9',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'script.js:199',message:'queryAssistantAPI error',data:{error:error.message},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H7'})}).catch(()=>{});
      // #endregion
      console.error('Assistant API Error:', error);
      return null;
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
      // Command: list credits - improved pattern to match "list all LEED credits"
      // #region agent log
      const isListCredits = /(^|\b)(list|show)(\s+all)?(\s+LEED)?(\s+credits?)(\b|$)/i.test(prompt);
      fetch('http://127.0.0.1:7242/ingest/2627578b-6952-47f1-bd3c-8617269915d9',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'script.js:281',message:'list credits pattern check',data:{prompt:prompt,matches:isListCredits},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H7'})}).catch(()=>{});
      // #endregion
      if (isListCredits) {
        const resp = await fetchCredits();
        if (resp && !resp.error && resp.credits && resp.credits.length) {
          appendMessage(`Great! I found ${resp.total_count} LEED credits in the knowledge base. Here are the first 20 credits:\n\n`);
          resp.credits.slice(0, 20).forEach((c, i) => {
            appendMessage(`${i + 1}. **${c.code || 'N/A'}** — ${c.name || 'Unnamed'} (${c.type || 'Credit'})`);
          });
          appendMessage('\n**Tip:** You can ask me about any specific credit for detailed information. For example, try asking "Tell me about EA Optimize Energy Performance" or "What are the requirements for WE Indoor Water Use Reduction?"');
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
          appendMessage('I\'m analyzing your uploaded document against LEED requirements. This may take a moment...');
          
          const analysisData = await analyzeDocument(uploadedDocument);
          if (analysisData && !analysisData.error) {
            appendMessage(`**Analysis Complete!**\n\nI've reviewed your document against ${analysisData.analysis_results.length} LEED credit categories. Here's what I found:\n`);
            
            analysisData.analysis_results.forEach(result => {
              appendMessage(`**${result.credit_code} Credit:**`);
              if (result.relevant_info && result.relevant_info.length > 0) {
                const topResult = result.relevant_info[0];
                appendMessage(`The document appears to address: ${topResult.text.substring(0, 250)}${topResult.text.length > 250 ? '...' : ''}`);
                appendMessage(`Relevance: ${(topResult.score * 100).toFixed(0)}% match\n`);
              } else {
                appendMessage(`No clear connection found to this credit category.\n`);
              }
            });
            
            appendMessage('Would you like me to provide more detailed information about any of these credits?');
          } else {
            appendMessage('I apologize, but I couldn\'t complete the analysis. The backend API may be offline.\n\n**To fix this:** Start the API server by running:\n```bash\npython src/leed_rag_api.py\n```\nThen reload this page and try again.');
          }
        } else {
          appendMessage('I\'d be happy to analyze a document for you! Please upload a document first using the attachment button, then ask me to analyze it. I can help identify which LEED credits your document addresses and provide guidance on compliance.');
        }
      } else if(p.includes('hello') || p.includes('hi')){
        appendMessage('Hello! I\'m Albedo, your AI-powered LEED certification assistant. I\'m here to help you understand LEED credits, analyze your project documentation, and guide you through the certification process. Feel free to ask me anything about LEED requirements, or upload a document and I can help analyze it for compliance. What would you like to know?');
      } else {
        // General query: prefer robust assistant (templates + citations + evidence),
        // with a fallback to plain RAG retrieval summary.
        const assistantData = await queryAssistantAPI(prompt, uploadedDocument);
        // Check if assistant found results (retrieved array exists and has items)
        const hasResults = assistantData && assistantData.retrieved && Array.isArray(assistantData.retrieved) && assistantData.retrieved.length > 0;
        
        // Debug logging
        console.log('Query:', prompt);
        if (assistantData) {
          console.log('Assistant API response:', {
            hasAnswer: !!assistantData.answer,
            retrievedCount: assistantData.retrieved ? assistantData.retrieved.length : 0,
            hasResults: hasResults,
            answerPreview: assistantData.answer ? assistantData.answer.substring(0, 100) : 'no answer'
          });
        } else {
          console.log('Assistant API returned null/undefined');
        }
        
        if (assistantData && assistantData.answer && hasResults) {
          // Main answer (now in natural language format)
          appendMessage(assistantData.answer);

          // Citations block (now formatted more naturally)
          if (assistantData.citations && assistantData.citations.trim()) {
            appendMessage(assistantData.citations);
          }

          // Optional evidence classifier result (now with natural language explanation)
          if (assistantData.evidence_classification) {
            const evidence = assistantData.evidence_classification;
            let evidenceMessage = "**Evidence Analysis:**\n\n";
            
            if (evidence.reason) {
              evidenceMessage += evidence.reason;
            } else {
              // Fallback to decision-based message
              if (evidence.decision === "supported") {
                evidenceMessage += `Your evidence appears to support this credit requirement. `;
                evidenceMessage += `Confidence level: ${(evidence.confidence * 100).toFixed(0)}%.`;
              } else {
                evidenceMessage += `Your evidence may need additional details to fully support this credit. `;
                evidenceMessage += `Confidence level: ${(evidence.confidence * 100).toFixed(0)}%.`;
              }
            }
            
            appendMessage(evidenceMessage);
          }
        } else {
          // Fallback: plain RAG retrieval summary - ALWAYS use this for reliable results
          const ragData = await queryRAGAPI(prompt);
          
          // Debug logging
          console.log('RAG API fallback response:', {
            hasError: !!ragData.error,
            errorMessage: ragData.error || ragData.message || 'none',
            resultsCount: ragData.results ? ragData.results.length : 0,
            query: prompt,
            resultsPreview: ragData.results ? ragData.results.slice(0, 2).map(r => ({
              credit: r.metadata?.credit_name || r.metadata?.credit_code || 'unknown',
              score: r.score,
              textPreview: r.text?.substring(0, 50) || 'no text'
            })) : 'no results'
          });
          
          if (ragData && !ragData.error && ragData.results && ragData.results.length > 0) {
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/2627578b-6952-47f1-bd3c-8617269915d9',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'script.js:398',message:'displaying results',data:{resultsCount:ragData.results.length,firstResultMetadata:ragData.results[0]?.metadata,firstResultText:ragData.results[0]?.text?.substring(0,100)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'H7'})}).catch(()=>{});
            // #endregion
            let response = `I found ${ragData.results.length} relevant result${ragData.results.length > 1 ? 's' : ''} in the LEED knowledge base:\n\n`;
            ragData.results.forEach((result, index) => {
              if (index < 5) { // Show up to 5 results
                // Extract credit info more robustly
                const metadata = result.metadata || {};
                let creditCode = metadata.credit_code || metadata.CreditCode || '';
                let creditName = metadata.credit_name || metadata.CreditName || '';
                const category = metadata.category || metadata.Category || '';
                const creditType = metadata.type || metadata.credit_type || metadata.CreditType || 'Credit';
                
                // Clean up credit name (remove trailing dots and extra whitespace)
                if (creditName) {
                  creditName = creditName.replace(/\.{3,}/g, '').replace(/\s+/g, ' ').trim();
                  // Remove page numbers at the end (e.g., "Credit Name ........................................................... 12")
                  creditName = creditName.replace(/\s+\d+\s*$/, '').trim();
                }
                
                // Try to extract from text if metadata is missing
                const text = result.text || '';
                if (!creditCode || !creditName || creditCode === 'None') {
                  // Pattern: "EA Credit: Optimize Energy Performance" or "None Credit: LEED Accredited"
                  const textMatch = text.match(/^([A-Z]{1,3}|None)\s+(?:Credit|Prerequisite|Prereq)?\s*:?\s*(.+?)(?:\n|\.{3,}|$)/);
                  if (textMatch) {
                    if ((!creditCode || creditCode === 'None') && textMatch[1] !== 'None') {
                      creditCode = textMatch[1];
                    }
                    if (!creditName) {
                      creditName = textMatch[2].replace(/\.{3,}/g, '').replace(/\s+/g, ' ').trim();
                      creditName = creditName.replace(/\s+\d+\s*$/, '').trim();
                    }
                  }
                  
                  // Try alternative pattern: "EA Prerequisite: Minimum Energy Performance"
                  if (!creditCode || creditCode === 'None') {
                    const altMatch = text.match(/^([A-Z]{1,3})\s+(Prerequisite|Credit|Prereq)/);
                    if (altMatch) {
                      creditCode = altMatch[1];
                    }
                  }
                }
                
                // Build display name
                let displayName = '';
                if (creditCode && creditCode !== 'None' && creditName) {
                  displayName = `${creditCode}: ${creditName}`;
                } else if (creditCode && creditCode !== 'None') {
                  displayName = creditCode;
                } else if (creditName) {
                  displayName = creditName;
                } else if (category) {
                  displayName = category;
                } else {
                  // Extract from text as last resort
                  const fallbackMatch = text.match(/^([A-Z]{1,3})\s+(?:Credit|Prerequisite|Prereq)?\s*:?\s*(.+?)(?:\n|$)/);
                  if (fallbackMatch && fallbackMatch[1] !== 'None') {
                    displayName = `${fallbackMatch[1]}: ${fallbackMatch[2].substring(0, 50).trim()}`;
                  } else {
                    displayName = `${creditType} Information`;
                  }
                }
                
                response += `**${displayName}**\n`;
                // Clean and display text (remove excessive dots, trim, remove page numbers)
                let displayText = text.replace(/\.{4,}/g, '...').trim();
                // Remove trailing page numbers
                displayText = displayText.replace(/\s+\d+\s*$/, '').trim();
                displayText = displayText.length > 400 ? displayText.substring(0, 400) + '...' : displayText;
                if (displayText) {
                  response += `${displayText}\n\n`;
                }
              }
            });
            response += 'Would you like more details about any of these credits?';
            appendMessage(response);
          } else {
            const healthy = await checkApiStatus();
            if (!healthy) {
              appendMessage('❌ Backend API is not reachable.\n\n**Tip:** Start the API server:\n```bash\npython src/leed_rag_api.py\n```\nThen reload this page and try again.');
            } else {
              appendMessage('I couldn\'t find specific information about that in the knowledge base. Let me help you get the information you need. You could try:\n\n• Asking about a specific credit (e.g., "Tell me about EA Optimize Energy Performance")\n• Requesting a list of credits ("List all LEED credits")\n• Asking about categories ("What are the energy efficiency requirements?")\n• Uploading a document for analysis\n\nFeel free to rephrase your question, and I\'ll do my best to help!');
            }
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
      appendMessage('Perfect! I\'ve successfully loaded your document. I can now help you analyze it for LEED compliance.\n\n**What would you like to do?**\n• Ask me to "Analyze this document" to see which LEED credits it addresses\n• Ask "What credits does this document cover?" for a summary\n• Ask specific questions about how your document relates to particular LEED credits\n\nFeel free to ask me anything about your document!');
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
