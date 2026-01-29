/**
 * YouTube/Playlist to MP3 Converter
 * Frontend JavaScript
 */

// State
let videos = [];
let duplicateIndices = new Set();
let duplicateGroups = [];

// DOM Elements
const urlInput = document.getElementById('url-input');
const analyzeBtn = document.getElementById('analyze-btn');
const videoListSection = document.getElementById('video-list-section');
const videoList = document.getElementById('video-list');
const videoCount = document.getElementById('video-count');
const downloadBtn = document.getElementById('download-btn');
const selectAllBtn = document.getElementById('select-all-btn');
const deselectAllBtn = document.getElementById('deselect-all-btn');
const invertBtn = document.getElementById('invert-btn');
const deselectDuplicatesBtn = document.getElementById('deselect-duplicates-btn');
const progressSection = document.getElementById('progress-section');
const progressBar = document.getElementById('progress-bar');
const progressText = document.getElementById('progress-text');
const resultsSection = document.getElementById('results-section');
const resultsList = document.getElementById('results-list');
const downloadZipBtn = document.getElementById('download-zip-btn');
const downloadPathInput = document.getElementById('download-path');
const browseBtn = document.getElementById('browse-btn');
const searchInput = document.getElementById('search-input');
const selectionStats = document.getElementById('selection-stats');
const clearSuccessBtn = document.getElementById('clear-success-btn');
const clearAllBtn = document.getElementById('clear-all-btn');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    analyzeBtn.addEventListener('click', handleAnalyze);
    downloadBtn.addEventListener('click', handleDownload);
    selectAllBtn.addEventListener('click', () => setAllCheckboxes(true));
    deselectAllBtn.addEventListener('click', () => setAllCheckboxes(false));
    invertBtn.addEventListener('click', handleInvertSelection);
    deselectDuplicatesBtn.addEventListener('click', handleDeselectDuplicates);
    downloadZipBtn.addEventListener('click', handleDownloadZip);
    browseBtn.addEventListener('click', handleBrowseFolder);
    searchInput.addEventListener('input', handleSearch);
    clearSuccessBtn.addEventListener('click', handleClearSuccess);
    clearAllBtn.addEventListener('click', handleClearAll);
});

/**
 * Handle browse folder button click
 * Calls backend API to open native folder picker dialog
 */
async function handleBrowseFolder() {
    browseBtn.disabled = true;
    browseBtn.textContent = '選擇中...';

    try {
        const response = await fetch('/api/browse-folder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.path) {
            downloadPathInput.value = data.path;
        }
    } catch (error) {
        console.error('Folder selection error:', error);
        alert('無法開啟資料夾選擇器');
    } finally {
        browseBtn.disabled = false;
        browseBtn.textContent = '📂 瀏覽';
    }
}

/**
 * Parse URLs from input
 */
function parseUrls(text) {
    return text.split('\n')
        .map(line => line.trim())
        .filter(line => line && (line.includes('youtube.com') || line.includes('youtu.be')));
}

/**
 * Handle analyze button click
 */
async function handleAnalyze() {
    // Parse URLs (simple split by newline)
    const urls = urlInput.value.split('\n').filter(u => u.trim());

    if (urls.length === 0) {
        alert('請輸入至少一個 YouTube URL');
        return;
    }

    // Detect Mix playlist (RD... in list parameter)
    const isMix = urls.some(u => u.includes('list=RD'));
    let limit = null;

    if (isMix) {
        const input = prompt("偵測到 Mix (合集/電台)，可能包含數千首歌曲。\n請輸入要載入的歌曲數量 (建議 50-100):", "50");
        if (input === null) return; // User cancelled
        limit = parseInt(input) || 50;
    }

    // UI updates
    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = '⏳ 分析中...';
    resultsSection.classList.remove('visible');
    progressSection.classList.remove('visible');

    try {
        // Fetch video info
        const response = await fetch('/api/fetch-info', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ urls, limit })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to fetch video info');
        }

        videos = data.videos;

        // Check for duplicates
        const dupResponse = await fetch('/api/check-duplicates', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ videos, threshold: 80 })
        });

        const dupData = await dupResponse.json();
        duplicateIndices = new Set(dupData.duplicate_indices);
        duplicateGroups = dupData.duplicate_groups;

        // Render video list
        renderVideoList();

        // Show warnings if any
        if (data.errors && data.errors.length > 0) {
            console.warn('Some URLs had errors:', data.errors);
        }

    } catch (error) {
        alert('錯誤: ' + error.message);
        console.error(error);
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = '🔍 分析 URL';
    }
}

