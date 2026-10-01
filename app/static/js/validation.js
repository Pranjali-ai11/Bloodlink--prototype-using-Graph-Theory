const ValidationRules = {
    password: {
        pattern: /^(?=.*[A-Z])(?=.*[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]).{8,}$/,
        message: 'Password must be at least 8 characters with 1 uppercase letter and 1 special character (!@#$%^&*)'
    },
    phone: {
        pattern: /^\d{10}$/,
        message: 'Phone number must be exactly 10 digits'
    },
    
    email: {
        pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
        message: 'Please enter a valid email address'
    }
};

function validatePassword(password) {
    const rules = ValidationRules.password;
    
    if (password.length < 8) {
        return { valid: false, message: 'Password must be at least 8 characters' };
    }
    
    if (!/[A-Z]/.test(password)) {
        return { valid: false, message: 'Password must contain at least 1 uppercase letter' };
    }
    
    if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
        return { valid: false, message: 'Password must contain at least 1 special character (!@#$%^&*)' };
    }
    
    return { valid: true, message: 'Password is strong' };
}
function validatePhone(phone) {
    const cleaned = phone.replace(/\D/g, '');
    
    if (cleaned.length !== 10) {
        return { valid: false, message: 'Phone number must be exactly 10 digits' };
    }
    
    return { valid: true, message: 'Phone number is valid' };
}
function validateEmail(email) {
    if (!ValidationRules.email.pattern.test(email)) {
        return { valid: false, message: ValidationRules.email.message };
    }
    return { valid: true, message: 'Email is valid' };
}
function validateAge(age) {
    const parsedAge = Number(age);
    if (!Number.isInteger(parsedAge) || parsedAge < 0) {
        return { valid: false, message: 'Please enter a valid age.' };
    }
    const role = document.getElementById('role')?.value || 'donor';
    if (role === 'donor' && parsedAge < 18) {
        return { valid: false, message: 'Donors must be 18 or older to register.' };
    }
    return { valid: true, message: 'Age is valid.' };
}
function showFieldError(fieldId, message) {
    const field = document.getElementById(fieldId);
    if (!field) return;
    
    field.classList.add('error');
    
    let errorDiv = field.nextElementSibling;
    if (!errorDiv || !errorDiv.classList.contains('error-text')) {
        errorDiv = document.createElement('div');
        errorDiv.className = 'error-text show';
        field.parentNode.insertBefore(errorDiv, field.nextSibling);
    }
    
    errorDiv.textContent = message;
    errorDiv.classList.add('show');
}
function clearFieldError(fieldId) {
    const field = document.getElementById(fieldId);
    if (!field) return;
    
    field.classList.remove('error');
    
    const errorDiv = field.nextElementSibling;
    if (errorDiv && errorDiv.classList.contains('error-text')) {
        errorDiv.classList.remove('show');
    }
}
function attachFieldValidation(fieldId, validationFn) {
    const field = document.getElementById(fieldId);
    if (!field) return;
    
    field.addEventListener('blur', function() {
        const result = validationFn(this.value);
        
        if (!result.valid) {
            showFieldError(fieldId, result.message);
        } else {
            clearFieldError(fieldId);
        }
    });
    
    field.addEventListener('input', function() {
        clearFieldError(fieldId);
    });
}
function validateFormBeforeSubmit(formId, requiredFields) {
    const form = document.getElementById(formId);
    if (!form) return true;
    
    let isValid = true;
    
    requiredFields.forEach(fieldConfig => {
        const field = document.getElementById(fieldConfig.id);
        if (!field) return;
        
        const value = field.value.trim();
        if (!value) {
            showFieldError(fieldConfig.id, 'This field is required');
            isValid = false;
            return;
        }
        if (fieldConfig.validate) {
            const result = fieldConfig.validate(value);
            if (!result.valid) {
                showFieldError(fieldConfig.id, result.message);
                isValid = false;
                return;
            }
        }
        
        clearFieldError(fieldConfig.id);
    });
    
    return isValid;
}
function markRequiredFields(formId, requiredFieldIds) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    requiredFieldIds.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        const label = field ? field.closest('.form-group')?.querySelector('label') : null;
        
        if (label && !label.innerHTML.includes('<span class="required">*</span>')) {
            const span = document.createElement('span');
            span.className = 'required';
            span.textContent = '*';
            label.appendChild(span);
        }
    });
}
