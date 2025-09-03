// DOM elementləri
const urlInput = document.getElementById('urlInput');
const getInfoBtn = document.getElementById('getInfoBtn');
const loadingSection = document.getElementById('loadingSection');
const videoInfo = document.getElementById('videoInfo');
const errorMessage = document.getElementById('errorMessage');
const errorText = document.getElementById('errorText');
const downloadBtn = document.getElementById('downloadBtn');
const thumbnail = document.getElementById('thumbnail');
const videoTitle = document.getElementById('videoTitle');
const videoDuration = document.getElementById('videoDuration');
const qualityOptions = document.getElementById('qualityOptions');
const qualitySelect = document.getElementById('qualitySelect');

// Format düymələri
const formatButtons = document.querySelectorAll('.format-btn');
let selectedFormat = 'video';
let currentVideoUrl = '';

// Format seçimi
formatButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        formatButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        selectedFormat = btn.dataset.format;
        
        // Audio seçildikdə keyfiyyət seçimini gizlə
        if (selectedFormat === 'audio') {
            qualityOptions.style.display = 'none';
        } else {
            qualityOptions.style.display = 'block';
        }
    });
});

// URL doğrulama
function isValidUrl(url) {
    const platforms = [
        'youtube.com',
        'youtu.be',
        'tiktok.com',
        'twitter.com',
        'x.com',
        'instagram.com',
        'facebook.com',
        'vimeo.com'
    ];
    
    try {
        const urlObj = new URL(url);
        return platforms.some(platform => urlObj.hostname.includes(platform));
    } catch {
        return false;
    }
}

// Müddəti formatla
function formatDuration(seconds) {
    if (!seconds) return 'Naməlum';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    } else {
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }
}

// Xəta göstər
function showError(message) {
    errorText.textContent = message;
    errorMessage.style.display = 'block';
    loadingSection.style.display = 'none';
    videoInfo.style.display = 'none';
    
    setTimeout(() => {
        errorMessage.style.display = 'none';
    }, 5000);
}

// Video məlumatlarını al
async function getVideoInfo() {
    const url = urlInput.value.trim();
    
    if (!url) {
        showError('Zəhmət olmasa bir link daxil edin');
        return;
    }
    
    if (!isValidUrl(url)) {
        showError('Zəhmət olmasa düzgün bir sosial media linki daxil edin');
        return;
    }
    
    // Loading göstər
    loadingSection.style.display = 'block';
    videoInfo.style.display = 'none';
    errorMessage.style.display = 'none';
    currentVideoUrl = url;
    
    try {
        const response = await fetch('/api/info', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: url })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Video məlumatlarını göstər
            displayVideoInfo(data.info);
        } else {
            showError(data.error || 'Video məlumatları alına bilmədi');
        }
    } catch (error) {
        showError('Xəta baş verdi. Zəhmət olmasa yenidən cəhd edin.');
        console.error('Error:', error);
    } finally {
        loadingSection.style.display = 'none';
    }
}

// Video məlumatlarını göstər
function displayVideoInfo(info) {
    videoTitle.textContent = info.title || 'Video';
    videoDuration.textContent = `Müddət: ${formatDuration(info.duration)}`;
    
    if (info.thumbnail) {
        thumbnail.src = info.thumbnail;
        thumbnail.style.display = 'block';
    } else {
        thumbnail.style.display = 'none';
    }
    
    videoInfo.style.display = 'block';
}

// Video/Audio endir
async function downloadMedia() {
    if (!currentVideoUrl) {
        showError('Zəhmət olmasa əvvəlcə video linki daxil edin');
        return;
    }
    
    // Download düyməsini deaktiv et
    downloadBtn.disabled = true;
    downloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Yüklənir...';
    
    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: currentVideoUrl,
                format: selectedFormat,
                quality: qualitySelect.value
            })
        });
        
        if (response.ok) {
            // Faylı endir
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            
            // Fayl adını müəyyən et
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'download';
            if (contentDisposition) {
                const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (match && match[1]) {
                    filename = match[1].replace(/['"]/g, '');
                }
            }
            
            // Fayl uzantısını əlavə et
            if (!filename.includes('.')) {
                filename += selectedFormat === 'audio' ? '.mp3' : '.mp4';
            }
            
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            // Uğur mesajı
            showSuccess('Yükləmə tamamlandı!');
        } else {
            const data = await response.json();
            showError(data.error || 'Yükləmə zamanı xəta baş verdi');
        }
    } catch (error) {
        showError('Yükləmə zamanı xəta baş verdi. Zəhmət olmasa yenidən cəhd edin.');
        console.error('Error:', error);
    } finally {
        // Download düyməsini aktivləşdir
        downloadBtn.disabled = false;
        downloadBtn.innerHTML = '<i class="fas fa-download"></i> Yüklə';
    }
}