/**
 * Render the video list
 */
function renderVideoList() {
    videoList.innerHTML = '';
    videoCount.textContent = videos.length;

    videos.forEach((video, index) => {
        const isDuplicate = duplicateIndices.has(index);
        const groupIndex = findDuplicateGroup(index);

        // Check if video is unavailable/private
        const title = video.title || '';
        const isUnavailable = title.includes('[Private video]') ||
            title.includes('[Deleted video]') ||
            title.includes('[Unavailable]') ||
            title === 'Private video' ||
            title === 'Deleted video';

        const item = document.createElement('div');
        let itemClass = 'video-item';
        if (isDuplicate) itemClass += ' duplicate';
        if (isUnavailable) itemClass += ' unavailable';
        item.className = itemClass;

        // Unavailable videos are unchecked by default
        const isChecked = !isUnavailable;

        item.innerHTML = `
            <input type="checkbox" class="video-checkbox" data-index="${index}" ${isChecked ? 'checked' : ''}>
            <div class="video-info">
                <div class="video-title">${escapeHtml(video.title)}</div>
                <div class="video-meta">${video.duration_formatted || 'Unknown duration'}</div>
            </div>
            ${isDuplicate ? `<span class="duplicate-badge">可能重複 (群組 ${groupIndex + 1})</span>` : ''}
            ${isUnavailable ? `<span class="duplicate-badge" style="background: rgba(100,100,100,0.3); color: var(--text-muted);">不可用</span>` : ''}
        `;

        videoList.appendChild(item);
    });

    videoListSection.classList.add('visible');
    updateDownloadButton();

    // Add checkbox listeners
    document.querySelectorAll('.video-checkbox').forEach(cb => {
        cb.addEventListener('change', updateDownloadButton);
    });

    // Clear search input
    searchInput.value = '';
}

/**
 * Find which duplicate group a video belongs to
 */
function findDuplicateGroup(index) {
    for (let i = 0; i < duplicateGroups.length; i++) {
        if (duplicateGroups[i].includes(index)) {
            return i;
        }
    }
    return -1;
}

/**
 * Update download button state and selection stats
 */
function updateDownloadButton() {
    const total = document.querySelectorAll('.video-checkbox').length;
    const checked = document.querySelectorAll('.video-checkbox:checked').length;
    downloadBtn.textContent = `⬇️ 下載選取的歌曲 (${checked})`;
    downloadBtn.disabled = checked === 0;

    // Update selection stats
    if (selectionStats) {
        const dupCount = duplicateIndices.size;
        selectionStats.textContent = `已選 ${checked} / ${total} 首${dupCount > 0 ? ` (${dupCount} 首重複)` : ''}`;
    }
}

/**
 * Set all checkboxes
 */
function setAllCheckboxes(checked) {
    document.querySelectorAll('.video-checkbox').forEach(cb => {
        cb.checked = checked;
    });
    updateDownloadButton();
}

/**
 * Handle search input - filter videos by title
 */
function handleSearch() {
    const query = searchInput.value.toLowerCase().trim();
    document.querySelectorAll('.video-item').forEach((item, index) => {
        const title = videos[index]?.title?.toLowerCase() || '';
        if (query === '' || title.includes(query)) {
            item.classList.remove('hidden');
        } else {
            item.classList.add('hidden');
        }
    });
}

/**
 * Handle invert selection
 */
function handleInvertSelection() {
    document.querySelectorAll('.video-checkbox').forEach(cb => {
        cb.checked = !cb.checked;
    });
    updateDownloadButton();
}

/**
 * Handle deselect duplicates - uncheck all duplicate items except first in each group
 */
function handleDeselectDuplicates() {
    // Uncheck all items that are marked as duplicates
    duplicateIndices.forEach(index => {
        const cb = document.querySelector(`.video-checkbox[data-index="${index}"]`);
        if (cb) cb.checked = false;
    });
    updateDownloadButton();
}

/**
 * Handle clear success - keep only failed items, clear successful ones
 */
function handleClearSuccess() {
    if (!window.downloadResults) return;

    // Filter to keep only failed results
    const failedResults = window.downloadResults.filter(r => !r.success);

    if (failedResults.length === 0) {
        // If no failed items, hide results section
        resultsSection.classList.remove('visible');
        progressSection.classList.remove('visible');
    } else {
        // Re-render with only failed items
        window.downloadResults = failedResults;
        renderResults(failedResults, null);
    }
}

