class ComparisonHub {
    constructor() {
        this.theme = localStorage.getItem('theme') || 'dark';
        this.init();
    }

    init() {
        this.initTheme();
        this.initAnimations();
        this.initCounters();
        this.initModalHandlers();
        this.initTooltips();
    }

    // Theme management
    initTheme() {
        document.documentElement.setAttribute('data-bs-theme', this.theme);
        this.updateThemeIcon();
    }

    toggleTheme() {
        this.theme = this.theme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-bs-theme', this.theme);
        localStorage.setItem('theme', this.theme);
        this.updateThemeIcon();
        
        // Smooth transition
        document.body.style.transition = 'all 0.3s ease';
        setTimeout(() => {
            document.body.style.transition = '';
        }, 300);
    }

    updateThemeIcon() {
        const icon = document.getElementById('theme-icon');
        if (icon) {
            icon.className = this.theme === 'dark' 
                ? 'bi bi-sun-fill' 
                : 'bi bi-moon-stars';
        }
    }

    // Animation observers
    initAnimations() {
        // Intersection Observer for scroll animations
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const delay = entry.target.dataset.delay || 0;
                    setTimeout(() => {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translateY(0)';
                    }, delay);
                }
            });
        }, observerOptions);

        // Observe all animate-card elements
        document.querySelectorAll('.animate-card').forEach(card => {
            observer.observe(card);
        });
    }

    // Counter animations
    initCounters() {
        const counters = document.querySelectorAll('.counter');
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.animateCounter(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        });

        counters.forEach(counter => observer.observe(counter));
    }

    animateCounter(element) {
        const target = parseInt(element.dataset.target) || 0;
        const duration = 2000;
        const steps = 60;
        const increment = target / steps;
        let current = 0;
        
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                element.textContent = target;
                clearInterval(timer);
            } else {
                element.textContent = Math.floor(current);
            }
        }, duration / steps);
    }

    // Modal handlers
    initModalHandlers() {
        // Handle modal backdrop clicks
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                const modal = bootstrap.Modal.getInstance(e.target);
                if (modal) modal.hide();
            }
        });
    }

    // Initialize tooltips
    initTooltips() {
        const tooltipTriggerList = [].slice.call(
            document.querySelectorAll('[data-bs-toggle="tooltip"]')
        );
        tooltipTriggerList.map(tooltipTriggerEl => {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Utility functions
    showNotification(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = `
            top: 20px; 
            right: 20px; 
            z-index: 9999; 
            min-width: 300px;
            animation: slideInRight 0.3s ease-out;
        `;
        
        notification.innerHTML = `
            <i class="bi bi-${this.getNotificationIcon(type)} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto remove
        setTimeout(() => {
            if (notification.parentElement) {
                notification.style.opacity = '0';
                notification.style.transform = 'translateX(100%)';
                setTimeout(() => notification.remove(), 300);
            }
        }, duration);
    }

    getNotificationIcon(type) {
        const icons = {
            success: 'check-circle-fill',
            danger: 'exclamation-triangle-fill',
            warning: 'exclamation-triangle-fill',
            info: 'info-circle-fill'
        };
        return icons[type] || 'info-circle-fill';
    }
}

// Global functions for template use
function showCreateModal() {
    const modal = new bootstrap.Modal(document.getElementById('createAnalysisModal'));
    modal.show();
}

function toggleTheme() {
    window.comparisonHub.toggleTheme();
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.comparisonHub = new ComparisonHub();
    
    // Handle create analysis form
    const createForm = document.getElementById('createAnalysisForm');
    if (createForm) {
        createForm.addEventListener('submit', handleCreateAnalysis);
    }
});

async function handleCreateAnalysis(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const submitBtn = e.target.querySelector('button[type="submit"]');
    
    // Show loading state
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<span class="loading-spinner me-2"></span>Creating...';
    submitBtn.disabled = true;
    
    try {
        const response = await fetch('/create-analysis', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Hide modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('createAnalysisModal'));
            modal.hide();
            
            // Show success notification
            window.comparisonHub.showNotification(
                'Analysis created successfully!', 
                'success'
            );
            
            // Redirect to analysis setup
            setTimeout(() => {
                window.location.href = `/analysis/${result.analysis_id}/setup`;
            }, 1000);
        } else {
            throw new Error(result.error || 'Failed to create analysis');
        }
    } catch (error) {
        window.comparisonHub.showNotification(
            error.message, 
            'danger'
        );
    } finally {
        // Restore button state
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + K to open search (future feature)
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        // Future: open search modal
    }
    
    // Ctrl/Cmd + N to create new analysis
    if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
        showCreateModal();
    }
});
