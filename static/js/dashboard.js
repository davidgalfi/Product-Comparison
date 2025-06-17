class DashboardManager {
    constructor() {
        this.animationType = 'zoom';
        this.init();
    }

    init() {
        console.log('Dashboard Manager initializing...'); // Debug log
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.bindAnalysisActions();
            });
        } else {
            this.bindAnalysisActions();
        }
    }

    bindAnalysisActions() {
        console.log('Binding analysis actions...'); // Debug log
        
        // Delete analysis buttons
        document.addEventListener('click', (e) => {
            if (e.target.closest('.delete-analysis-btn')) {
                e.preventDefault();
                const btn = e.target.closest('.delete-analysis-btn');
                const analysisId = btn.getAttribute('data-analysis-id'); // More reliable
                const analysisName = btn.getAttribute('data-analysis-name'); // More reliable
                
                console.log('Delete clicked:', analysisId, analysisName); // Debug log
                
                if (analysisId && analysisName) {
                    this.showFancyDeleteConfirmation(analysisId, analysisName);
                } else {
                    console.error('Missing analysis data attributes');
                }
            }
        });

        // Duplicate analysis buttons
        document.addEventListener('click', (e) => {
            if (e.target.closest('.duplicate-analysis-btn')) {
                e.preventDefault();
                const btn = e.target.closest('.duplicate-analysis-btn');
                const analysisId = btn.getAttribute('data-analysis-id');
                
                console.log('Duplicate clicked:', analysisId); // Debug log
                
                if (analysisId) {
                    this.duplicateAnalysis(analysisId);
                }
            }
        });
    }

    showFancyDeleteConfirmation(analysisId, analysisName) {
        console.log('Showing delete confirmation for:', analysisName); // Debug log
        
        // Remove any existing modals
        const existingModal = document.querySelector('.delete-confirmation-modal');
        if (existingModal) {
            existingModal.remove();
        }
        
        const modal = this.createAnimatedConfirmationModal(analysisName);
        document.body.appendChild(modal);
        
        // Add event listeners after modal is in DOM
        setTimeout(() => {
            const confirmBtn = modal.querySelector('.confirm-delete');
            const cancelBtn = modal.querySelector('.cancel-delete');
            const backdrop = modal.querySelector('.modal-backdrop');
            
            if (confirmBtn) {
                confirmBtn.addEventListener('click', () => {
                    const selectedAnimation = modal.querySelector('#animationType')?.value || this.animationType;
                    this.deleteAnalysisWithAnimation(analysisId, selectedAnimation);
                    modal.remove();
                });
            }
            
            if (cancelBtn) {
                cancelBtn.addEventListener('click', () => {
                    modal.remove();
                });
            }
            
            if (backdrop) {
                backdrop.addEventListener('click', () => {
                    modal.remove();
                });
            }
        }, 10);
    }

    createAnimatedConfirmationModal(analysisName) {
        const modal = document.createElement('div');
        modal.className = 'delete-confirmation-modal';
        modal.innerHTML = `
            <div class="modal-backdrop" style="
                position: fixed; 
                top: 0; 
                left: 0; 
                width: 100%; 
                height: 100%;
                background: rgba(0,0,0,0.6); 
                z-index: 10500;
                backdrop-filter: blur(5px);
            "></div>
            <div class="modal-content glass-card" style="
                position: fixed; 
                top: 50%; 
                left: 50%; 
                transform: translate(-50%, -50%);
                z-index: 10501; 
                max-width: 500px; 
                width: 90%;
                padding: 2rem;
                animation: modalFadeIn 0.3s ease-out;
            ">
                <h4 class="gradient-text mb-3">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    Confirm Deletion
                </h4>
                <p class="mb-2">Are you sure you want to delete "<strong>${analysisName}</strong>"?</p>
                <p class="text-muted mb-4">This action cannot be undone and will remove all objects and data.</p>
                
                <div class="animation-selector mb-4">
                    <label class="form-label fw-semibold">Choose delete animation:</label>
                    <select class="form-select" id="animationType">
                        <option value="zoom">🎯 Zoom Out</option>
                        <option value="slide">➡️ Slide Away</option>
                        <option value="fall">⬇️ Fall Away</option>
                        <option value="shredder">✂️ Shredder Effect</option>
                    </select>
                </div>
                
                <div class="modal-actions">
                    <button class="btn btn-secondary cancel-delete">
                        <i class="bi bi-x me-1"></i>Cancel
                    </button>
                    <button class="btn btn-danger confirm-delete">
                        <i class="bi bi-trash me-1"></i>Delete with Animation
                    </button>
                </div>
            </div>
        `;
        
        return modal;
    }

    async deleteAnalysisWithAnimation(analysisId, selectedAnimation) {
        console.log('Starting delete animation:', selectedAnimation); // Debug log
        
        const analysisCard = document.querySelector(`[data-analysis-id="${analysisId}"]`);
        
        if (analysisCard) {
            // Add animation class
            analysisCard.classList.add(`deleting-${selectedAnimation}`);
            
            // For shredder effect, create pieces
            if (selectedAnimation === 'shredder') {
                this.createShredderEffect(analysisCard);
            }
            
            // Wait for animation to complete
            await this.waitForAnimation(analysisCard, selectedAnimation);
        }
        
        // Make API call
        try {
            const response = await fetch(`/analysis/${analysisId}/delete`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' }
            });

            const result = await response.json();

            if (result.success) {
                if (analysisCard) {
                    analysisCard.remove();
                    
                    // Check if no analyses left
                    const remainingCards = document.querySelectorAll('.analysis-card').length;
                    if (remainingCards === 0) {
                        setTimeout(() => location.reload(), 500);
                    }
                }
                
                this.showNotification(result.message, 'success');
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            console.error('Delete error:', error); // Debug log
            // Reset card if error occurs
            if (analysisCard) {
                analysisCard.className = analysisCard.className.replace(/deleting-\w+/g, '');
            }
            this.showNotification(`Error deleting analysis: ${error.message}`, 'danger');
        }
    }

    async duplicateAnalysis(analysisId) {
        try {
            this.showNotification('Duplicating analysis...', 'info', 2000);

            const response = await fetch(`/analysis/${analysisId}/duplicate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification(result.message, 'success');
                setTimeout(() => {
                    window.location.href = `/analysis/${result.new_analysis_id}`;
                }, 1500);
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            this.showNotification(`Error duplicating analysis: ${error.message}`, 'danger');
        }
    }

    createShredderEffect(card) {
        const pieces = 8;
        for (let i = 0; i < pieces; i++) {
            const piece = card.cloneNode(true);
            piece.className = `shredder-piece piece-${i % 2 + 1}`;
            piece.style.clipPath = `inset(0 ${(pieces - i - 1) * (100/pieces)}% 0 ${i * (100/pieces)}%)`;
            piece.style.animationDelay = `${i * 0.1}s`;
            card.appendChild(piece);
        }
    }

    waitForAnimation(element, animationType) {
        return new Promise((resolve) => {
            const duration = {
                'zoom': 700,
                'slide': 1000,
                'fall': 1000,
                'shredder': 1700
            };
            
            setTimeout(resolve, duration[animationType] || 1000);
        });
    }

    showNotification(message, type, duration = 5000) {
        // Create fancy notification
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} fancy-notification`;
        notification.style.cssText = `
            position: fixed; 
            top: 20px; 
            right: 20px; 
            z-index: 10502;
            min-width: 300px; 
            animation: slideInRight 0.3s ease-out;
            box-shadow: 0 8px 32px rgba(0,0,0,0.2);
            border-radius: 10px;
            padding: 15px;
        `;
        
        const iconMap = {
            'success': 'bi-check-circle',
            'danger': 'bi-exclamation-triangle',
            'info': 'bi-info-circle'
        };
        
        notification.innerHTML = `
            <i class="bi ${iconMap[type] || 'bi-info-circle'} me-2"></i>${message}
            <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentElement) {
                notification.style.animation = 'slideOutRight 0.3s ease-out';
                setTimeout(() => notification.remove(), 300);
            }
        }, duration);
    }
}

// Initialize immediately
console.log('Initializing Dashboard Manager...'); // Debug log
new DashboardManager();
