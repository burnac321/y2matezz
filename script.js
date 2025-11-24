class Y2MateZZDownloader {
    constructor() {
        this.backendUrl = 'y2matezz-production.up.railway.app'; // Replace with your Railway URL
        this.currentVideoData = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.checkBackendHealth();
    }

    bindEvents() {
        const urlInput = document.getElementById('videoUrl');
        const fetchBtn = document.getElementById('fetchBtn');

        // Enter key support
        urlInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.getFormats();
            }
        });

        // Paste event with validation
        urlInput.addEventListener('paste', (e) => {
            setTimeout(() => {
                this.validateUrl(urlInput.value);
            }, 100);
        });

        // Input validation
        urlInput.addEventListener('input', () => {
            this.validateUrl(urlInput.value);
        });
    }

    validateUrl(url) {
        const fetchBtn = document.getElementById('fetchBtn');
        const isValid = url.length > 10 && url.includes('://');
        
        fetchBtn.disabled = !isValid;
        return isValid;
    }

    async checkBackendHealth() {
        try {
            const response = await fetch(`${this.backendUrl}/health`);
            if (!response.ok) {
                console.warn('Backend might be unavailable');
            }
        } catch (error) {
            console.warn('Cannot reach backend server');
        }
    }

    async getFormats() {
        const url = document.getElementById('videoUrl').value.trim();
        
        if (!this.validateUrl(url)) {
            this.showError('Please enter a valid video URL');
            return;
        }

        this.showLoading();
        this.hideError();
        this.hideResults();

        try {
            const data = await this.makeRequest('/get_formats', { url });
            
            if (data.error) {
                this.showError(data.error);
                return;
            }

            this.currentVideoData = data;
            this.displayResults(data);
            
        } catch (error) {
            this.showError('Network error. Please check your connection and try again.');
        }
    }

    async getDirectUrl(formatId) {
        if (!this.currentVideoData) return;

        const url = document.getElementById('videoUrl').value.trim();
        const downloadBtn = event.target;
        const originalText = downloadBtn.innerHTML;

        // Show loading state on button
        downloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Preparing...';
        downloadBtn.disabled = true;

        try {
            const data = await this.makeRequest('/get_direct_url', {
                url: url,
                format_id: formatId
            });

            if (data.error) {
                this.showError(data.error);
                return;
            }

            // Create and trigger download
            this.triggerDownload(data.video_url, data.filename);

        } catch (error) {
            this.showError('Failed to prepare download. Please try again.');
        } finally {
            // Restore button state
            downloadBtn.innerHTML = originalText;
            downloadBtn.disabled = false;
        }
    }

    triggerDownload(downloadUrl, filename) {
        // Open in new tab for direct download
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.target = '_blank';
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        // Show success message
        this.showTempMessage('Download started! Check your browser downloads.', 'success');
    }

    async makeRequest(endpoint, data) {
        const response = await fetch(`${this.backendUrl}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    displayResults(data) {
        const resultsSection = document.getElementById('results');
        const formatsGrid = this.createFormatsGrid(data);
        
        resultsSection.innerHTML = `
            <div class="video-info">
                <h3>${this.escapeHtml(data.title)}</h3>
                ${data.thumbnail ? `<img src="${data.thumbnail}" alt="Thumbnail" style="max-width: 200px; border-radius: 8px; margin-top: 15px;">` : ''}
                <div class="video-meta">
                    ${data.uploader ? `<div class="meta-item"><i class="fas fa-user"></i> ${this.escapeHtml(data.uploader)}</div>` : ''}
                    ${data.duration ? `<div class="meta-item"><i class="fas fa-clock"></i> ${data.duration}</div>` : ''}
                    ${data.view_count ? `<div class="meta-item"><i class="fas fa-eye"></i> ${this.formatNumber(data.view_count)} views</div>` : ''}
                </div>
            </div>
            <div class="formats-grid">
                <h3 style="margin-bottom: 20px; color: #333;">Available Formats:</h3>
                ${formatsGrid}
            </div>
        `;
        
        this.hideLoading();
        resultsSection.classList.remove('hidden');
        
        // Add click listeners to download buttons
        resultsSection.querySelectorAll('.download-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const formatId = btn.dataset.formatId;
                this.getDirectUrl(formatId);
            });
        });
    }

    createFormatsGrid(data) {
        if (!data.formats || data.formats.length === 0) {
            return '<p>No formats available for this video.</p>';
        }

        return data.formats.map(format => `
            <div class="format-item">
                <div class="format-info">
                    <div class="format-quality">${format.quality || `${format.resolution} (${format.ext.toUpperCase()})`}</div>
                    <div class="format-details">
                        ${format.format_note ? `${format.format_note} • ` : ''}
                        ${format.ext.toUpperCase()}
                        ${format.filesize ? ` • ${this.formatFileSize(format.filesize)}` : ''}
                    </div>
                </div>
                <button class="download-btn" data-format-id="${format.format_id}">
                    <i class="fas fa-download"></i>
                    Download
                </button>
            </div>
        `).join('');
    }

    showLoading() {
        document.getElementById('loading').classList.remove('hidden');
    }

    hideLoading() {
        document.getElementById('loading').classList.add('hidden');
    }

    showError(message) {
        this.hideLoading();
        const errorSection = document.getElementById('error');
        errorSection.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i>
            <h3>Oops! Something went wrong</h3>
            <p>${this.escapeHtml(message)}</p>
            <button onclick="location.reload()" style="margin-top: 15px; padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer;">
                Try Again
            </button>
        `;
        errorSection.classList.remove('hidden');
    }

    hideError() {
        document.getElementById('error').classList.add('hidden');
    }

    hideResults() {
        document.getElementById('results').classList.add('hidden');
    }

    showTempMessage(message, type = 'info') {
        const tempMsg = document.createElement('div');
        tempMsg.className = `temp-message ${type}`;
        tempMsg.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check' : 'info'}"></i>
            ${message}
        `;
        
        tempMsg.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#d4edda' : '#d1ecf1'};
            color: ${type === 'success' ? '#155724' : '#0c5460'};
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1000;
            border-left: 4px solid ${type === 'success' ? '#28a745' : '#17a2b8'};
        `;
        
        document.body.appendChild(tempMsg);
        
        setTimeout(() => {
            tempMsg.remove();
        }, 4000);
    }

    formatFileSize(bytes) {
        if (!bytes) return 'Unknown size';
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    }

    formatNumber(num) {
        return new Intl.NumberFormat().format(num);
    }

    escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
}

// Initialize the application
const downloader = new Y2MateZZDownloader();

// Global functions for HTML onclick handlers
function getFormats() {
    downloader.getFormats();
}

function downloadFormat(formatId) {
    downloader.getDirectUrl(formatId);
}

// Service Worker registration for PWA capabilities (optional)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/sw.js').then(function(registration) {
            console.log('SW registered: ', registration);
        }).catch(function(registrationError) {
            console.log('SW registration failed: ', registrationError);
        });
    });
}
