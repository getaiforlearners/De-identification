// Common JavaScript for the Healthcare Data De-Identifier application

// Wait for the document to be ready
document.addEventListener('DOMContentLoaded', function() {
    // Enable all tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Handle connection selection on process page
    var connectionSelect = document.getElementById('connection_id');
    if (connectionSelect) {
        connectionSelect.addEventListener('change', function() {
            var connId = this.value;
            if (!connId) {
                // Clear patient table select
                document.getElementById('patient_table').innerHTML = '<option value="">Select table</option>';
                return;
            }
            
            // Show spinner
            document.getElementById('table-loading').classList.remove('d-none');
            
            // Get tables for the selected connection
            fetch(`/get-tables/${connId}`)
                .then(response => response.json())
                .then(data => {
                    document.getElementById('table-loading').classList.add('d-none');
                    
                    if (data.success) {
                        // Populate patient table dropdown
                        var tableSelect = document.getElementById('patient_table');
                        tableSelect.innerHTML = '<option value="">Select table</option>';
                        
                        data.tables.forEach(function(table) {
                            var option = document.createElement('option');
                            option.value = table;
                            option.textContent = table;
                            tableSelect.appendChild(option);
                        });
                    } else {
                        showAlert('danger', 'Error fetching tables: ' + data.message);
                    }
                })
                .catch(error => {
                    document.getElementById('table-loading').classList.add('d-none');
                    showAlert('danger', 'Error: ' + error);
                });
        });
    }
    
    // Handle patient table selection
    var patientTableSelect = document.getElementById('patient_table');
    if (patientTableSelect) {
        patientTableSelect.addEventListener('change', function() {
            var connId = document.getElementById('connection_id').value;
            var tableName = this.value;
            
            if (!connId || !tableName) {
                // Clear ID field select
                document.getElementById('patient_id_field').innerHTML = '<option value="">Select field</option>';
                return;
            }
            
            // Show spinner
            document.getElementById('field-loading').classList.remove('d-none');
            
            // Get columns for the selected table
            fetch(`/get-columns/${connId}/${tableName}`)
                .then(response => response.json())
                .then(data => {
                    document.getElementById('field-loading').classList.add('d-none');
                    
                    if (data.success) {
                        // Populate ID field dropdown
                        var fieldSelect = document.getElementById('patient_id_field');
                        fieldSelect.innerHTML = '<option value="">Select field</option>';
                        
                        data.columns.forEach(function(column) {
                            var option = document.createElement('option');
                            option.value = column;
                            option.textContent = column;
                            fieldSelect.appendChild(option);
                        });
                    } else {
                        showAlert('danger', 'Error fetching columns: ' + data.message);
                    }
                })
                .catch(error => {
                    document.getElementById('field-loading').classList.add('d-none');
                    showAlert('danger', 'Error: ' + error);
                });
        });
    }
    
    // Process form submission
    var processForm = document.getElementById('process-form');
    if (processForm) {
        processForm.addEventListener('submit', function(event) {
            // Validate form
            if (!validateProcessForm()) {
                event.preventDefault();
                return false;
            }
            
            // Show processing overlay
            showProcessingOverlay();
        });
    }
    
    // Select/deselect all rules
    var selectAllRules = document.getElementById('select-all-rules');
    if (selectAllRules) {
        selectAllRules.addEventListener('change', function() {
            var checkboxes = document.querySelectorAll('input[name="rule_ids"]');
            checkboxes.forEach(function(checkbox) {
                checkbox.checked = selectAllRules.checked;
            });
        });
    }
    
    // Select/deselect all mappings
    var selectAllMappings = document.getElementById('select-all-mappings');
    if (selectAllMappings) {
        selectAllMappings.addEventListener('change', function() {
            var checkboxes = document.querySelectorAll('input[name="mapping_ids"]');
            checkboxes.forEach(function(checkbox) {
                checkbox.checked = selectAllMappings.checked;
            });
        });
    }
});

// Show an alert message
function showAlert(type, message) {
    var alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Insert at the top of the main content
    var mainContent = document.querySelector('main');
    if (mainContent) {
        mainContent.insertBefore(alertDiv, mainContent.firstChild);
    }
    
    // Auto-dismiss after 5 seconds
    setTimeout(function() {
        alertDiv.remove();
    }, 5000);
}

// Validate the process form
function validateProcessForm() {
    var connectionId = document.getElementById('connection_id').value;
    if (!connectionId) {
        showAlert('danger', 'Please select a database connection.');
        return false;
    }
    
    // Check if at least one rule is selected
    var ruleCheckboxes = document.querySelectorAll('input[name="rule_ids"]:checked');
    if (ruleCheckboxes.length === 0) {
        showAlert('danger', 'Please select at least one de-identification rule.');
        return false;
    }
    
    // If patient table is selected, ID field must also be selected
    var patientTable = document.getElementById('patient_table').value;
    var patientIdField = document.getElementById('patient_id_field').value;
    
    if (patientTable && !patientIdField) {
        showAlert('danger', 'Please select a patient ID field.');
        return false;
    }
    
    // All validations passed
    return true;
}

// Show processing overlay
function showProcessingOverlay() {
    var overlay = document.createElement('div');
    overlay.className = 'spinner-overlay';
    overlay.innerHTML = `
        <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Processing...</span>
        </div>
        <div class="spinner-text">
            De-identification in progress... This may take a few minutes.
        </div>
    `;
    
    document.body.appendChild(overlay);
}

// Handle chart creation on results page (if needed)
function createProcessingChart(completedCount, modifiedCount) {
    // If Chart.js is included
    if (typeof Chart !== 'undefined') {
        var ctx = document.getElementById('processing-chart');
        if (ctx) {
            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Modified', 'Unchanged'],
                    datasets: [{
                        data: [modifiedCount, completedCount - modifiedCount],
                        backgroundColor: ['#0d6efd', '#6c757d']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        }
    }
}
