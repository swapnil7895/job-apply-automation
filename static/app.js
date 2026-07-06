document.addEventListener("DOMContentLoaded", () => {
    // Current active platform ('linkedin' or 'naukri')
    let currentPlatform = 'linkedin';
    let pollInterval = null;
    let wasRunning = false;

    // --- Tab Switching ---
    const navBtns = document.querySelectorAll('.nav-btn');
    const panels = document.querySelectorAll('.panel');

    navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-target');
            if (!targetId) return; // Skip if it's not a tab button (like theme toggle)

            // Update active button
            navBtns.forEach(b => { if(b.hasAttribute('data-target')) b.classList.remove('active') });
            btn.classList.add('active');

            // Update active panel
            panels.forEach(p => p.classList.remove('active'));
            document.getElementById(targetId).classList.add('active');

            if (targetId === 'linkedin-panel') {
                currentPlatform = 'linkedin';
                loadConfig('linkedin');
                checkLoginStatus('linkedin');
                startStatusPolling();
                consoleCard.style.display = 'flex';
            } else if (targetId === 'naukri-panel') {
                currentPlatform = 'naukri';
                loadConfig('naukri');
                checkLoginStatus('naukri');
                startStatusPolling();
                consoleCard.style.display = 'flex';
            } else if (targetId === 'reports-panel') {
                loadReports();
                stopStatusPolling();
                consoleCard.style.display = 'none';
            } else if (targetId === 'settings-panel') {
                loadEmailConfig();
                stopStatusPolling();
                consoleCard.style.display = 'none'; // hide terminal on settings page
            }
        });
    });

    // --- UI Toggles ---
    const sidebar = document.getElementById('sidebar');
    const toggleSidebarBtn = document.getElementById('toggle-sidebar-btn');
    if (toggleSidebarBtn && sidebar) {
        toggleSidebarBtn.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
        });
    }

    // --- Theme Toggle ---
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    const themeIcon = document.getElementById('theme-icon');
    const themeText = document.getElementById('theme-text');
    
    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'dark';
    if (savedTheme === 'light') {
        document.documentElement.setAttribute('data-theme', 'light');
        themeIcon.textContent = '🌙';
        themeText.textContent = 'Dark Mode';
    } else {
        themeIcon.textContent = '☀️';
        themeText.textContent = 'Light Mode';
    }

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            if (currentTheme === 'light') {
                document.documentElement.removeAttribute('data-theme');
                localStorage.setItem('theme', 'dark');
                themeIcon.textContent = '☀️';
                themeText.textContent = 'Light Mode';
            } else {
                document.documentElement.setAttribute('data-theme', 'light');
                localStorage.setItem('theme', 'light');
                themeIcon.textContent = '🌙';
                themeText.textContent = 'Dark Mode';
            }
        });
    }

    const consoleHeaderToggle = document.getElementById('console-header-toggle');
    const consoleOutput = document.getElementById('console-output');
    const consoleCard = document.querySelector('.console-card');
    if (consoleHeaderToggle && consoleOutput) {
        consoleHeaderToggle.addEventListener('click', () => {
            consoleCard.classList.toggle('collapsed');
        });
    }

    // --- Login Management ---
    async function checkLoginStatus(platform) {
        const badge = document.getElementById(`${platform}-login-status`);
        const statusText = badge?.querySelector('.status-text');
        const indicator = badge?.querySelector('.status-indicator');
        const userNameSpan = badge?.querySelector('.user-name');
        
        const startBtn = document.getElementById(`btn-start-${platform}`);
        const loginBtn = document.getElementById(`btn-login-${platform}`);
        const logoutBtn = document.getElementById(`${platform}-logout-btn`);
        
        // Handle both old and new HTML gracefully
        if (!badge) return;
        
        if (statusText && indicator) {
            badge.className = 'login-status-badge status-checking';
            statusText.textContent = 'Checking...';
            indicator.style.backgroundColor = 'var(--text-secondary)';
            if (userNameSpan) userNameSpan.textContent = '';
        } else {
            badge.className = 'login-status-badge status-checking';
            badge.textContent = 'Checking Login...';
        }
        
        if (startBtn) startBtn.disabled = true;

        try {
            const res = await fetch(`/api/login/status/${platform}`);
            if (res.ok) {
                const data = await res.json();
                if (data.logged_in) {
                    badge.className = 'login-status-badge status-logged-in';
                    if (statusText) {
                        statusText.textContent = 'Logged In';
                        indicator.style.backgroundColor = 'var(--success)';
                        if (userNameSpan) {
                            userNameSpan.textContent = data.user_name ? `(${data.user_name})` : '(Name Hidden)';
                        }
                    } else {
                        badge.textContent = '🟢 Logged In' + (data.user_name ? ` (${data.user_name})` : '');
                    }
                    if (startBtn) startBtn.disabled = false;
                    if (loginBtn) loginBtn.style.display = 'none';
                    if (logoutBtn) logoutBtn.style.display = 'inline-block';
                } else {
                    badge.className = 'login-status-badge status-logged-out';
                    if (statusText) {
                        statusText.textContent = 'Not Logged In';
                        indicator.style.backgroundColor = 'var(--danger)';
                    } else {
                        badge.textContent = '🔴 Not Logged In';
                    }
                    if (startBtn) startBtn.disabled = true;
                    if (loginBtn) loginBtn.style.display = 'inline-block';
                    if (logoutBtn) logoutBtn.style.display = 'none';
                }
            }
        } catch (e) {
            if (statusText) {
                statusText.textContent = 'Error checking status';
                indicator.style.backgroundColor = 'var(--danger)';
            } else {
                badge.textContent = 'Error checking status';
            }
        }
    }

    async function triggerManualLogin(platform) {
        try {
            const res = await fetch(`/api/login/manual/${platform}`, { method: 'POST' });
            if (!res.ok) {
                alert("Failed to start manual login.");
            }
        } catch (e) {
            console.error(e);
        }
    }

    async function logoutPlatform(platform) {
        try {
            const badge = document.getElementById(`${platform}-login-status`);
            const statusText = badge?.querySelector('.status-text');
            if(badge) badge.className = 'login-status-badge status-checking';
            if(statusText) statusText.textContent = 'Logging out...';
            
            const res = await fetch(`/api/logout/${platform}`, { method: 'POST' });
            if (!res.ok) {
                alert("Failed to logout.");
            }
            checkLoginStatus(platform);
        } catch (e) {
            console.error(e);
        }
    }

    document.getElementById('btn-login-linkedin').addEventListener('click', () => triggerManualLogin('linkedin'));
    document.getElementById('btn-login-naukri').addEventListener('click', () => triggerManualLogin('naukri'));
    document.getElementById('linkedin-logout-btn')?.addEventListener('click', () => logoutPlatform('linkedin'));
    document.getElementById('naukri-logout-btn')?.addEventListener('click', () => logoutPlatform('naukri'));

    // --- Configuration Management ---
    async function loadConfig(platform) {
        try {
            const res = await fetch(`/api/config/${platform}`);
            if (res.ok) {
                const config = await res.json();
                populateForm(platform, config);
            }
        } catch (e) {
            console.error("Failed to load config for " + platform, e);
        }
    }

    function populateForm(platform, config) {
        const form = document.getElementById(`${platform}-form`);
        if (!form) return;

        form.elements[`${platform}_max_applications`].value = config.max_applications || 10;
        form.elements[`${platform}_date_posted`].value = config.date_posted || (platform === 'linkedin' ? 'Past week' : '7');
        
        const easyApplyInput = document.getElementById(`${platform}_easy_apply`);
        if (easyApplyInput) easyApplyInput.checked = config.easy_apply !== false; // default true
        
        const remoteOnlyInput = document.getElementById(`${platform}_remote_only`);
        if (remoteOnlyInput) remoteOnlyInput.checked = config.remote_only === true; // default false
        
        const keywords = config.job_keywords || config.keywords || [];
        form.elements[`${platform}_job_keywords`].value = Array.isArray(keywords) ? keywords.join(', ') : keywords;
        
        form.elements[`${platform}_location`].value = config.location || '';
        
        const salaryRangeSelect = form.elements[`${platform}_salary_range`];
        if (salaryRangeSelect) {
            salaryRangeSelect.value = config.salary_range || '';
        }
        
        const titleKeywords = config.title_filter_keywords || [];
        form.elements[`${platform}_title_filter`].value = Array.isArray(titleKeywords) ? titleKeywords.join(', ') : titleKeywords;
        
        const skillsProfile = config.skills_profile || {};
        const skillsInput = document.getElementById(`${platform}_skills_profile`);
        if (skillsInput) {
            skillsInput.value = Object.keys(skillsProfile).length > 0 ? JSON.stringify(skillsProfile, null, 2) : '';
        }
        
        const emailAlertsInput = document.getElementById(`${platform}_email_alerts`);
        if (emailAlertsInput) {
            emailAlertsInput.checked = config.email_alerts === true; // default false
            // Check if email config is done before allowing them to check it
            emailAlertsInput.addEventListener('change', (e) => {
                if (e.target.checked) {
                    const badge = document.getElementById('email-status-badge');
                    if (badge && badge.textContent.includes('Not Configured')) {
                        e.target.checked = false;
                        alert("Email configuration needs to be done from Settings first!");
                    }
                }
            });
        }
    }

    async function saveConfig(platform) {
        const form = document.getElementById(`${platform}-form`);
        const btn = form.querySelector('button[type="submit"]');
        const originalText = btn.textContent;
        
        const keywordsInput = form.elements[`${platform}_job_keywords`].value;
        const keywords = keywordsInput.split(',').map(k => k.trim()).filter(k => k);
        
        const titleFilterInput = form.elements[`${platform}_title_filter`].value;
        const titleFilterKeywords = titleFilterInput.split(',').map(k => k.trim()).filter(k => k);

        let skillsProfileObj = {};
        const skillsInput = document.getElementById(`${platform}_skills_profile`);
        if (skillsInput && skillsInput.value.trim() !== '') {
            try {
                skillsProfileObj = JSON.parse(skillsInput.value);
            } catch (e) {
                alert("Invalid JSON format in Skills Profile. Please fix it before saving.");
                btn.textContent = originalText;
                return;
            }
        }

        const newConfig = {
            max_applications: parseInt(form.elements[`${platform}_max_applications`].value) || 10,
            date_posted: form.elements[`${platform}_date_posted`].value,
            easy_apply: document.getElementById(`${platform}_easy_apply`) ? document.getElementById(`${platform}_easy_apply`).checked : true,
            remote_only: document.getElementById(`${platform}_remote_only`) ? document.getElementById(`${platform}_remote_only`).checked : false,
            email_alerts: document.getElementById(`${platform}_email_alerts`) ? document.getElementById(`${platform}_email_alerts`).checked : false,
            location: form.elements[`${platform}_location`].value,
            salary_range: form.elements[`${platform}_salary_range`] ? form.elements[`${platform}_salary_range`].value : '',
            title_filter_keywords: titleFilterKeywords,
            skills_profile: skillsProfileObj
        };

        if (platform === 'linkedin') {
            newConfig.job_keywords = keywords;
        } else {
            newConfig.keywords = keywords; // naukri config uses "keywords" instead of "job_keywords" usually
        }

        try {
            btn.textContent = "Saving...";
            const res = await fetch(`/api/config/${platform}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ config: newConfig })
            });

            if (res.ok) {
                btn.textContent = "Saved!";
                setTimeout(() => btn.textContent = originalText, 2000);
            } else {
                alert("Failed to save configuration");
                btn.textContent = originalText;
            }
        } catch (e) {
            console.error(e);
            alert("Error saving configuration");
            btn.textContent = originalText;
        }
    }

    document.getElementById('linkedin-form').addEventListener('submit', (e) => { e.preventDefault(); saveConfig('linkedin'); });
    document.getElementById('naukri-form').addEventListener('submit', (e) => { e.preventDefault(); saveConfig('naukri'); });

    // --- Email Settings Panel ---
    const emailForm = document.getElementById('email-settings-form');
    const btnTestEmail = document.getElementById('btn-test-email');
    const emailBadge = document.getElementById('email-status-badge');

    async function loadEmailConfig() {
        try {
            const res = await fetch('/api/email/config');
            if (res.ok) {
                const data = await res.json();
                if (data.configured) {
                    emailBadge.textContent = '✅ Configured';
                    emailBadge.className = 'login-status-badge status-logged-in';
                    document.getElementById('email_smtp_server').value = data.smtp_server;
                    document.getElementById('email_smtp_port').value = data.smtp_port;
                    document.getElementById('email_sender_email').value = data.sender_email;
                    document.getElementById('email_receiver_email').value = data.receiver_email || '';
                } else {
                    emailBadge.textContent = '❌ Not Configured';
                    emailBadge.className = 'login-status-badge status-logged-out';
                }
            }
        } catch (e) {
            console.error('Failed to load email config:', e);
        }
    }

    // Call it once on load to ensure state is ready for toggles on other tabs
    loadEmailConfig();

    if (emailForm) {
        emailForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = emailForm.querySelector('button[type="submit"]');
            const originalText = btn.textContent;
            btn.textContent = 'Saving...';
            btn.disabled = true;

            const config = {
                smtp_server: document.getElementById('email_smtp_server').value,
                smtp_port: parseInt(document.getElementById('email_smtp_port').value),
                sender_email: document.getElementById('email_sender_email').value,
                sender_password: document.getElementById('email_sender_password').value,
                receiver_email: document.getElementById('email_receiver_email').value || null
            };

            try {
                const res = await fetch('/api/email/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });
                if (res.ok) {
                    btn.textContent = 'Saved!';
                    loadEmailConfig();
                } else {
                    alert('Failed to save settings');
                    btn.textContent = originalText;
                }
            } catch (err) {
                alert('Error saving settings');
                btn.textContent = originalText;
            }
            setTimeout(() => {
                btn.textContent = originalText;
                btn.disabled = false;
            }, 2000);
        });
    }

    if (btnTestEmail) {
        btnTestEmail.addEventListener('click', async () => {
            if (!emailForm.reportValidity()) return;
            
            const originalText = btnTestEmail.textContent;
            btnTestEmail.textContent = 'Sending...';
            btnTestEmail.disabled = true;

            const config = {
                smtp_server: document.getElementById('email_smtp_server').value,
                smtp_port: parseInt(document.getElementById('email_smtp_port').value),
                sender_email: document.getElementById('email_sender_email').value,
                sender_password: document.getElementById('email_sender_password').value,
                receiver_email: document.getElementById('email_receiver_email').value || null
            };

            try {
                const res = await fetch('/api/email/test', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });
                const data = await res.json();
                if (res.ok) {
                    alert('Success: ' + data.message);
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (err) {
                alert('Error testing email connection');
            }
            btnTestEmail.textContent = originalText;
            btnTestEmail.disabled = false;
        });
    }

    // --- Automation Execution ---
    async function startAutomation(platform) {
        const isHeadless = document.getElementById(`${platform}-headless`).checked;
        const btn = document.getElementById(`btn-start-${platform}`);
        
        try {
            const res = await fetch(`/api/start/${platform}?headless=${isHeadless}`, {
                method: 'POST'
            });
            const data = await res.json();
            
            if (res.ok) {
                console.log(data.message);
                window.limitAlertShown = false; // Reset alert flag on new run
                startStatusPolling(); // Ensure polling is active
            } else {
                alert(data.error || "Failed to start automation");
            }
        } catch (e) {
            console.error(e);
            alert("Error starting automation");
        }
    }

    document.getElementById('btn-start-linkedin').addEventListener('click', () => startAutomation('linkedin'));
    document.getElementById('btn-start-naukri').addEventListener('click', () => startAutomation('naukri'));


    // --- Status Polling ---
    function startStatusPolling() {
        if (pollInterval) clearInterval(pollInterval);
        pollStatus(); // Poll immediately
        pollInterval = setInterval(pollStatus, 2000);
    }

    function stopStatusPolling() {
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
    }

    async function pollStatus() {
        if (!currentPlatform) return;
        try {
            const res = await fetch(`/api/status/${currentPlatform}`);
            if (res.ok) {
                const data = await res.json();
                updateConsole(data);
            }
        } catch (e) {
            // Silently ignore network errors during polling
        }
    }

    function updateConsole(data) {
        const dot = document.getElementById('status-dot');
        const text = document.getElementById('status-text');
        const consoleOut = document.getElementById('console-output');
        const limitAlert = document.getElementById('limit-alert');
        const limitPlatformName = document.getElementById('limit-platform-name');

        if (data.running) {
            dot.classList.add('running');
            text.textContent = `Running ${currentPlatform.toUpperCase()}`;
            wasRunning = true;
        } else {
            dot.classList.remove('running');
            text.textContent = 'Idle';
            if (wasRunning) {
                wasRunning = false;
                // Just stopped running (either automation or manual login), check login status
                checkLoginStatus(currentPlatform);
            }
        }

        if (data.latest_logs && data.latest_logs.length > 0) {
            consoleOut.innerHTML = data.latest_logs
                .map(line => `<div class="log-line">${escapeHTML(line)}</div>`)
                .join('');
            consoleOut.scrollTop = consoleOut.scrollHeight;
        }

        if (data.limit_reached) {
            if (!window.limitAlertShown) {
                window.limitAlertShown = true;
            }
            limitPlatformName.textContent = currentPlatform;
            limitAlert.style.display = 'flex';
            
            // Move the alert just below the panel header of the active platform
            const activePanel = document.getElementById(`${currentPlatform}-panel`);
            if (activePanel) {
                const configCard = activePanel.querySelector('.config-card');
                if (configCard && limitAlert.parentElement !== activePanel) {
                    activePanel.insertBefore(limitAlert, configCard);
                }
            }
        } else {
            window.limitAlertShown = false;
            limitAlert.style.display = 'none';
        }
    }

    function escapeHTML(str) {
        return str.replace(/[&<>'"]/g, 
            tag => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                "'": '&#39;',
                '"': '&quot;'
            }[tag] || tag)
        );
    }

    // --- Reports (Tabular) ---
    let currentReportPlatform = 'linkedin';
    const reportTabs = document.querySelectorAll('.report-tab-btn');
    const reportsTableBody = document.getElementById('reports-table-body');
    const selectAllCheckbox = document.getElementById('select-all-reports');
    const btnDeleteReports = document.getElementById('btn-delete-reports');
    const btnRefreshReports = document.getElementById('btn-refresh-reports');
    
    reportTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            reportTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentReportPlatform = tab.getAttribute('data-platform');
            loadReports();
        });
    });

    async function loadReports() {
        if (!reportsTableBody) return;
        reportsTableBody.innerHTML = '<tr><td colspan="8" style="text-align:center;">Loading runs...</td></tr>';
        selectAllCheckbox.checked = false;
        updateDeleteButtonState();
        
        try {
            const res = await fetch(`/api/runs/${currentReportPlatform}`);
            if (res.ok) {
                const data = await res.json();
                if (data.runs.length === 0) {
                    reportsTableBody.innerHTML = '<tr><td colspan="8" style="text-align:center;">No automation runs found.</td></tr>';
                } else {
                    reportsTableBody.innerHTML = data.runs.map(run => {
                        const date = new Date(run.timestamp).toLocaleString();
                        const pdfLink = run.pdf_path ? `<a href="/api/reports/${run.pdf_path.split(/[\\/]/).pop()}" target="_blank" style="color:var(--accent-primary);">View PDF</a>` : 'N/A';
                        const emailStatus = run.email_status || 'N/A';
                        const emailColor = emailStatus === 'Sent' ? 'var(--success)' : (emailStatus === 'Failed' ? 'var(--danger)' : 'var(--text-secondary)');
                        return `
                            <tr>
                                <td><input type="checkbox" class="report-row-checkbox" data-id="${run.id}"></td>
                                <td>#${run.id}</td>
                                <td>${date}</td>
                                <td>${run.status}</td>
                                <td style="text-align: center;">${run.success_count}</td>
                                <td style="text-align: center;">${run.ignore_count}</td>
                                <td style="text-align: center;">${run.failed_count}</td>
                                <td>${pdfLink}</td>
                                <td style="color: ${emailColor};">${emailStatus}</td>
                            </tr>
                        `;
                    }).join('');
                    
                    // Attach listeners for checkboxes
                    document.querySelectorAll('.report-row-checkbox').forEach(cb => {
                        cb.addEventListener('change', updateDeleteButtonState);
                    });
                }
            }
        } catch (e) {
            reportsTableBody.innerHTML = '<tr><td colspan="8" style="text-align:center;">Error loading runs.</td></tr>';
        }
    }

    function updateDeleteButtonState() {
        const checkboxes = document.querySelectorAll('.report-row-checkbox');
        const anyChecked = Array.from(checkboxes).some(cb => cb.checked);
        btnDeleteReports.disabled = !anyChecked;
        
        const allChecked = checkboxes.length > 0 && Array.from(checkboxes).every(cb => cb.checked);
        selectAllCheckbox.checked = allChecked;
    }

    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', (e) => {
            const checkboxes = document.querySelectorAll('.report-row-checkbox');
            checkboxes.forEach(cb => cb.checked = e.target.checked);
            updateDeleteButtonState();
        });
    }

    if (btnDeleteReports) {
        btnDeleteReports.addEventListener('click', async () => {
            const checkboxes = document.querySelectorAll('.report-row-checkbox:checked');
            const ids = Array.from(checkboxes).map(cb => parseInt(cb.getAttribute('data-id')));
            if (ids.length === 0) return;
            
            if (confirm(`Are you sure you want to delete ${ids.length} selected run(s)? This will also delete any associated PDF reports.`)) {
                try {
                    const res = await fetch('/api/runs', {
                        method: 'DELETE',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ run_ids: ids })
                    });
                    if (res.ok) {
                        loadReports();
                    } else {
                        alert('Failed to delete runs.');
                    }
                } catch (e) {
                    alert('Error deleting runs.');
                }
            }
        });
    }

    if (btnRefreshReports) {
        btnRefreshReports.addEventListener('click', loadReports);
    }

    // --- Schedules Logic ---
    const scheduleForm = document.getElementById('create-schedule-form');
    const schedulesTableBody = document.querySelector('#schedules-table tbody');

    async function loadSchedules() {
        if (!schedulesTableBody) return;
        try {
            const response = await fetch('/api/schedules');
            const data = await response.json();
            schedulesTableBody.innerHTML = '';
            data.forEach(sch => {
                const tr = document.createElement('tr');
                const headlessText = sch.headless ? 'Headless' : 'Visible';
                tr.innerHTML = `
                    <td style="text-transform: capitalize;">${sch.platform} <span style="font-size: 0.8em; color: var(--text-secondary); margin-left: 4px;">(${headlessText})</span></td>
                    <td>${sch.cron_time}</td>
                    <td>
                        <label class="toggle-switch">
                            <input type="checkbox" ${sch.is_active ? 'checked' : ''} onchange="window.toggleSchedule(${sch.id}, this.checked)">
                            <span class="slider"></span>
                        </label>
                    </td>
                    <td>
                        <button class="btn btn-secondary" onclick="window.deleteSchedule(${sch.id})" style="padding: 4px 8px; color: var(--danger); border-color: var(--danger);">Delete</button>
                    </td>
                `;
                schedulesTableBody.appendChild(tr);
            });
        } catch (error) {
            console.error('Error loading schedules:', error);
        }
    }

    if (scheduleForm) {
        scheduleForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const platform = document.getElementById('schedule-platform').value;
            const time = document.getElementById('schedule-time').value;
            const headless = document.getElementById('schedule-headless').checked;
            try {
                await fetch('/api/schedules', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({platform, cron_time: time, headless})
                });
                loadSchedules();
            } catch (error) {
                console.error('Error creating schedule:', error);
            }
        });
    }

    window.toggleSchedule = async (id, isActive) => {
        try {
            await fetch(`/api/schedules/${id}/toggle`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({is_active: isActive ? 1 : 0})
            });
        } catch (error) {
            console.error('Error toggling schedule:', error);
        }
    };

    window.deleteSchedule = async (id) => {
        if (!confirm('Delete this schedule?')) return;
        try {
            await fetch(`/api/schedules/${id}`, { method: 'DELETE' });
            loadSchedules();
        } catch (error) {
            console.error('Error deleting schedule:', error);
        }
    };

    // Initial load
    loadConfig('linkedin');
    checkLoginStatus('linkedin');
    startStatusPolling();
    loadSchedules();
});
