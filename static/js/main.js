// Additional JavaScript functionality

// Auto-hide alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(alert => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
});

// File preview for images
function showFilePreview(fileId, fileType) {
    if (fileType.match(/^image\//)) {
        // Implement image preview modal
        console.log('Show image preview for:', fileId);
    }
}

// Storage usage update
function updateStorageUsage() {
    fetch('/api/storage')
        .then(response => response.json())
        .then(data => {
            const progressBar = document.querySelector('.progress-bar');
            const storageText = document.querySelector('.storage-text');
            
            if (progressBar) {
                progressBar.style.width = `${data.percentage}%`;
                progressBar.textContent = `${data.percentage.toFixed(1)}%`;
                
                if (data.percentage > 90) {
                    progressBar.classList.add('bg-danger');
                }
            }
            
            if (storageText) {
                storageText.textContent = `${data.used_formatted} / ${data.total_formatted}`;
            }
        });
}

// Update storage every minute
setInterval(updateStorageUsage, 60000);
