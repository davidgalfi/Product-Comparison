class AnalysisSetup {
    constructor() {
        this.analysisId = window.location.pathname.split('/')[2];
        this.init();
    }

    init() {
        this.initFieldForm();
        this.initSortable();
        this.initFieldSuggestions();
        this.initPreview();
        this.loadFieldSuggestions();
    }

    initFieldForm() {
        const form = document.getElementById('fieldForm');
        const fieldType = document.getElementById('fieldType');
        const unitSection = document.getElementById('unitSection');

        // Show/hide unit field based on type
        fieldType.addEventListener('change', () => {
            const showUnit = ['number', 'decimal', 'price'].includes(fieldType.value);
            unitSection.style.display = showUnit ? 'block' : 'none';
        });

        // Handle form submission
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.addField(new FormData(form));
        });
    }

    async addField(formData) {
        try {
            const data = {
                field_name: formData.get('field_name'),
                field_type: formData.get('field_type'),
                field_unit: formData.get('field_unit') || '',
                is_required: formData.has('is_required')
            };

            const response = await fetch(`/analysis/${this.analysisId}/fields`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification('Field added successfully!', 'success');
                this.addFieldToList(result.field_id, data);
                document.getElementById('fieldForm').reset();
                document.getElementById('unitSection').style.display = 'none';
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            this.showNotification(error.message, 'error');
        }
    }

    addFieldToList(fieldId, fieldData) {
        const fieldsList = document.getElementById('fieldsList');
        
        // Create empty state if fields list doesn't exist
        if (!fieldsList) {
            location.reload(); // Reload to show fields list
            return;
        }

        const fieldItem = this.createFieldElement(fieldId, fieldData);
        fieldsList.appendChild(fieldItem);
        
        // Animate in
        fieldItem.style.opacity = '0';
        fieldItem.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            fieldItem.style.transition = 'all 0.3s ease';
            fieldItem.style.opacity = '1';
            fieldItem.style.transform = 'translateY(0)';
        }, 100);
    }

    createFieldElement(fieldId, fieldData) {
        const div = document.createElement('div');
        div.className = 'field-item glass-card p-3 mb-3';
        div.setAttribute('data-field-id', fieldId);
        
        div.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="drag-handle me-3">
                    <i class="bi bi-grip-vertical text-muted"></i>
                </div>
                
                <div class="field-info flex-grow-1">
                    <div class="d-flex align-items-center mb-1">
                        <h5 class="mb-0 me-2">${fieldData.field_name}</h5>
                        ${fieldData.is_required ? '<span class="badge bg-danger">Required</span>' : ''}
                        ${fieldData.field_unit ? `<span class="badge bg-info ms-1">${fieldData.field_unit}</span>` : ''}
                    </div>
                    <small class="text-muted">
                        <i class="bi bi-gear me-1"></i>${this.getFieldTypeLabel(fieldData.field_type)}
                    </small>
                </div>
                
                <div class="field-actions">
                    <button class="btn btn-outline-primary btn-sm me-1" onclick="editField(${fieldId})">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-danger btn-sm" onclick="deleteField(${fieldId})">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
        `;
        
        return div;
    }

    getFieldTypeLabel(type) {
        const types = {
            'text': 'Text',
            'number': 'Number',
            'decimal': 'Decimal',
            'boolean': 'Yes/No',
            'select': 'Dropdown',
            'rating': 'Rating (1-5)',
            'price': 'Price',
            'date': 'Date'
        };
        return types[type] || 'Text';
    }

    initSortable() {
        const fieldsList = document.getElementById('fieldsList');
        if (!fieldsList) return;

        // Simple drag and drop (you can use SortableJS for more features)
        let draggedElement = null;

        fieldsList.addEventListener('dragstart', (e) => {
            if (e.target.closest('.field-item')) {
                draggedElement = e.target.closest('.field-item');
                e.target.style.opacity = '0.5';
            }
        });

        fieldsList.addEventListener('dragend', (e) => {
            if (e.target.closest('.field-item')) {
                e.target.style.opacity = '1';
                this.updateFieldOrder();
            }
        });

        fieldsList.addEventListener('dragover', (e) => {
            e.preventDefault();
        });

        fieldsList.addEventListener('drop', (e) => {
            e.preventDefault();
            const targetItem = e.target.closest('.field-item');
            
            if (targetItem && draggedElement && targetItem !== draggedElement) {
                const rect = targetItem.getBoundingClientRect();
                const mouseY = e.clientY;
                
                if (mouseY < rect.top + rect.height / 2) {
                    fieldsList.insertBefore(draggedElement, targetItem);
                } else {
                    fieldsList.insertBefore(draggedElement, targetItem.nextSibling);
                }
            }
        });

        // Make field items draggable
        document.querySelectorAll('.field-item').forEach(item => {
            item.setAttribute('draggable', 'true');
        });
    }

    async updateFieldOrder() {
        const fieldIds = Array.from(document.querySelectorAll('.field-item'))
            .map(item => parseInt(item.getAttribute('data-field-id')));

        try {
            const response = await fetch(`/analysis/${this.analysisId}/fields/reorder`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ field_ids: fieldIds })
            });

            const result = await response.json();
            if (!result.success) {
                throw new Error(result.error);
            }
        } catch (error) {
            console.error('Error updating field order:', error);
        }
    }

    loadFieldSuggestions() {
        const category = document.querySelector('p.text-muted').textContent.trim();
        const suggestions = this.getFieldSuggestions(category);
        
        this.renderSuggestions('fieldSuggestions', suggestions);
        this.renderSuggestions('quickSuggestions', suggestions.slice(0, 4));
    }

    getFieldSuggestions(category) {
        const suggestions = {
            'Electronics': [
                { name: 'Brand', type: 'text' },
                { name: 'Model', type: 'text' },
                { name: 'Price', type: 'price', unit: '$' },
                { name: 'Screen Size', type: 'decimal', unit: 'inches' },
                { name: 'Resolution', type: 'text' },
                { name: 'Refresh Rate', type: 'number', unit: 'Hz' },
                { name: 'Connectivity', type: 'text' },
                { name: 'Warranty', type: 'text' }
            ],
            'Fashion': [
                { name: 'Brand', type: 'text' },
                { name: 'Material', type: 'text' },
                { name: 'Color', type: 'text' },
                { name: 'Size', type: 'text' },
                { name: 'Price', type: 'price', unit: '$' },
                { name: 'Waterproof', type: 'boolean' },
                { name: 'Weight', type: 'decimal', unit: 'oz' },
                { name: 'Rating', type: 'rating' }
            ],
            'Books': [
                { name: 'Author', type: 'text' },
                { name: 'Publisher', type: 'text' },
                { name: 'Publication Date', type: 'date' },
                { name: 'Pages', type: 'number' },
                { name: 'Price', type: 'price', unit: '$' },
                { name: 'Rating', type: 'rating' },
                { name: 'Genre', type: 'text' },
                { name: 'Language', type: 'text' }
            ]
        };

        return suggestions[category] || suggestions['Electronics'];
    }

    renderSuggestions(containerId, suggestions) {
        const container = document.getElementById(containerId);
        if (!container) return;

        container.innerHTML = suggestions.map(suggestion => `
            <button class="btn btn-outline-primary btn-sm me-2 mb-2 suggestion-btn" 
                    data-name="${suggestion.name}" 
                    data-type="${suggestion.type}"
                    data-unit="${suggestion.unit || ''}">
                <i class="bi bi-plus me-1"></i>${suggestion.name}
            </button>
        `).join('');

        // Add click handlers
        container.querySelectorAll('.suggestion-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.fillFieldForm(
                    btn.dataset.name,
                    btn.dataset.type,
                    btn.dataset.unit
                );
            });
        });
    }

    fillFieldForm(name, type, unit) {
        document.getElementById('fieldName').value = name;
        document.getElementById('fieldType').value = type;
        
        if (unit) {
            document.getElementById('fieldUnit').value = unit;
            document.getElementById('unitSection').style.display = 'block';
        }

        // Trigger change event
        document.getElementById('fieldType').dispatchEvent(new Event('change'));
        
        // Focus on add button
        document.querySelector('#fieldForm button[type="submit"]').focus();
    }

    initPreview() {
        const previewBtn = document.getElementById('previewBtn');
        if (!previewBtn) return;

        previewBtn.addEventListener('click', () => {
            this.generateFormPreview();
        });
    }

    generateFormPreview() {
        const fields = Array.from(document.querySelectorAll('.field-item'));
        const previewContainer = document.getElementById('formPreview');
        
        if (fields.length === 0) {
            previewContainer.innerHTML = '<p class="text-muted">No fields to preview. Add some fields first.</p>';
            return;
        }

        let formHTML = '<form class="preview-form">';
        
        // Basic object info
        formHTML += `
            <div class="row mb-3">
                <div class="col-md-6">
                    <label class="form-label">Object Name *</label>
                    <input type="text" class="form-control" placeholder="Enter object name">
                </div>
                <div class="col-md-6">
                    <label class="form-label">Brand</label>
                    <input type="text" class="form-control" placeholder="Enter brand">
                </div>
            </div>
        `;

        // Custom fields
        fields.forEach(fieldItem => {
            const fieldName = fieldItem.querySelector('h5').textContent;
            const isRequired = fieldItem.querySelector('.badge.bg-danger') !== null;
            const unit = fieldItem.querySelector('.badge.bg-info')?.textContent || '';
            
            formHTML += this.generateFieldPreview(fieldName, isRequired, unit);
        });

        formHTML += '</form>';
        previewContainer.innerHTML = formHTML;

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('previewModal'));
        modal.show();
    }

    generateFieldPreview(fieldName, isRequired, unit) {
        const label = `${fieldName}${isRequired ? ' *' : ''}${unit ? ` (${unit})` : ''}`;
        
        return `
            <div class="mb-3">
                <label class="form-label">${label}</label>
                <input type="text" class="form-control" placeholder="Enter ${fieldName.toLowerCase()}">
            </div>
        `;
    }

    showNotification(message, type) {
        // Use the global notification system from main.js
        if (window.comparisonHub) {
            window.comparisonHub.showNotification(message, type);
        }
    }
}

// Global functions for template use
async function deleteField(fieldId) {
    if (!confirm('Are you sure you want to delete this field? This will also delete all data for this field.')) {
        return;
    }

    try {
        const analysisId = window.location.pathname.split('/')[2];
        const response = await fetch(`/analysis/${analysisId}/fields/${fieldId}`, {
            method: 'DELETE'
        });

        const result = await response.json();
        
        if (result.success) {
            // Remove field from UI
            const fieldElement = document.querySelector(`[data-field-id="${fieldId}"]`);
            fieldElement.style.transition = 'all 0.3s ease';
            fieldElement.style.opacity = '0';
            fieldElement.style.transform = 'translateX(-100%)';
            
            setTimeout(() => {
                fieldElement.remove();
            }, 300);
            
            window.comparisonHub?.showNotification('Field deleted successfully!', 'success');
        } else {
            throw new Error(result.error);
        }
    } catch (error) {
        window.comparisonHub?.showNotification(error.message, 'danger');
    }
}

function editField(fieldId) {
    // TODO: Implement field editing modal
    window.comparisonHub?.showNotification('Field editing coming soon!', 'info');
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname.includes('/setup')) {
        window.analysisSetup = new AnalysisSetup();
    }
});
