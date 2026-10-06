(() => {
  const fileInput = document.getElementById('file');
  const drop = document.getElementById('drop');
  const fileLabel = document.getElementById('fileLabel');
  const startBtn = document.getElementById('startBtn');
  const flowCard = document.getElementById('flowCard');
  const resultCard = document.getElementById('resultCard');
  const errorCard = document.getElementById('errorCard');
  const barFill = document.getElementById('barFill');
  const statusText = document.getElementById('statusText');
  const jobFile = document.getElementById('jobFile');
  const scoresEl = document.getElementById('scores');
  const notesEl = document.getElementById('notes');
  const transcriptEl = document.getElementById('transcript');
  const providerEl = document.getElementById('provider');
  const errorText = document.getElementById('errorText');

  let selected = null;
  let pollTimer = null;

  function resetUI() {
    flowCard.hidden = true;
    resultCard.hidden = true;
    errorCard.hidden = true;
    barFill.style.width = '0%';
    statusText.textContent = 'Waiting…';
    document.querySelectorAll('.steps li').forEach((li) => {
      li.classList.remove('active', 'done');
    });
  }

  function setStep(step) {
    const order = ['upload', 'load', 'transcribe', 'evaluate', 'done'];
    const idx = order.indexOf(step);
    document.querySelectorAll('.steps li').forEach((li) => {
      const s = li.getAttribute('data-step');
      const i = order.indexOf(s);
      li.classList.remove('active', 'done');
      if (step === 'error') return;
      if (i < idx || step === 'done') li.classList.add('done');
      if (s === step) li.classList.add('active');
    });
  }

  function showScores(scores) {
    scoresEl.innerHTML = '';
    Object.keys(scores || {}).forEach((k) => {
      const div = document.createElement('div');
      div.className = 'score';
      div.innerHTML = `<div class="k">${k}</div><div class="v">${scores[k]}</div>`;
      scoresEl.appendChild(div);
    });
  }

  drop.addEventListener('click', () => fileInput.click());
  drop.addEventListener('dragover', (e) => {
    e.preventDefault();
    drop.classList.add('drag');
  });
  drop.addEventListener('dragleave', () => drop.classList.remove('drag'));
  drop.addEventListener('drop', (e) => {
    e.preventDefault();
    drop.classList.remove('drag');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      selected = e.dataTransfer.files[0];
      fileLabel.textContent = selected.name;
      startBtn.disabled = false;
    }
  });
  fileInput.addEventListener('change', () => {
    selected = fileInput.files && fileInput.files[0] ? fileInput.files[0] : null;
    fileLabel.textContent = selected ? selected.name : 'Choose recording';
    startBtn.disabled = !selected;
  });

  async function poll(jobId) {
    const r = await fetch('/api/jobs/' + jobId);
    const j = await r.json();
    if (!j.ok && j.error === 'Unknown job') throw new Error('Job lost');

    setStep(j.step || 'load');
    barFill.style.width = (j.progress || 0) + '%';
    statusText.textContent = j.step_label || j.status || 'Working…';
    jobFile.textContent = j.filename || '';

    if (j.status === 'done') {
      clearInterval(pollTimer);
      pollTimer = null;
      flowCard.hidden = false;
      resultCard.hidden = false;
      providerEl.textContent =
        'ASR: ' + (j.asr_provider || 'ethio-asr') +
        ' · Scorer: ' + (j.provider || 'unknown');
      showScores(j.scores || {});
      notesEl.textContent = j.notes || '';
      const tr = j.transcript || '(empty)';
      transcriptEl.textContent = tr;
      let eth = 0;
      for (const ch of tr) {
        const c = ch.codePointAt(0);
        if (c >= 0x1200 && c <= 0x137F) eth++;
      }
      if (tr.length > 40 && eth < 8) {
        notesEl.textContent = (notesEl.textContent || '')
          + ' ⚠ Transcript still weak — try another clearer recording.';
      }
      startBtn.disabled = false;
      return;
    }
    if (j.status === 'error') {
      clearInterval(pollTimer);
      pollTimer = null;
      errorCard.hidden = false;
      errorText.textContent = j.error || 'Unknown error';
      startBtn.disabled = false;
      return;
    }
  }

  startBtn.addEventListener('click', async () => {
    if (!selected) return;
    resetUI();
    flowCard.hidden = false;
    setStep('upload');
    barFill.style.width = '5%';
    statusText.textContent = 'Uploading recording…';
    startBtn.disabled = true;

    const fd = new FormData();
    fd.append('file', selected);
    fd.append('caller', document.getElementById('caller').value || '');
    fd.append('agent_ext', document.getElementById('agent').value || '');

    try {
      const r = await fetch('/api/jobs', { method: 'POST', body: fd });
      const j = await r.json();
      if (!r.ok || !j.job_id) throw new Error(j.error || 'Upload failed');
      statusText.textContent = 'Queued…';
      pollTimer = setInterval(() => {
        poll(j.job_id).catch((err) => {
          clearInterval(pollTimer);
          pollTimer = null;
          errorCard.hidden = false;
          errorText.textContent = String(err.message || err);
          startBtn.disabled = false;
        });
      }, 800);
      await poll(j.job_id);
    } catch (err) {
      errorCard.hidden = false;
      errorText.textContent = String(err.message || err);
      startBtn.disabled = false;
    }
  });

  document.getElementById('againBtn').addEventListener('click', () => {
    resetUI();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
  document.getElementById('retryBtn').addEventListener('click', () => {
    resetUI();
  });
})();
