(() => {
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
  const request = (url, options = {}) => fetch(url, { ...options, headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf, ...(options.headers || {}) } }).then(async res => { const body = await res.json().catch(() => ({})); if (!res.ok) throw new Error(body.error || 'Request could not be completed.'); return body; });

  const root = document.documentElement;
  const savedTheme = localStorage.getItem('echoguard-theme');
  if (savedTheme) root.dataset.theme = savedTheme;
  document.querySelectorAll('[data-theme-toggle]').forEach(button => button.addEventListener('click', () => {
    root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('echoguard-theme', root.dataset.theme);
    document.querySelectorAll('[data-theme-icon]').forEach(icon => { icon.textContent = root.dataset.theme === 'dark' ? '☼' : '◐'; });
  }));

  const content = document.querySelector('[data-voice-target]');
  const voiceButton = document.querySelector('[data-voice-input]');
  const voiceLabel = document.querySelector('[data-voice-label]');
  const wordCount = document.querySelector('[data-word-count]');
  if (content && wordCount) {
    const updateCount = () => { wordCount.textContent = `${content.value.trim() ? content.value.trim().split(/\s+/).length : 0} words`; };
    content.addEventListener('input', updateCount); updateCount();
  }
  if (voiceButton && content) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) { voiceButton.disabled = true; voiceLabel.textContent = 'Voice unavailable — type instead'; }
    else {
      const recognition = new SpeechRecognition(); recognition.continuous = true; recognition.interimResults = true; recognition.lang = document.documentElement.lang || 'en-US'; let base = '';
      recognition.onstart = () => { voiceButton.classList.add('is-listening'); voiceButton.setAttribute('aria-pressed', 'true'); voiceLabel.textContent = 'Listening… click to stop'; };
      recognition.onend = () => { voiceButton.classList.remove('is-listening'); voiceButton.setAttribute('aria-pressed', 'false'); voiceLabel.textContent = 'Use voice input'; };
      recognition.onresult = event => { let interim = ''; for (let i = event.resultIndex; i < event.results.length; i++) { const transcript = event.results[i][0].transcript; if (event.results[i].isFinal) base += `${transcript} `; else interim += transcript; } content.value = `${base}${interim}`.trim(); content.dispatchEvent(new Event('input')); };
      voiceButton.addEventListener('click', () => { if (voiceButton.classList.contains('is-listening')) recognition.stop(); else { base = content.value ? `${content.value.trim()} ` : ''; recognition.start(); } });
    }
  }

  document.querySelectorAll('[data-memory-action]').forEach(button => button.addEventListener('click', async () => {
    const action = button.dataset.memoryAction; const id = button.dataset.noteId;
    try { const result = await request(`/api/memories/${id}/${action}`, { method: 'POST' }); if (action === 'archive') button.closest('.library-card')?.classList.toggle('is-archived', result.is_archived); if (action === 'favorite') button.textContent = result.is_favorite ? '★' : '☆'; } catch (error) { alert(error.message); }
  }));

  const resultBox = document.querySelector('[data-ai-result]');
  document.querySelectorAll('[data-summarize]').forEach(button => button.addEventListener('click', async () => { button.disabled = true; button.textContent = 'Summarizing…'; try { const data = await request(`/api/memories/${button.dataset.noteId}/summarize`, { method: 'POST' }); resultBox.innerHTML = `<div class="result-block"><span class="provenance-label">${data.source === 'local' ? 'LOCAL FALLBACK SUMMARY' : 'AI SUMMARY'}</span><p>${escapeHtml(data.summary)}</p><ul>${data.key_points.map(point => `<li>${escapeHtml(point)}</li>`).join('')}</ul></div>`; } catch (error) { resultBox.innerHTML = `<p class="field-error">${escapeHtml(error.message)}</p>`; } finally { button.disabled = false; button.textContent = '✦ Summarize memory'; } }));
  document.querySelectorAll('[data-extract-actions]').forEach(button => button.addEventListener('click', async () => { button.disabled = true; button.textContent = 'Finding actions…'; try { const data = await request(`/api/memories/${button.dataset.noteId}/extract-actions`, { method: 'POST' }); if (!data.actions.length) resultBox.innerHTML = '<p class="muted-copy">No clear actions were found in this memory.</p>'; else { resultBox.innerHTML = `<div class="result-block"><span class="provenance-label">SUGGESTED ACTIONS · REVIEW BEFORE SAVING</span>${data.actions.map((action, index) => `<label class="suggestion-row"><input type="checkbox" checked data-suggested-index="${index}"><span><strong>${escapeHtml(action.title)}</strong><small>${escapeHtml(action.description || '')}</small></span></label>`).join('')}<button class="btn btn-primary btn-sm mt-3" data-confirm-actions>Confirm selected tasks</button></div>`; resultBox.dataset.actions = JSON.stringify(data.actions); resultBox.querySelector('[data-confirm-actions]').addEventListener('click', async event => { const selected = [...resultBox.querySelectorAll('[data-suggested-index]:checked')].map(input => data.actions[Number(input.dataset.suggestedIndex)]); event.target.disabled = true; const saved = await request(`/api/assistant/confirm-actions/${button.dataset.noteId}`, { method: 'POST', body: JSON.stringify({ actions: selected }) }); event.target.textContent = `${saved.created.length} task${saved.created.length === 1 ? '' : 's'} saved`; }); } } catch (error) { resultBox.innerHTML = `<p class="field-error">${escapeHtml(error.message)}</p>`; } finally { button.disabled = false; button.textContent = '→ Find possible actions'; } }));

  const assistantForm = document.querySelector('[data-assistant-form]'); const conversation = document.querySelector('[data-conversation]');
  const askAssistant = question => { const user = document.createElement('div'); user.className = 'user-message'; user.innerHTML = `<span class="message-label">YOU</span><p>${escapeHtml(question)}</p>`; conversation.appendChild(user); const pending = document.createElement('div'); pending.className = 'assistant-message'; pending.innerHTML = '<span class="message-label">ECHOGUARD</span><p>Searching your saved memories…</p>'; conversation.appendChild(pending); request('/api/assistant/ask', { method: 'POST', body: JSON.stringify({ question }) }).then(data => { pending.querySelector('p').textContent = data.answer; }).catch(error => { pending.querySelector('p').textContent = error.message; }); };
  if (assistantForm) assistantForm.addEventListener('submit', event => { event.preventDefault(); const input = assistantForm.elements.question; const question = input.value.trim(); if (question) { askAssistant(question); input.value = ''; } });
  document.querySelectorAll('[data-prompt]').forEach(button => button.addEventListener('click', () => { const input = assistantForm?.elements.question; if (input) { input.value = button.dataset.prompt; input.focus(); } }));

  const taskForm = document.querySelector('[data-task-form]');
  if (taskForm) taskForm.addEventListener('submit', async event => { event.preventDefault(); const form = new FormData(taskForm); const status = taskForm.querySelector('[data-task-status]'); try { await request('/api/tasks', { method: 'POST', body: JSON.stringify({ title: form.get('title'), priority: form.get('priority'), due_at: form.get('due_at') || null, reminder_at: form.get('reminder_at') || null }) }); status.textContent = 'Task saved.'; setTimeout(() => window.location.reload(), 350); } catch (error) { status.textContent = error.message; } });
  document.querySelectorAll('[data-toggle-task]').forEach(button => button.addEventListener('click', async () => { const row = button.closest('[data-task-id]'); try { const data = await request(`/api/tasks/${row.dataset.taskId}/toggle`, { method: 'POST' }); row.classList.toggle('is-complete', data.task.status === 'completed'); button.textContent = data.task.status === 'completed' ? '✓' : ''; } catch (error) { alert(error.message); } }));
  document.querySelectorAll('[data-delete-task]').forEach(button => button.addEventListener('click', async () => { const row = button.closest('[data-task-id]'); if (!confirm('Delete this task?')) return; try { await request(`/api/tasks/${row.dataset.taskId}`, { method: 'DELETE' }); row.remove(); } catch (error) { alert(error.message); } }));
  document.querySelectorAll('[data-edit-task]').forEach(button => button.addEventListener('click', () => { const form = button.closest('[data-task-id]').querySelector('[data-task-edit]'); form.hidden = !form.hidden; }));
  document.querySelectorAll('[data-save-edit]').forEach(button => button.addEventListener('click', async () => { const row = button.closest('[data-task-id]'); const edit = row.querySelector('[data-task-edit]'); try { await request(`/api/tasks/${row.dataset.taskId}`, { method: 'PATCH', body: JSON.stringify({ title: edit.querySelector('[data-edit-title]').value, priority: edit.querySelector('[data-edit-priority]').value, due_at: edit.querySelector('[data-edit-due]').value || null, reminder_at: edit.querySelector('[data-edit-reminder]').value || null }) }); window.location.reload(); } catch (error) { alert(error.message); } }));
  document.querySelector('[data-add-task]')?.addEventListener('click', () => document.querySelector('#task-title')?.focus());
  function escapeHtml(value) { return String(value ?? '').replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char])); }
})();
