document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const rtspStatus = document.getElementById('rtsp-status');
    const logoDot = document.querySelector('.logo-dot');
    const fpsCounter = document.getElementById('fps-counter');
    const videoStream = document.getElementById('video-stream');
    const pausedOverlay = document.getElementById('paused-overlay');
    const activeCamTitle = document.getElementById('active-cam-title');
    
    const cameraSelect = document.getElementById('camera-select');
    const btnManageCameras = document.getElementById('btn-manage-cameras');
    const modalCameras = document.getElementById('modal-cameras');
    const modalClose = document.getElementById('modal-close');
    
    const formAddCamera = document.getElementById('form-add-camera');
    const camEditId = document.getElementById('cam-edit-id');
    const camName = document.getElementById('cam-name');
    const camUrl = document.getElementById('cam-url');
    const camLocation = document.getElementById('cam-location');
    const btnSaveCam = document.getElementById('btn-save-cam');
    const btnCancelEdit = document.getElementById('btn-cancel-edit');
    const cameraListContainer = document.getElementById('camera-list');
    
    const btnPause = document.getElementById('btn-pause');
    const btnReset = document.getElementById('btn-reset');
    const btnClearLogs = document.getElementById('btn-clear-logs');
    
    const statCurrent = document.getElementById('stat-current');
    const statPeak = document.getElementById('stat-peak');
    const statFrames = document.getElementById('stat-frames');
    
    const sliderConf = document.getElementById('slider-conf');
    const sliderNms = document.getElementById('slider-nms');
    const confVal = document.getElementById('conf-val');
    const nmsVal = document.getElementById('nms-val');
    const logsContainer = document.getElementById('logs-container');

    // Chart Setup
    const ctx = document.getElementById('liveChart').getContext('2d');
    const neonGradient = ctx.createLinearGradient(0, 0, 0, 200);
    neonGradient.addColorStop(0, 'rgba(0, 240, 255, 0.2)');
    neonGradient.addColorStop(1, 'rgba(0, 240, 255, 0)');

    const maxChartDataPoints = 30;
    const chartLabels = Array(maxChartDataPoints).fill('');
    const chartData = Array(maxChartDataPoints).fill(0);

    const liveChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartLabels,
            datasets: [{
                label: 'Person Count',
                data: chartData,
                borderColor: '#00f0ff',
                borderWidth: 2,
                pointBackgroundColor: '#00f0ff',
                pointHoverRadius: 6,
                backgroundColor: neonGradient,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { display: false } },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { stepSize: 1, color: '#64748b', font: { family: 'Orbitron', size: 10 } },
                    min: 0,
                    suggestedMax: 5
                }
            },
            animation: { duration: 300 }
        }
    });

    let displayedLogKeys = new Set();
    let isPausedState = false;

    // Load & Render Cameras
    function loadCameras() {
        fetch('/api/cameras')
            .then(res => res.json())
            .then(data => {
                const { cameras, active_id } = data;
                
                // Populate Dropdown
                cameraSelect.innerHTML = '';
                cameras.forEach(cam => {
                    const opt = document.createElement('option');
                    opt.value = cam.id;
                    opt.textContent = `${cam.name} (${cam.location || 'Default'})`;
                    if (cam.id === active_id) opt.selected = true;
                    cameraSelect.appendChild(opt);
                });

                // Populate Modal List
                renderCameraListModal(cameras, active_id);
            })
            .catch(err => console.error("Error loading cameras:", err));
    }

    function renderCameraListModal(cameras, active_id) {
        cameraListContainer.innerHTML = '';
        cameras.forEach(cam => {
            const item = document.createElement('div');
            item.className = 'camera-item';
            
            const isActive = cam.id === active_id;
            
            item.innerHTML = `
                <div class="camera-item-info">
                    <h4>${cam.name} ${isActive ? '<span class="text-cyan">(ACTIVE)</span>' : ''}</h4>
                    <p><strong>RTSP:</strong> ${cam.url}</p>
                    ${cam.location ? `<p><strong>Location:</strong> ${cam.location}</p>` : ''}
                </div>
                <div class="camera-item-actions">
                    <button class="btn btn-sm btn-secondary btn-edit-cam" data-id="${cam.id}">✏️ Edit</button>
                    <button class="btn btn-sm btn-danger btn-delete-cam" data-id="${cam.id}">🗑️ Delete</button>
                </div>
            `;

            // Bind Edit button
            item.querySelector('.btn-edit-cam').addEventListener('click', () => {
                camEditId.value = cam.id;
                camName.value = cam.name;
                camUrl.value = cam.url;
                camLocation.value = cam.location || '';
                btnSaveCam.textContent = '💾 Save Changes';
                btnCancelEdit.classList.remove('hidden');
            });

            // Bind Delete button
            item.querySelector('.btn-delete-cam').addEventListener('click', () => {
                if (confirm(`Are you sure you want to delete camera "${cam.name}"?`)) {
                    fetch('/api/cameras/delete', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ id: cam.id })
                    })
                    .then(res => res.json())
                    .then(data => {
                        if (data.status === 'success') {
                            loadCameras();
                            refreshStream();
                        } else {
                            alert(data.message);
                        }
                    });
                }
            });

            cameraListContainer.appendChild(item);
        });
    }

    // Switch Camera Dropdown Change
    cameraSelect.addEventListener('change', () => {
        const selectedId = cameraSelect.value;
        if (!selectedId) return;

        fetch('/api/cameras/switch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: selectedId })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                refreshStream();
                appendLog("[System]", `Switched stream to selected camera.`, "system-entry");
            }
        });
    });

    // Save/Add Camera Form
    formAddCamera.addEventListener('submit', (e) => {
        e.preventDefault();
        const id = camEditId.value;
        const name = camName.value.trim();
        const url = camUrl.value.trim();
        const location = camLocation.value.trim();

        const endpoint = id ? '/api/cameras/edit' : '/api/cameras/add';
        const payload = id ? { id, name, url, location } : { name, url, location };

        fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                resetCameraForm();
                loadCameras();
                refreshStream();
            } else {
                alert(data.message);
            }
        });
    });

    btnCancelEdit.addEventListener('click', resetCameraForm);

    function resetCameraForm() {
        camEditId.value = '';
        camName.value = '';
        camUrl.value = '';
        camLocation.value = '';
        btnSaveCam.textContent = '➕ Add Camera';
        btnCancelEdit.classList.add('hidden');
    }

    // Modal Control
    btnManageCameras.addEventListener('click', () => modalCameras.classList.remove('hidden'));
    modalClose.addEventListener('click', () => modalCameras.classList.add('hidden'));

    // Threshold Sliders
    function saveSettings() {
        const conf = parseFloat(sliderConf.value);
        const nms = parseFloat(sliderNms.value);
        confVal.textContent = `${Math.round(conf * 100)}%`;
        nmsVal.textContent = `${Math.round(nms * 100)}%`;

        fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ conf_threshold: conf, nms_threshold: nms })
        });
    }

    sliderConf.addEventListener('input', () => confVal.textContent = `${Math.round(parseFloat(sliderConf.value) * 100)}%`);
    sliderConf.addEventListener('change', saveSettings);
    sliderNms.addEventListener('input', () => nmsVal.textContent = `${Math.round(parseFloat(sliderNms.value) * 100)}%`);
    sliderNms.addEventListener('change', saveSettings);

    // Pause/Resume
    btnPause.addEventListener('click', () => {
        fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'toggle_pause' })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') updatePauseUI(data.paused);
        });
    });

    function updatePauseUI(isPaused) {
        isPausedState = isPaused;
        if (isPaused) {
            btnPause.innerHTML = '<span class="btn-icon">▶</span> Resume Stream';
            btnPause.classList.replace('btn-primary', 'btn-secondary');
            pausedOverlay.classList.remove('hidden');
            logoDot.className = 'logo-dot pulse-paused';
            rtspStatus.textContent = 'Paused';
            rtspStatus.className = 'value text-warning';
        } else {
            btnPause.innerHTML = '<span class="btn-icon">⏸</span> Pause Stream';
            btnPause.classList.replace('btn-secondary', 'btn-primary');
            pausedOverlay.classList.add('hidden');
            logoDot.className = 'logo-dot pulse-active';
            rtspStatus.textContent = 'Connected';
            rtspStatus.className = 'value text-green';
        }
    }

    function refreshStream() {
        const timestamp = new Date().getTime();
        videoStream.src = `/video_feed?t=${timestamp}`;
    }

    btnReset.addEventListener('click', refreshStream);
    btnClearLogs.addEventListener('click', () => {
        logsContainer.innerHTML = '';
        displayedLogKeys.clear();
    });

    function appendLog(timeStr, message, typeClass, count = null) {
        const entry = document.createElement('div');
        entry.className = `log-entry ${typeClass}`;
        const countHtml = count !== null ? `<span class="log-count">Count: ${count}</span>` : '';
        entry.innerHTML = `<span class="log-time">[${timeStr}]</span> <span class="log-msg">${message}</span> ${countHtml}`;
        logsContainer.prepend(entry);
        if (logsContainer.children.length > 50) logsContainer.removeChild(logsContainer.lastChild);
    }

    // Polling Loop
    function pollTelemetry() {
        fetch('/api/stats')
            .then(res => res.json())
            .then(data => {
                if (data.active_camera) {
                    activeCamTitle.textContent = `${data.active_camera.name.toUpperCase()} FEED`;
                }

                if (!data.connected) {
                    rtspStatus.textContent = 'Reconnecting...';
                    rtspStatus.className = 'value text-danger';
                    logoDot.className = 'logo-dot pulse-offline';
                } else if (!isPausedState) {
                    rtspStatus.textContent = 'Connected';
                    rtspStatus.className = 'value text-green';
                    logoDot.className = 'logo-dot pulse-active';
                }

                fpsCounter.textContent = `${data.fps} FPS`;
                statCurrent.textContent = data.current_count;
                statPeak.textContent = data.peak_count;
                statFrames.textContent = data.total_frames;

                if (!data.paused) {
                    chartData.push(data.current_count);
                    chartData.shift();
                    liveChart.update('none');
                }

                data.logs.forEach(log => {
                    const key = `${log.timestamp}-${log.count}-${log.camera}`;
                    if (!displayedLogKeys.has(key)) {
                        displayedLogKeys.add(key);
                        const typeClass = log.event.toLowerCase() === 'detection' ? 'detection' : 'clearance';
                        const message = log.event.toLowerCase() === 'detection' 
                            ? `Person detected on ${log.camera || 'camera'}` 
                            : `Clearance on ${log.camera || 'camera'}`;
                        appendLog(log.timestamp, message, typeClass, log.count);
                    }
                });
            });
    }

    // Initialize
    loadCameras();
    saveSettings();
    setInterval(pollTelemetry, 500);
});