// Uğur mesajı göstər
function showSuccess(message) {
    const successDiv = document.createElement('div');
    successDiv.className = 'success-message';
    successDiv.innerHTML = `
        <i class="fas fa-check-circle"></i>
        <p>${message}</p>
    `;
    document.body.appendChild(successDiv);
    
    setTimeout(() => {
        successDiv.remove();
    }, 3000);
}

// Event listeners
getInfoBtn.addEventListener('click', getVideoInfo);
downloadBtn.addEventListener('click', downloadMedia);

// Enter düyməsi ilə axtarış
urlInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        getVideoInfo();
    }
});

// URL yapışdırıldıqda avtomatik analiz
urlInput.addEventListener('paste', (e) => {
    setTimeout(() => {
        if (isValidUrl(urlInput.value)) {
            getVideoInfo();
        }
    }, 100);
});

// Səhifə yüklənəndə
document.addEventListener('DOMContentLoaded', () => {
    // Input-a fokus et
    urlInput.focus();
    
    // Köhnə faylları təmizlə (backend-də)
    fetch('/api/clean', {
        method: 'POST'
    }).catch(console.error);
});

// Clipboard API dəstəyi
if (navigator.clipboard) {
    // Yapışdır düyməsi əlavə et
    const pasteBtn = document.createElement('button');
    pasteBtn.className = 'paste-btn';
    pasteBtn.innerHTML = '<i class="fas fa-paste"></i>';
    pasteBtn.title = 'Linkı yapışdır';
    
    urlInput.parentElement.style.position = 'relative';
    urlInput.parentElement.appendChild(pasteBtn);
    
    pasteBtn.addEventListener('click', async () => {
        try {
            const text = await navigator.clipboard.readText();
            urlInput.value = text;
            if (isValidUrl(text)) {
                getVideoInfo();
            }
        } catch (err) {
            console.error('Clipboard oxunma xətası:', err);
        }
    });
}

// Progress bar əlavə et
function createProgressBar() {
    const progressBar = document.createElement('div');
    progressBar.className = 'progress-bar';
    progressBar.innerHTML = `
        <div class="progress-bar-fill"></div>
        <span class="progress-text">0%</span>
    `;
    return progressBar;
}

// Faylın ölçüsünü formatla
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Video keyfiyyətini avtomatik seç
function autoSelectQuality(formats) {
    if (!formats || formats.length === 0) return;
    
    // Mövcud keyfiyyətləri tap
    const availableQualities = [];
    formats.forEach(format => {
        if (format.height) {
            availableQualities.push(format.height);
        }
    });
    
    // Quality select-i yenilə
    qualitySelect.innerHTML = '<option value="best">Ən Yaxşı</option>';
    
    const standardQualities = [1080, 720, 480, 360];
    standardQualities.forEach(quality => {
        if (availableQualities.some(q => q >= quality)) {
            const option = document.createElement('option');
            option.value = quality;
            option.textContent = `${quality}p`;
            qualitySelect.appendChild(option);
        }
    });
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + V - Yapışdır və analiz et
    if ((e.ctrlKey || e.metaKey) && e.key === 'v') {
        setTimeout(() => {
            if (document.activeElement === urlInput && isValidUrl(urlInput.value)) {
                getVideoInfo();
            }
        }, 100);
    }
    
    // Ctrl/Cmd + Enter - Yüklə
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        if (videoInfo.style.display === 'block') {
            downloadMedia();
        }
    }
    
    // Escape - Təmizlə
    if (e.key === 'Escape') {
        urlInput.value = '';
        videoInfo.style.display = 'none';
        errorMessage.style.display = 'none';
        urlInput.focus();
    }
});

// Mobil cihazlar üçün optimizasiya
if ('ontouchstart' in window) {
    document.body.classList.add('touch-device');
}

// Service Worker qeydiyyatı (offline dəstəyi üçün)
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(console.error);
}

// Analytics (istəyə bağlı)
function trackEvent(category, action, label) {
    // Google Analytics və ya digər analytics xidməti
    console.log('Track Event:', { category, action, label });
}

// Dil dəstəyi
const translations = {
    az: {
        'loading': 'Yüklənir...',
        'error': 'Xəta',
        'success': 'Uğurlu',
        'download': 'Yüklə',
        'analyze': 'Analiz Et'
    },
    en: {
        'loading': 'Loading...',
        'error': 'Error',
        'success': 'Success',
        'download': 'Download',
        'analyze': 'Analyze'
    }
};

let currentLang = 'az';

function translate(key) {
    return translations[currentLang][key] || key;
}
