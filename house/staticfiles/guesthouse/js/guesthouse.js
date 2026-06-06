// Guest House Module - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Sidebar toggle
    const toggleBtn = document.getElementById('ghToggleSidebar');
    const sidebar = document.getElementById('ghSidebar');
    
    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
        });
    }

    // Auto-close alerts after 5 seconds
    document.querySelectorAll('.gh-alert').forEach(function(alert) {
        setTimeout(function() {
            if (alert.parentElement) alert.remove();
        }, 5000);
    });

    // Confirm dialogs
    document.querySelectorAll('[data-confirm]').forEach(function(el) {
        el.addEventListener('click', function(e) {
            if (!confirm(this.dataset.confirm || 'Are you sure?')) {
                e.preventDefault();
            }
        });
    });

    // Table row click navigation
    document.querySelectorAll('[data-href]').forEach(function(el) {
        el.style.cursor = 'pointer';
        el.addEventListener('click', function() {
            window.location.href = this.dataset.href;
        });
    });

    // Status badge helper
    window.ghBadge = function(status) {
        return '<span class="gh-badge-status gh-badge-' + status + '">' + status.replace(/_/g, ' ') + '</span>';
    };
});