class ObjectForm {
    constructor() {
        this.init();
    }

    init() {
        this.initRatingInputs();
        this.initFormValidation();
        this.initImagePreview();
    }

    initRatingInputs() {
        document.querySelectorAll('.rating-input').forEach(ratingContainer => {
            const stars = ratingContainer.querySelectorAll('.rating-star');
            const hiddenInput = ratingContainer.querySelector('input[type="hidden"]');
            const currentRating = parseInt(ratingContainer.dataset.rating) || 0;

            // Set initial rating
            this.updateStars(stars, currentRating);

            stars.forEach((star, index) => {
                star.addEventListener('click', () => {
                    const rating = index + 1;
                    hiddenInput.value = rating;
                    this.updateStars(stars, rating);
                });

                star.addEventListener('mouseover', () => {
                    this.updateStars(stars, index + 1, true);
                });
            });

            ratingContainer.addEventListener('mouseleave', () => {
                const currentValue = parseInt(hiddenInput.value) || 0;
                this.updateStars(stars, currentValue);
            });
        });
    }

    updateStars(stars, rating, isHover = false) {
        stars.forEach((star, index) => {
            star.classList.remove('bi-star', 'bi-star-fill');
            
            if (index < rating) {
                star.classList.add('bi-star-fill');
                star.style.color = isHover ? '#ffc107' : '#ffb400';
            } else {
                star.classList.add('bi-star');
                star.style.color = '#dee2e6';
            }
        });
    }

    initFormValidation() {
        const form = document.getElementById('objectForm');
        if (!form) return;

        form.addEventListener('submit', (e) => {
            if (!this.validateForm(form)) {
                e.preventDefault();
                this.showValidationErrors();
            }
        });

        // Real-time validation
        const inputs = form.querySelectorAll('input[required], select[required]');
        inputs.forEach(input => {
            input.addEventListener('blur', () => {
                this.validateField(input);
            });
        });
    }

    validateForm(form) {
        let isValid = true;
        const requiredFields = form.querySelectorAll('[required]');

        requiredFields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });

        return isValid;
    }

    validateField(field) {
        const value = field.value.trim();
        const isValid = value !== '';

        // Remove existing validation classes
        field.classList.remove('is-valid', 'is-invalid');
        
        // Add appropriate class
        field.classList.add(isValid ? 'is-valid' : 'is-invalid');

        return isValid;
    }

    showValidationErrors() {
        window.comparisonHub?.showNotification(
            'Please fill in all required fields',
            'warning'
        );
    }

    initImagePreview() {
        const imageUrlInput = document.getElementById('imageUrl');
        if (!imageUrlInput) return;

        imageUrlInput.addEventListener('blur', () => {
            const url = imageUrlInput.value.trim();
            if (url) {
                this.showImagePreview(url);
            } else {
                this.removeImagePreview();
            }
        });
    }

    showImagePreview(url) {
        // Remove existing preview
        this.removeImagePreview();

        const previewContainer = document.createElement('div');
        previewContainer.className = 'image-preview mt-2';
        previewContainer.innerHTML = `
            <div class="d-flex align-items-center">
                <img src="${url}" alt="Preview" class="preview-image me-3" 
                     style="width: 60px; height: 60px; object-fit: cover; border-radius: 8px;"
                     onerror="this.parentElement.parentElement.style.display='none'">
                <div>
                    <small class="text-success">
                        <i class="bi bi-check-circle me-1"></i>Image loaded successfully
                    </small>
                </div>
            </div>
        `;

        const imageUrlInput = document.getElementById('imageUrl');
        imageUrlInput.parentElement.appendChild(previewContainer);
    }

    removeImagePreview() {
        const existingPreview = document.querySelector('.image-preview');
        if (existingPreview) {
            existingPreview.remove();
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ObjectForm();
});
