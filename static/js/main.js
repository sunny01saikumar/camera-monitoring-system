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
    const btnManageFaces = document.getElementById('btn-manage-faces');
    const btnManageSmtp = document.getElementById('btn-manage-smtp');
    
    const modalCameras = document.getElementById('modal-cameras');
    const modalFaces = document.getElementById('modal-faces');
    const modalSmtp = document.getElementById('modal-smtp');
    
    const formAddCamera = document.getElementById('form-add-camera');
    const camEditId = document.getElementById('cam-edit-id');
    const camName = document.getElementById('cam-name');
    const camUrl = document.getElementById('cam-url');
    const camLocation = document.getElementById('cam-location');
    const btnSaveCam = document.getElementById('btn-save-cam');
    const btnCancelEdit = document.getElementById('btn-cancel-edit');
    const cameraListContainer = document.getElementById('camera-list');
    
    const formUploadFace = document.getElementById('form-upload-face');
    const facePersonName = document.getElementById('face-person-name');
    const faceFile = document.getElementById('face-file');
    const facesListContainer = document.getElementById('faces-list');
    
    const formSmtp = document.getElementById('form-smtp');
    const smtpEnabled = document.getElementById('smtp-enabled');
    const smtpSender = document.getElementById('smtp-sender');
    const smtpPassword = document.getElementById('smtp-password');
    const smtpRecipient = document.getElementById('smtp-recipient');
    const smtpCooldown = document.getElementById('smtp-cooldown');
    
    const osgiServicesContainer = document.getElementById('osgi-services-container');
    const btnPause = document.getElementById('btn-pause');
    const btnReset = document.getElementById('btn-reset');
    const btnClearLogs = document.getElementById('btn-clear-logs');
    
    const statCurrent = document.getElementById('stat-current');
    const statPeak = document.getElementById('stat-peak');
    const statFrames = document.getElementById('stat-frames');
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
                cameraSelect.innerHTML = '';
                cameras.forEach(cam => {
                    const opt = document.createElement('option');
                    opt.value = cam.id;
                    opt.textContent = `${cam.name} (${cam.location || 'Default'})`;
                    if (cam.id === active_id) opt.selected = true;
                    cameraSelect.appendChild(opt);
                });
                renderCameraListModal(cameras, active_id);
            });
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
                </div>
                <div class="camera-item-actions">
                    <button class="btn btn-sm btn-secondary btn-edit-cam" data-id="${cam.id}">✏️ Edit</button>
                    <button class="btn btn-sm btn-danger btn-delete-cam" data-id="${cam.id}">🗑️ Delete</button>
                </div>
            `;
            item.querySelector('.btn-edit-cam').addEventListener('click', () => {
                camEditId.value = cam.id;
                camName.value = cam.name;
                camUrl.value = cam.url;
                camLocation.value = cam.location || '';
                btnSaveCam.textContent = '💾 Save Changes';
                btnCancelEdit.classList.remove('hidden');
            });
            item.querySelector('.btn-delete-cam').addEventListener('click', () => {
                if (confirm(`Delete camera "${cam.name}"?`)) {
                    fetch('/api/cameras/delete', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ id: cam.id })
                    }).then(() => { loadCameras(); refreshStream(); });
                }
            });
            cameraListContainer.appendChild(item);
        });
    }

    cameraSelect.addEventListener('change', () => {
        const selectedId = cameraSelect.value;
        if (!selectedId) return;
        fetch('/api/cameras/switch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: selectedId })
        }).then(() => { refreshStream(); appendLog("[OSGi Core]", "Switched active camera.", "system-entry"); });
    });

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
        }).then(() => { resetCameraForm(); loadCameras(); refreshStream(); });
    });

    btnCancelEdit.addEventListener('click', resetCameraForm);
    function resetCameraForm() {
        camEditId.value = ''; camName.value = ''; camUrl.value = ''; camLocation.value = '';
        btnSaveCam.textContent = '➕ Add Camera'; btnCancelEdit.classList.add('hidden');
    }

    // Render OSGi Service Controls (On-Demand Service Execution)
    function renderOSGiServices(services) {
        osgiServicesContainer.innerHTML = '';
        const serviceNames = {
            "camera_service": "Camera Ingestion & Proxy Service",
            "ai_analytics_service": "YOLOv8 + Known/Unknown AI Service",
            "gmail_notifier_service": "Gmail SMTP Alert Service"
        };

        Object.keys(services).forEach(service_id => {
            const state = services[service_id];
            const isActive = state === "ACTIVE";
            const item = document.createElement('div');
            item.className = 'osgi-service-item';
            
            item.innerHTML = `
                <div class="osgi-service-info">
                    <h4>${serviceNames[service_id] || service_id}</h4>
                    <p>Bundle State: <span class="${isActive ? 'service-status-active' : 'service-status-resolved'}">[${state}]</span></p>
                </div>
                <button class="btn btn-sm ${isActive ? 'btn-danger' : 'btn-primary'} btn-toggle-osgi" data-id="${service_id}" data-active="${isActive}">
                    ${isActive ? 'Deactivate' : 'Execute (Start)'}
                </button>
            `;

            item.querySelector('.btn-toggle-osgi').addEventListener('click', (e) => {
                const sid = e.target.getAttribute('data-id');
                const active = e.target.getAttribute('data-active') === 'true';
                fetch('/api/osgi/toggle', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ service_id: sid, enable: !active })
                }).then(() => pollTelemetry());
            });

            osgiServicesContainer.appendChild(item);
        });
    }

    // Known Faces Gallery
    function loadFaces() {
        fetch('/api/faces')
            .then(res => res.json())
            .then(data => {
                facesListContainer.innerHTML = '';
                if (data.faces.length === 0) {
                    facesListContainer.innerHTML = '<p style="color:#64748b; font-size:12px;">No known faces registered. Upload photos above.</p>';
                    return;
                }
                data.faces.forEach(face => {
                    const item = document.createElement('div');
                    item.className = 'camera-item';
                    item.innerHTML = `
                        <div class="camera-item-info">
                            <h4>KNOWN: ${face.name}</h4>
                            <p>Profile: ${face.filename}</p>
                        </div>
                        <span class="hud-badge">REGISTERED</span>
                    `;
                    facesListContainer.appendChild(item);
                });
            });
    }

    formUploadFace.addEventListener('submit', (e) => {
        e.preventDefault();
        const formData = new FormData();
        formData.append('name', facePersonName.value.trim());
        formData.append('file', faceFile.files[0]);

        fetch('/api/faces/upload', {
            method: 'POST',
            body: formData
        }).then(res => res.json()).then(data => {
            if (data.status === 'success') {
                facePersonName.value = ''; faceFile.value = '';
                loadFaces();
                appendLog("[AI Analytics]", `New known face profile registered: ${data.name}`, "system-entry");
            }
        });
    });

    // Gmail SMTP Settings
    function loadSMTP() {
        fetch('/api/smtp')
            .then(res => res.json())
            .then(data => {
                smtpEnabled.checked = data.enabled || false;
                smtpSender.value = data.sender_email || '';
                smtpPassword.value = data.app_password || '';
                smtpRecipient.value = data.recipient_email || '';
                smtpCooldown.value = data.cooldown_seconds || 180;
            });
    }

    formSmtp.addEventListener('submit', (e) => {
        e.preventDefault();
        const payload = {
            enabled: smtpEnabled.checked,
            sender_email: smtpSender.value.trim(),
            app_password: smtpPassword.value.trim(),
            recipient_email: smtpRecipient.value.trim(),
            cooldown_seconds: parseInt(smtpCooldown.value) || 180
        };

        fetch('/api/smtp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }).then(res => res.json()).then(data => {
            alert(data.message);
            modalSmtp.classList.add('hidden');
        });
    });

    // Modal Triggers
    btnManageCameras.addEventListener('click', () => modalCameras.classList.remove('hidden'));
    btnManageFaces.addEventListener('click', () => { loadFaces(); modalFaces.classList.remove('hidden'); });
    btnManageSmtp.addEventListener('click', () => { loadSMTP(); modalSmtp.classList.remove('hidden'); });

    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', () => {
            modalCameras.classList.add('hidden');
            modalFaces.classList.add('hidden');
            modalSmtp.classList.add('hidden');
        });
    });

    // Stream & Controls
    btnPause.addEventListener('click', () => {
        fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'toggle_pause' })
        }).then(res => res.json()).then(data => {
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
        } else {
            btnPause.innerHTML = '<span class="btn-icon">⏸</span> Pause Stream';
            btnPause.classList.replace('btn-secondary', 'btn-primary');
            pausedOverlay.classList.add('hidden');
            logoDot.className = 'logo-dot pulse-active';
            rtspStatus.textContent = 'Connected';
        }
    }

    function refreshStream() {
        videoStream.src = `/video_feed?t=${new Date().getTime()}`;
    }

    btnReset.addEventListener('click', refreshStream);
    btnClearLogs.addEventListener('click', () => { logsContainer.innerHTML = ''; displayedLogKeys.clear(); });

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

                // Render OSGi Services
                if (data.osgi_services) {
                    renderOSGiServices(data.osgi_services);
                }

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
                        appendLog(log.timestamp, log.details || 'Event logged', typeClass, log.count);
                    }
                });
            });
    }

    // Initialize
    loadCameras();
    setInterval(pollTelemetry, 500);
});
