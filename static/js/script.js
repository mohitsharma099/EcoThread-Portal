/**
 * EcoThread - Application Interactions
 * Handles form validation, DOM manipulation, and UI micro-animations
 */

document.addEventListener('DOMContentLoaded', () => {
    
    // Password toggle functionality on login page
    const toggleBtn = document.getElementById('togglePswd');
    const pswdField = document.getElementById('passwordField');
    
    if (toggleBtn && pswdField) {
        toggleBtn.addEventListener('click', () => {
            if (pswdField.type === 'password') {
                pswdField.type = 'text';
                toggleBtn.innerHTML = '<i class="bi bi-eye-slash"></i>';
            } else {
                pswdField.type = 'password';
                toggleBtn.innerHTML = '<i class="bi bi-eye"></i>';
            }
        });
    }

    // Dynamic row highlighting for chemical inputs
    const chemInputsOuter = document.querySelectorAll('.form-hover-row input');
    
    chemInputsOuter.forEach(input => {
        input.addEventListener('focus', function() {
            this.closest('.form-hover-row').style.backgroundColor = 'rgba(0, 255, 213, 0.1)';
            this.closest('.form-hover-row').style.transition = 'background-color 0.3s';
        });
        
        input.addEventListener('blur', function() {
            if(this.value === '') {
                this.closest('.form-hover-row').style.backgroundColor = 'transparent';
            } else {
                this.closest('.form-hover-row').style.backgroundColor = 'rgba(255, 255, 255, 0.05)';
            }
        });

        // Initialize state for pre-filled forms (if any)
        if(input.value !== '') {
            input.closest('.form-hover-row').style.backgroundColor = 'rgba(255, 255, 255, 0.05)';
        }
    });

    // Auto-dismiss Flash alerts after 5 seconds
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
});