/**
 * Handle clear all - reset everything except download path
 */
function handleClearAll() {
    // Reset state
    videos = [];
    duplicateIndices = new Set();
    duplicateGroups = [];
    window.downloadResults = null;

    // Clear UI
    videoList.innerHTML = '';
    resultsList.innerHTML = '';
    urlInput.value = '';
    searchInput.value = '';
    videoCount.textContent = '0';
    selectionStats.textContent = '已選 0 首';
    progressBar.style.width = '0%';
    progressText.textContent = '準備中...';

    // Hide sections
    videoListSection.classList.remove('visible');
    resultsSection.classList.remove('visible');
    progressSection.classList.remove('visible');

    // Note: Download path is preserved
}

/**
 * Handle download button click
 */
async function handleDownload() {
    const selectedIndices = [];
    document.querySelectorAll('.video-checkbox:checked').forEach(cb => {
        selectedIndices.push(parseInt(cb.dataset.index));
    });

    if (selectedIndices.length === 0) {
        alert('請至少選擇一首歌曲');
        return;
    }

    const selectedVideos = selectedIndices.map(i => videos[i]);

    // Show progress
    downloadBtn.disabled = true;
    progressSection.classList.add('visible');
    resultsSection.classList.remove('visible');
    progressBar.style.width = '0%';
    progressText.textContent = `準備下載 ${selectedVideos.length} 首歌曲...`;

    try {
        // Start download
        const downloadPath = downloadPathInput.value.trim();
        const selectedFormat = document.querySelector('input[name="format"]:checked').value;
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                videos: selectedVideos,
                download_path: downloadPath,
                format: selectedFormat
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Download failed');
        }

        // Update progress to 100%
        progressBar.style.width = '100%';
        const pathInfo = data.download_path ? ` → ${data.download_path}` : '';
        progressText.textContent = `完成! ${data.successful_count}/${data.total_count} 首歌曲下載成功${pathInfo}`;

        // Show results
        renderResults(data.results, data.download_path);

    } catch (error) {
        alert('下載錯誤: ' + error.message);
        console.error(error);
        progressSection.classList.remove('visible');
    } finally {
        downloadBtn.disabled = false;
    }
}

/**
 * Render download results
 */
function renderResults(results, downloadPath) {
    resultsList.innerHTML = '';

    results.forEach((result, index) => {
        const item = document.createElement('div');
        item.className = `result-item ${result.success ? 'success' : 'error'}`;

        let actions = '';
        if (!result.success && result.video) {
            // Add retry button for failed downloads
            actions = `
                <button class="btn-retry" data-index="${index}" onclick="retryDownload(${index})">
                    🔄 重試
                </button>
            `;
        }

        item.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px; flex: 1;">
                <span class="result-icon">${result.success ? '✅' : '❌'}</span>
                <span class="result-title">${escapeHtml(result.title)}</span>
            </div>
            ${actions}
            ${result.error ? `<div style="width: 100%; color: var(--error); font-size: 0.85rem; margin-top: 5px;">${escapeHtml(result.error)}</div>` : ''}
        `;
        resultsList.appendChild(item);
    });

    // Store results for retry functionality
    window.downloadResults = results;

    resultsSection.classList.add('visible');

    // Enable zip download if there are successful downloads
    const hasSuccessful = results.some(r => r.success);
    downloadZipBtn.disabled = !hasSuccessful;
}

/**
 * Retry a failed download
 */
async function retryDownload(index) {
    const result = window.downloadResults[index];
    if (!result || !result.video) return;

    const btn = document.querySelector(`button[data-index="${index}"]`);
    if (btn) {
        btn.disabled = true;
        btn.textContent = '⏳ 下載中...';
    }

    try {
        const downloadPath = downloadPathInput.value.trim();
        const selectedFormat = document.querySelector('input[name="format"]:checked').value;

        const response = await fetch('/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                videos: [result.video],
                download_path: downloadPath,
                format: selectedFormat
            })
        });

        const data = await response.json();

        if (data.results && data.results[0]) {
            // Update the result
            window.downloadResults[index] = data.results[0];
            // Re-render results
            renderResults(window.downloadResults, downloadPath);
        }
    } catch (error) {
        console.error('Retry failed:', error);
        if (btn) {
            btn.disabled = false;
            btn.textContent = '🔄 重試';
        }
    }
}


/**
 * Handle ZIP download
 */
function handleDownloadZip() {
    window.location.href = '/api/download-zip';
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
