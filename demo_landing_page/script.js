// Wrap initialization in DOMContentLoaded to ensure elements exist (robust for different load scenarios)
document.addEventListener('DOMContentLoaded', () => {
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
  const fileInput = document.getElementById('file-input');
  const clearBtn = document.getElementById('clear-chat');
  const openDemoBtn = document.getElementById('open-demo');

  if(!messagesEl || !form || !input || !sendBtn) {
    console.error('Demo init: missing required DOM elements. Aborting script to avoid errors.');
    if(messagesEl) messagesEl.textContent = '⚠️ Demo script could not initialize: missing UI elements.';
    return;
  }

  function appendMessage(text, cls='bot'){
    const div = document.createElement('div');
    div.className = 'message ' + (cls==='user' ? 'user' : 'bot');
    div.textContent = text;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
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
    typingDiv.textContent = '🔍 Searching LEED knowledge base...';
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
          appendMessage(`Found ${ragData.results.length} relevant LEED information:`);
          ragData.results.forEach((result, index) => {
            if (index < 2) {
              appendMessage(`\n📋 ${result.metadata.credit_name || 'Credit'}:`);
              appendMessage(`   ${result.text.substring(0, 200)}...`);
              appendMessage(`   Relevance: ${result.score.toFixed(3)}`);
            }
          });
        } else {
          const healthy = await checkApiStatus();
          if (!healthy) {
            appendMessage('❌ Backend API is not reachable.');
            appendMessage('Tip: Start the API: python src/leed_rag_api.py');
            appendMessage('Then reload this page and try again.');
          } else {
            appendMessage('No relevant results found. Try a more specific LEED v4.1 question (e.g., "EA Optimize Energy Performance").');
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

  fileInput && fileInput.addEventListener('change', (e)=>{
    const f = e.target.files && e.target.files[0];
    if(!f) return;
    appendMessage(`Uploaded file: ${f.name} (${Math.round(f.size/1024)} KB)`);
    
    // Store document for analysis
    const reader = new FileReader();
    reader.onload = () => {
      uploadedDocument = reader.result || '';
      const preview = (typeof uploadedDocument === 'string') ? uploadedDocument.slice(0,800) : '';
      appendMessage('Document loaded successfully!');
      appendMessage('Preview (first 800 chars):');
      appendMessage(preview);
      appendMessage('You can now ask: "Analyze this document" or ask specific LEED questions.');
    };
    try {
      reader.readAsText(f.slice(0,20000));
    } catch (err) {
      console.error('File read error:', err);
      appendMessage('❌ Failed to read the uploaded file. Try a different file or use a plain text file.');
    }
  });

  clearBtn && clearBtn.addEventListener('click', ()=>{
    messagesEl.innerHTML = '';
    uploadedDocument = null;
    appendMessage("👋 Hi! I'm Albedo, your AI-powered LEED assistant. Upload a document or ask me about LEED credits, compliance requirements, or recommendations!");
  });

  openDemoBtn && openDemoBtn.addEventListener('click', ()=>{
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
