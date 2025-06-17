class AnalysisView {
    constructor() {
        this.currentView = 'table';
        this.chart = null;
        this.analysisData = this.parseAnalysisData();
        this.init();
    }

    init() {
        this.initViewSwitching();
        this.initTableSorting();
        this.initChart();
        this.bindEvents();
    }

    parseAnalysisData() {
        // Extract data from the page for JavaScript use
        const objects = [];
        document.querySelectorAll('.object-row').forEach(row => {
            const objectId = row.dataset.objectId;
            const objectName = row.querySelector('.fw-bold').textContent;
            const brand = row.querySelector('.text-muted')?.textContent || '';
            
            const fieldValues = {};
            row.querySelectorAll('.field-value').forEach((cell, index) => {
                const fieldType = cell.dataset.fieldType;
                const value = this.extractCellValue(cell, fieldType);
                fieldValues[index] = value;
            });

            objects.push({
                id: objectId,
                name: objectName,
                brand: brand,
                values: fieldValues
            });
        });

        return { objects };
    }

    extractCellValue(cell, fieldType) {
        switch (fieldType) {
            case 'number':
            case 'decimal':
                const numText = cell.textContent.trim();
                return numText === '-' ? null : parseFloat(numText);
            
            case 'price':
                const priceText = cell.textContent.trim();
                if (priceText === '-') return null;
                return parseFloat(priceText.replace('$', ''));
            
            case 'rating':
                const filledStars = cell.querySelectorAll('.bi-star-fill').length;
                return filledStars;
            
            case 'boolean':
                const badge = cell.querySelector('.badge');
                return badge ? badge.textContent.trim() : null;
            
            default:
                const text = cell.textContent.trim();
                return text === '-' ? null : text;
        }
    }

    initViewSwitching() {
        const tableBtn = document.getElementById('tableViewBtn');
        const cardBtn = document.getElementById('cardViewBtn');
        const chartBtn = document.getElementById('chartViewBtn');

        tableBtn?.addEventListener('click', () => this.switchView('table'));
        cardBtn?.addEventListener('click', () => this.switchView('card'));
        chartBtn?.addEventListener('click', () => this.switchView('chart'));
    }

    switchView(viewType) {
        // Update button states
        document.querySelectorAll('[id$="ViewBtn"]').forEach(btn => {
            btn.classList.remove('active');
        });
        document.getElementById(`${viewType}ViewBtn`).classList.add('active');

        // Show/hide views
        document.querySelectorAll('.comparison-view').forEach(view => {
            view.classList.remove('active');
        });
        document.getElementById(`${viewType}View`).classList.add('active');

        this.currentView = viewType;

        // Initialize chart if switching to chart view
        if (viewType === 'chart') {
            setTimeout(() => this.updateChart(), 100);
        }
    }

    initTableSorting() {
        document.querySelectorAll('.sortable').forEach(header => {
            header.addEventListener('click', () => {
                this.sortTable(header);
            });
        });
    }

    sortTable(header) {
        const table = header.closest('table');
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const columnIndex = Array.from(header.parentElement.children).indexOf(header);
        const fieldType = header.dataset.type;
        
        // Toggle sort direction
        const isAscending = !header.classList.contains('sort-asc');
        
        // Remove sort classes from all headers
        table.querySelectorAll('.sortable').forEach(th => {
            th.classList.remove('sort-asc', 'sort-desc');
        });
        
        // Add sort class to current header
        header.classList.add(isAscending ? 'sort-asc' : 'sort-desc');

        // Sort rows
        rows.sort((a, b) => {
            const aCell = a.children[columnIndex];
            const bCell = b.children[columnIndex];
            
            const aValue = this.extractCellValue(aCell, fieldType);
            const bValue = this.extractCellValue(bCell, fieldType);

            if (aValue === null && bValue === null) return 0;
            if (aValue === null) return isAscending ? 1 : -1;
            if (bValue === null) return isAscending ? -1 : 1;

            let comparison = 0;
            if (typeof aValue === 'number' && typeof bValue === 'number') {
                comparison = aValue - bValue;
            } else {
                comparison = String(aValue).localeCompare(String(bValue));
            }

            return isAscending ? comparison : -comparison;
        });

        // Reorder rows in DOM
        rows.forEach(row => tbody.appendChild(row));

        // Add animation
        rows.forEach((row, index) => {
            row.style.animation = 'none';
            setTimeout(() => {
                row.style.animation = `slideIn 0.3s ease-out ${index * 0.05}s`;
            }, 10);
        });
    }

    initChart() {
        const canvas = document.getElementById('comparisonChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        this.chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Comparison',
                    data: [],
                    backgroundColor: 'rgba(54, 162, 235, 0.6)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Object Comparison'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        // Bind chart controls
        const fieldSelect = document.getElementById('chartFieldSelect');
        const typeSelect = document.getElementById('chartTypeSelect');
        
        fieldSelect?.addEventListener('change', () => this.updateChart());
        typeSelect?.addEventListener('change', () => this.updateChart());
    }

    updateChart() {
        if (!this.chart) return;

        const fieldSelect = document.getElementById('chartFieldSelect');
        const typeSelect = document.getElementById('chartTypeSelect');
        
        if (!fieldSelect || !typeSelect) return;

        const selectedField = fieldSelect.selectedIndex;
        const chartType = typeSelect.value;

        // Extract data for selected field
        const labels = this.analysisData.objects.map(obj => obj.name);
        const data = this.analysisData.objects.map(obj => obj.values[selectedField] || 0);

        // Update chart type
        this.chart.config.type = chartType;
        
        // Update data
        this.chart.data.labels = labels;
        this.chart.data.datasets[0].data = data;
        this.chart.data.datasets[0].label = fieldSelect.options[fieldSelect.selectedIndex].text;

        // Update chart
        this.chart.update();
    }

    bindEvents() {
        // Add keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case '1':
                        e.preventDefault();
                        this.switchView('table');
                        break;
                    case '2':
                        e.preventDefault();
                        this.switchView('card');
                        break;
                    case '3':
                        e.preventDefault();
                        this.switchView('chart');
                        break;
                }
            }
        });
    }
}

// Global functions for template use
function editObject(objectId) {
    const analysisId = window.location.pathname.split('/')[2];
    window.location.href = `/analysis/${analysisId}/objects/${objectId}/edit`;
}

async function deleteObject(objectId) {
    if (!confirm('Are you sure you want to delete this object? This action cannot be undone.')) {
        return;
    }

    try {
        const analysisId = window.location.pathname.split('/')[2];
        const response = await fetch(`/analysis/${analysisId}/objects/${objectId}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (result.success) {
            // Remove object from UI
            const objectRow = document.querySelector(`[data-object-id="${objectId}"]`);
            if (objectRow) {
                objectRow.style.transition = 'all 0.3s ease';
                objectRow.style.opacity = '0';
                objectRow.style.transform = 'translateX(-100%)';
                
                setTimeout(() => {
                    objectRow.remove();
                    
                    // Check if no objects left
                    const remainingObjects = document.querySelectorAll('.object-row').length;
                    if (remainingObjects === 0) {
                        location.reload();
                    }
                }, 300);
            }

            window.comparisonHub?.showNotification('Object deleted successfully!', 'success');
        } else {
            throw new Error(result.error);
        }
    } catch (error) {
        window.comparisonHub?.showNotification(error.message, 'danger');
    }
}

function exportAnalysis() {
    const analysisId = window.location.pathname.split('/')[2];
    window.open(`/analysis/${analysisId}/export`, '_blank');
}

function shareAnalysis() {
    const analysisId = window.location.pathname.split('/')[2];
    const url = `${window.location.origin}/analysis/${analysisId}`;
    
    if (navigator.share) {
        navigator.share({
            title: 'Product Comparison Analysis',
            url: url
        });
    } else {
        navigator.clipboard.writeText(url).then(() => {
            window.comparisonHub?.showNotification('Link copied to clipboard!', 'success');
        });
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname.includes('/analysis/') && 
        !window.location.pathname.includes('/setup') && 
        !window.location.pathname.includes('/objects/new')) {
        new AnalysisView();
    }
});
