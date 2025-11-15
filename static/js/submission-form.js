// Form handling and navigation
const activityDeleteState = new WeakMap();

document.addEventListener('DOMContentLoaded', function() {
  const form = document.getElementById('submission-form');
  if (!form) return;
  
  const nextTabInput = document.getElementById('id_next_tab');
  const autosaveInput = document.getElementById('id_autosave');
  const skipValidationInput = document.getElementById('id_skip_validation');
  const currentTabKey = form.dataset.currentTab;
  const expectedTimings = JSON.parse(form.dataset.expectedTimings || '[]');
  const canEdit = (form.dataset.canEdit === '1');

  // Safety: Guard against corrupted form.action like "/.../[object HTMLButtonElement]"
  document.addEventListener('submit', function(ev) {
    const f = ev.target;
    try {
      if (f && typeof f.action === 'string' && f.action.indexOf('[object') !== -1) {
        // Reset to current URL (default action)
        f.removeAttribute('action');
      }
    } catch (e) { /* noop */ }
  });

  // Also sanitize on any action button click
  document.querySelectorAll('button[name="action"]').forEach(btn => {
    btn.addEventListener('click', () => {
      const f = btn.form || document.getElementById('submission-form');
      if (f && typeof f.action === 'string' && f.action.indexOf('[object') !== -1) {
        f.removeAttribute('action');
      }
      // Remove any stray formaction on the button
      if (btn.hasAttribute('formaction')) btn.removeAttribute('formaction');
    });
  });

  // If read-only, hard-disable all inputs inside the form except navigation
  if (!canEdit) {
    const controls = form.querySelectorAll('input, textarea, select, button');
    controls.forEach(el => {
      // keep hidden and navigation elements functional
      if (el.type === 'hidden') return;
      if (el.classList && el.classList.contains('tab-nav')) return;
      // Top tab links are <a>, not included here
      try { el.disabled = true; } catch (e) { /* noop */ }
    });
  }
  
  // Get navigation buttons (may not exist on all tabs)
  const prevButton = document.querySelector('.prev-tab');
  const nextButton = document.querySelector('.next-tab');
  
  // Exit if required elements not found (but navigation buttons are optional)
  if (!nextTabInput || !autosaveInput) {
    console.error('Required form elements not found');
    return;
  }

  // Tab configuration (dynamic if provided by server)
  const DEFAULT_TAB_ORDER = [
    { key: 'projects', label: 'Projects & Activities' },
    { key: 'pct', label: '% Implementation' },
    { key: 'slp', label: 'SLP' },
    { key: 'reading', label: 'Reading (CRLA/PHILIRI)' },
    { key: 'rma', label: 'RMA' },
    { key: 'supervision', label: 'Instructional Supervision & TA' },
    { key: 'adm', label: 'ADM One-Stop-Shop & EiE' }
  ];
  let providedOrder = [];
  try {
    providedOrder = JSON.parse(form.dataset.tabOrder || '[]');
  } catch (e) {
    providedOrder = [];
  }
  const TAB_ORDER = (Array.isArray(providedOrder) && providedOrder.length) ? providedOrder : DEFAULT_TAB_ORDER;

  // Find current tab index
  const currentTabIndex = TAB_ORDER.findIndex(tab => tab.key === currentTabKey);
  if (currentTabIndex === -1) {
    console.error('Invalid current tab:', currentTabKey);
    return;
  }

  // Update button states
  function updateNavigationButtons() {
    if (prevButton) prevButton.disabled = currentTabIndex <= 0;
    if (nextButton) nextButton.disabled = currentTabIndex >= TAB_ORDER.length - 1;
  }

  // Validate form fields before navigation
  function validateForm() {
    const requiredInputs = form.querySelectorAll('input[required], textarea[required], select[required]');
    const emptyFields = [];
    
    // Check each required field
    requiredInputs.forEach(field => {
      if (!field.offsetParent) {
        return;
      }
      const value = field.value?.trim() || '';
      const isEmpty = !value || value === '';
      
      if (isEmpty) {
        emptyFields.push(field);
        field.style.border = '2px solid var(--error-color)';
        field.style.backgroundColor = '#fee';
      } else {
        field.style.border = '';
        field.style.backgroundColor = '';
      }
    });
    
    // If there are empty required fields, show error
    if (emptyFields.length > 0) {
      const firstEmpty = emptyFields[0];
      firstEmpty.scrollIntoView({ behavior: 'smooth', block: 'center' });
      firstEmpty.focus();
      
      alert(`Please fill in all required fields before proceeding. (${emptyFields.length} field${emptyFields.length > 1 ? 's' : ''} missing)`);
      return false;
    }
    
    return true;
  }

  // Navigate to another tab with validation and autosave
  function navigateToTab(targetKey) {
    if (targetKey && targetKey !== currentTabKey) {
      const targetIndex = TAB_ORDER.findIndex(tab => tab.key === targetKey);
      const movingForward = targetIndex !== -1 && targetIndex > currentTabIndex;

      // Only block navigation on validation errors when moving forward
      if (movingForward && !validateForm()) {
        return false;
      }

      // Set target tab and autosave flag
      nextTabInput.value = targetKey;
      if (skipValidationInput) {
        skipValidationInput.value = movingForward ? '0' : '1';
      }
      autosaveInput.value = '1';
      form.submit();
    }
  }

  // Previous button handler
  if (prevButton) {
    prevButton.addEventListener('click', () => {
      if (currentTabIndex > 0) {
        navigateToTab(TAB_ORDER[currentTabIndex - 1].key);
      }
    });
  }

  // Next button handler
  if (nextButton) {
    nextButton.addEventListener('click', () => {
      if (currentTabIndex < TAB_ORDER.length - 1) {
        navigateToTab(TAB_ORDER[currentTabIndex + 1].key);
      }
    });
  }

  // Initialize navigation state
  updateNavigationButtons();

  // Hook tab navigation buttons
  document.querySelectorAll('.tab-nav').forEach(button => {
    button.addEventListener('click', (event) => {
      event.preventDefault();
      const target = button.dataset.navTarget;
      if (!target) return;
      if (canEdit) {
        navigateToTab(target);
      } else {
        const url = new URL(window.location.href);
        url.searchParams.set('tab', target);
        window.location.assign(url.toString());
      }
    });
  });

  // Track which SLP subject is being saved
  const subjectIdInput = document.getElementById('id_current_subject_id');
  const subjectPrefixInput = document.getElementById('id_current_subject_prefix');
  const subjectIndexInput = document.getElementById('id_current_subject_index');

  document.querySelectorAll('.save-subject-btn').forEach(button => {
    button.addEventListener('click', () => {
      if (subjectIdInput) subjectIdInput.value = button.dataset.subjectId || '';
      if (subjectPrefixInput) subjectPrefixInput.value = button.dataset.subjectPrefix || '';
      if (subjectIndexInput) subjectIndexInput.value = button.dataset.subjectIndex || '';
    });
  });

  document.querySelectorAll('button[name="action"][value="save_draft"]').forEach(button => {
    button.addEventListener('click', () => {
      if (subjectIdInput) subjectIdInput.value = '';
      if (subjectPrefixInput) subjectPrefixInput.value = '';
      if (subjectIndexInput) subjectIndexInput.value = '';
    });
  });

  // down or right arrow
  if (form) {
    form.addEventListener('submit', function(e) {
      
      // Log form data
      const formData = new FormData(form);
      for (let [key, value] of formData.entries()) {
        if (key.includes('slp') || key.includes('action') || key.includes('tab')) {
        }
      }
    });
  }

  // Tab link navigation (only intercept in edit mode)
  if (canEdit) {
    document.querySelectorAll('.tabs a').forEach(link => {
      link.addEventListener('click', (e) => {
        const targetTab = link.dataset.tab;
        if (targetTab && targetTab !== currentTabKey) {
          e.preventDefault();
          navigateToTab(targetTab);
        }
      });
    });
  }

  // down or right arrow
  if (expectedTimings.length) {
    const timingWarning = document.getElementById('timing-warning');
    const timingFields = form.querySelectorAll('select[name*="timing"]');
    const showWarningIfNeeded = () => {
      let mismatch = false;
      timingFields.forEach(field => {
        if (field.value && expectedTimings.indexOf(field.value) === -1) {
          mismatch = true;
        }
      });
      if (timingWarning) {
        timingWarning.style.display = mismatch ? 'block' : 'none';
      }
    };
    timingFields.forEach(field => field.addEventListener('change', showWarningIfNeeded));
    showWarningIfNeeded();
  }

  // SLP: Handle "Offered" checkbox to enable/disable row fields and LLC cards
  function initializeSLPOfferedToggle() {
    const cards = document.querySelectorAll('.slp-subject-card');
    
    cards.forEach(card => {
      // Find the "is_offered" checkbox in this card
      const offeredCheckbox = card.querySelector('input[id$="-is_offered"]');
      
      if (!offeredCheckbox) return;
      
      function toggleCardFields() {
        const isOffered = offeredCheckbox.checked;
        
        // Get all inputs and textareas in the card except the checkbox and hidden fields
        const fields = card.querySelectorAll('input:not([id$="-is_offered"]):not([type="hidden"]):not([type="checkbox"]), textarea');
        
        fields.forEach(field => {
          if ('readOnly' in field) {
            field.readOnly = !isOffered;
          }
          field.classList.toggle('slp-field-disabled', !isOffered);
          
          if (!isOffered) {
            if (field.type === 'number') {
              field.value = '0';
            } else {
              field.value = '';
            }
          }
        });
        
        // Visual feedback - disable sections but NOT the offered checkbox area
        const proficiencySection = card.querySelector('.proficiency-section');
        const llcSection = card.querySelector('.llc-section');
        const interventionSection = card.querySelector('.intervention-section');
        const strategySection = card.querySelector('.strategy-section');
        
        if (!isOffered) {
          // Disable sections except the checkbox itself
          if (proficiencySection) {
            const proficiencyGrid = proficiencySection.querySelector('.proficiency-grid');
            if (proficiencyGrid) proficiencyGrid.style.pointerEvents = 'none';
          }
          if (llcSection) llcSection.style.pointerEvents = 'none';
          if (interventionSection) interventionSection.style.pointerEvents = 'none';
          if (strategySection) strategySection.style.pointerEvents = 'none';
          
          card.style.opacity = '0.65';
        } else {
          // Enable all sections
          if (proficiencySection) {
            const proficiencyGrid = proficiencySection.querySelector('.proficiency-grid');
            if (proficiencyGrid) proficiencyGrid.style.pointerEvents = 'auto';
          }
          if (llcSection) llcSection.style.pointerEvents = 'auto';
          if (interventionSection) interventionSection.style.pointerEvents = 'auto';
          if (strategySection) strategySection.style.pointerEvents = 'auto';
          
          card.style.opacity = '1';
        }
        
        // Update status badge
        const statusBadge = card.querySelector('.status-badge');
        if (statusBadge) {
          if (!isOffered) {
            statusBadge.textContent = 'Not Offered';
            statusBadge.classList.remove('incomplete', 'complete');
            statusBadge.classList.add('not-offered');
          } else {
            // Check if subject is actually complete by calling updateProficiencyDisplay
            // which will calculate the proper status
            updateProficiencyDisplay(card);
          }
        }
        
        // Update proficiency display when toggled
        if (isOffered) {
          updateProficiencyDisplay(card);
        }
      }
      
      // Initialize on page load
      toggleCardFields();
      
      // down or right arrow
      offeredCheckbox.addEventListener('change', toggleCardFields);
      
      // Also update proficiency on input changes
      const proficiencyInputs = card.querySelectorAll('.proficiency-field input');
      proficiencyInputs.forEach(input => {
        input.addEventListener('input', () => updateProficiencyDisplay(card));
        input.addEventListener('blur', () => updateProficiencyDisplay(card));
      });
    });
  }
  
  // Initialize SLP toggle if on SLP tab
  if (currentTabKey === 'slp') {
    // Critical: Initialize offered toggle immediately (user might click right away)
    initializeSLPOfferedToggle();
    
    // Defer less critical initializations to improve perceived performance
    if (window.requestIdleCallback) {
      requestIdleCallback(() => {
        initializeSLPNestedAccordion();
        initializeSLPAnalysisTracking();
      });
    } else {
      // down or right arrow
      setTimeout(() => {
        initializeSLPNestedAccordion();
        initializeSLPAnalysisTracking();
      }, 100);
    }
  }

  // down or right arrow
  function initializeSLPNestedAccordion() {
    // down or right arrow
    const cards = document.querySelectorAll('.slp-subject-card');
    cards.forEach(card => {
      updateProficiencyDisplay(card);
    });
  }

  // down or right arrow
  window.toggleGrade = function(gradeId) {
    const container = document.getElementById('grade-' + gradeId);
    if (!container) {
      console.error('Container not found for gradeId:', gradeId);
      return;
    }
    const gradeAccordion = container.parentElement;
    const header = gradeAccordion.querySelector('.grade-header');
    const icon = header ? header.querySelector('.accordion-icon') : null;
    const shouldOpen = container.style.display === 'none' || container.style.display === '';

    container.style.display = shouldOpen ? 'block' : 'none';
    if (icon) {
      icon.textContent = shouldOpen ? String.fromCharCode(9660) : String.fromCharCode(9654); // down or right arrow
    }
    gradeAccordion.classList.toggle('open', shouldOpen);
  };

  window.toggleSubject = function(subjectId) {
    const content = document.getElementById('subject-' + subjectId);
    if (!content) {
      console.error('Subject content not found for ID:', subjectId);
      return;
    }
    const accordion = content.closest('.subject-accordion');
    const header = accordion ? accordion.querySelector('.subject-header') : null;
    const icon = header ? header.querySelector('.accordion-icon') : null;
    const shouldOpen = content.style.display === 'none' || content.style.display === '';

    content.style.display = shouldOpen ? 'block' : 'none';
    if (icon) {
      icon.textContent = shouldOpen ? String.fromCharCode(9660) : String.fromCharCode(9654); // down or right arrow
    }
    if (shouldOpen) {
      if (header) {
        header.classList.add('expanded');
      }

      // Update proficiency display when subject is expanded
      updateProficiencyDisplay(content);

      // down or right arrow
      const proficiencyInputs = content.querySelectorAll('input[id$="-enrolment"], input[id$="-dnme"], input[id$="-fs"], input[id$="-s"], input[id$="-vs"], input[id$="-o"]');
      proficiencyInputs.forEach(input => {
        input.addEventListener('input', () => {
          updateProficiencyDisplay(content);
        });
      });
    } else {
      if (header) {
        header.classList.remove('expanded');
      }
    }
  };

  // Update proficiency percentage display
  function updateProficiencyDisplay(subjectContent) {
    // Find the proficiency inputs within this subject content
    const enrolmentInput = subjectContent.querySelector('input[id$="-enrolment"]');
    const dnmeInput = subjectContent.querySelector('input[id$="-dnme"]');
    const fsInput = subjectContent.querySelector('input[id$="-fs"]');
    const sInput = subjectContent.querySelector('input[id$="-s"]');
    const vsInput = subjectContent.querySelector('input[id$="-vs"]');
    const oInput = subjectContent.querySelector('input[id$="-o"]');
    
    if (!enrolmentInput) return;
    
    // Get the form index from any input's ID
    const inputId = enrolmentInput.id; // e.g., "id_slp_rows-0-enrolment"
    const formIndex = inputId.match(/-(\d+)-/)?.[1];
    if (!formIndex) return;
    
    const enrolment = parseInt(enrolmentInput.value) || 0;
    const dnme = parseInt(dnmeInput?.value) || 0;
    const fs = parseInt(fsInput?.value) || 0;
    const s = parseInt(sInput?.value) || 0;
    const vs = parseInt(vsInput?.value) || 0;
    const o = parseInt(oInput?.value) || 0;
        
    // Calculate percentages
    const dnmePct = enrolment > 0 ? ((dnme / enrolment) * 100).toFixed(1) : 0;
    const fsPct = enrolment > 0 ? ((fs / enrolment) * 100).toFixed(1) : 0;
    const sPct = enrolment > 0 ? ((s / enrolment) * 100).toFixed(1) : 0;
    const vsPct = enrolment > 0 ? ((vs / enrolment) * 100).toFixed(1) : 0;
    const oPct = enrolment > 0 ? ((o / enrolment) * 100).toFixed(1) : 0;
    
    
    
    // Validate proficiency sum
    const proficiencySum = dnme + fs + s + vs + o;
    const proficiencySection = subjectContent.querySelector('[data-section="proficiency"]');
    const errorContainer = proficiencySection?.querySelector('.validation-errors');
    const errorMessages = proficiencySection?.querySelector('.error-messages');
    
    if (enrolment > 0 && proficiencySum !== enrolment) {
      // Show error
      if (errorContainer && errorMessages) {
        errorContainer.style.display = 'flex';
        errorMessages.innerHTML = `<div class="message message--error">Total proficiency counts (${proficiencySum}) must equal enrollment (${enrolment})</div>`;
      }
      // Mark inputs as error
      [dnmeInput, fsInput, sInput, vsInput, oInput].forEach(input => {
        if (input) input.classList.add('error');
      });
    } else {
      // Hide error
      if (errorContainer) {
        errorContainer.style.display = 'none';
      }
      // down or right arrow
      [dnmeInput, fsInput, sInput, vsInput, oInput].forEach(input => {
        if (input) input.classList.remove('error');
      });
    }
  }

  // Track completion of SLP subject sections
  function initializeSLPAnalysisTracking() {
    const cards = document.querySelectorAll('.slp-subject-card');
    cards.forEach(card => {
      const formIndex = card.dataset.formIndex;

      const enrolmentInput = card.querySelector('input[id$="-enrolment"]');
      const llcTextarea = card.querySelector('textarea[id$="-top_three_llc"]');
      const interventionTextarea = card.querySelector('textarea[id$="-intervention_plan"]');
      const strategyTextarea = card.querySelector('.strategy-textarea');

      const statusBadge = card.querySelector('.status-badge');
      const progressFill = card.querySelector(`[data-progress="${formIndex}"]`);
      const progressText = card.querySelector(`[data-progress-text="${formIndex}"]`);
      const offeredCheckbox = card.querySelector('input[id$="-is_offered"]');

      function updateProgress() {
        if (offeredCheckbox && !offeredCheckbox.checked) {
          if (statusBadge) {
            statusBadge.textContent = 'Not Offered';
            statusBadge.classList.remove('incomplete', 'complete');
            statusBadge.classList.add('not-offered');
          }
          if (progressFill) {
            progressFill.style.width = '0%';
          }
          if (progressText) {
            progressText.textContent = 'Not offered';
          }
          return;
        }

        let filledCount = 0;
        let totalFields = 3 + (strategyTextarea ? 1 : 0);

        if (enrolmentInput && enrolmentInput.value.trim().length > 0) {
          filledCount++;
        }
        if (llcTextarea && llcTextarea.value.trim().length > 0) {
          filledCount++;
        }
        if (interventionTextarea && interventionTextarea.value.trim().length > 0) {
          filledCount++;
        }
        if (strategyTextarea && strategyTextarea.value.trim().length > 0) {
          filledCount++;
        }

        const percentage = totalFields > 0 ? Math.round((filledCount / totalFields) * 100) : 0;

        if (progressFill) {
          progressFill.style.width = `${percentage}%`;
        }
        if (progressText) {
          progressText.textContent = `${percentage}% complete`;
        }

        if (statusBadge) {
          statusBadge.classList.remove('incomplete', 'complete', 'not-offered');
          if (percentage === 100) {
            statusBadge.textContent = 'Complete';
            statusBadge.classList.add('complete');
          } else {
            statusBadge.textContent = 'Incomplete';
            statusBadge.classList.add('incomplete');
          }
        }
      }

      [enrolmentInput, llcTextarea, interventionTextarea, strategyTextarea].forEach(field => {
        if (field) {
          field.addEventListener('input', updateProgress);
          field.addEventListener('blur', updateProgress);
        }
      });

      if (offeredCheckbox) {
        offeredCheckbox.addEventListener('change', updateProgress);
      }

      updateProgress();
    });
  }

  // Validate subject before saving
  function validateSubject(subjectContent) {
    const errors = [];
    
    // Check if subject is offered
    const offeredCheckbox = subjectContent.querySelector('input[id$="-is_offered"]');
    if (!offeredCheckbox || !offeredCheckbox.checked) {
      // Subject not offered - skip validation
      return { valid: true, errors: [] };
    }
    
    // Get form index
    const enrolmentInput = subjectContent.querySelector('input[id$="-enrolment"]');
    if (!enrolmentInput) return { valid: true, errors: [] };
    
    const inputId = enrolmentInput.id;
    const formIndex = inputId.match(/-(\d+)-/)?.[1];
    if (!formIndex) return { valid: true, errors: [] };
    
    // Get all inputs
    const enrolment = parseInt(enrolmentInput.value) || 0;
    const dnme = parseInt(subjectContent.querySelector('input[id$="-dnme"]')?.value) || 0;
    const fs = parseInt(subjectContent.querySelector('input[id$="-fs"]')?.value) || 0;
    const s = parseInt(subjectContent.querySelector('input[id$="-s"]')?.value) || 0;
    const vs = parseInt(subjectContent.querySelector('input[id$="-vs"]')?.value) || 0;
    const o = parseInt(subjectContent.querySelector('input[id$="-o"]')?.value) || 0;
    const llc = subjectContent.querySelector('textarea[id$="-top_three_llc"]')?.value.trim() || '';
    const intervention = subjectContent.querySelector('textarea[id$="-intervention_plan"]')?.value.trim() || '';
    
    // Validation 1: Proficiency must equal enrollment
    const proficiencySum = dnme + fs + s + vs + o;
    if (enrolment > 0 && proficiencySum !== enrolment) {
      errors.push({
        section: 'proficiency',
        message: `Total proficiency counts (${proficiencySum}) must equal enrollment (${enrolment})`
      });
    }
    
    // Validation 2: LLC should have content
    if (enrolment > 0 && llc.length < 10) {
      errors.push({
        section: 'llc',
        message: 'Top 3 LLC must be at least 10 characters'
      });
    }
    
    // Validation 3: Intervention should have content - REMOVED per user request
    // if (enrolment > 0 && intervention.length < 20) {
    //   errors.push({
    //     section: 'intervention',
    //     message: 'Intervention plan must be at least 20 characters'
    //   });
    // }
    
    return {
      valid: errors.length === 0,
      errors: errors
    };
  }

  // Display validation errors in sections
  function displayValidationErrors(subjectContent, errors) {
    // Clear all existing errors first
    subjectContent.querySelectorAll('.validation-errors').forEach(container => {
      container.style.display = 'none';
      const messages = container.querySelector('.error-messages');
      if (messages) messages.innerHTML = '';
    });
    
    // down or right arrow
    subjectContent.querySelectorAll('input.error, textarea.error').forEach(el => {
      el.classList.remove('error');
    });
    
    // Display new errors
    errors.forEach(error => {
      const section = subjectContent.querySelector(`[data-section="${error.section}"]`);
      if (section) {
        const errorContainer = section.querySelector('.validation-errors');
        const errorMessages = section.querySelector('.error-messages');
        
        if (errorContainer && errorMessages) {
          errorContainer.style.display = 'flex';
          errorMessages.innerHTML += `<div class="message message--error">${error.message}</div>`;
        }
        
        // down or right arrow
        if (error.section === 'proficiency') {
          ['dnme', 'fs', 's', 'vs', 'o'].forEach(field => {
            const input = section.querySelector(`input[id$="-${field}"]`);
            if (input) input.classList.add('error');
          });
        } else if (error.section === 'llc') {
          const textarea = section.querySelector('textarea[id$="-top_three_llc"]');
          if (textarea) textarea.classList.add('error');
        } else if (error.section === 'intervention') {
          const textarea = section.querySelector('textarea[id$="-intervention_plan"]');
          if (textarea) textarea.classList.add('error');
        }
      }
    });
  }

  // down or right arrow
  function scrollToFirstError(subjectContent) {
    const firstError = subjectContent.querySelector('.validation-errors[style*="flex"]');
    if (firstError) {
      firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }

  // Note: Save subject buttons work via native form submission (type="submit")
  // But we add validation before allowing submission
  document.addEventListener('click', function(e) {
    if (e.target.classList.contains('save-subject-btn')) {
      const subjectContent = e.target.closest('.subject-content');
      if (subjectContent) {
        // down or right arrow
        
        // Don't prevent default - let the form submit naturally
        // e.preventDefault(); // COMMENTED OUT
        
        // const validation = validateSubject(subjectContent);
        
        // if (!validation.valid) {
        //   e.preventDefault(); // Stop form submission
        //   displayValidationErrors(subjectContent, validation.errors);
        //   scrollToFirstError(subjectContent);
        //   
        //   // Shake the button
        //   e.target.classList.add('shake-error');
        //   setTimeout(() => e.target.classList.remove('shake-error'), 600);
        //   
        //   return false;
        // }
        
        // Valid - allow submission (remove alert, just show saving state)
        const originalText = e.target.textContent;
        e.target.textContent = 'Saving...';
        e.target.disabled = true;
        
        
        // Force form submission since something is blocking it
        const form = e.target.form || e.target.closest('form');
        if (form) {
            form.submit();
        } else {
            console.error('No form found for button!');
        }
        
        // Fallback: Reset button after 10 seconds in case something goes wrong
        setTimeout(() => {
          if (e.target.textContent === 'Saving...') {
            e.target.textContent = originalText;
            e.target.disabled = false;
            console.warn('Save button reset after timeout - check for server errors');
          }
        }, 10000);
        
        // Return false to prevent any other handlers from interfering
        return false;
      }
    }
  }); // REMOVED capture phase - let it bubble normally

  // Reset save buttons if page loaded with validation errors
  function resetSaveButtons() {
    const saveButtons = document.querySelectorAll('.save-subject-btn');
    saveButtons.forEach(button => {
      if (button.textContent === 'Saving...') {
        button.textContent = 'Save This Subject';
        button.disabled = false;
      }
    });
  }

  // Check if there are validation errors on page load and reset buttons
  const hasValidationErrors = document.querySelector('.validation-errors:not([style*="display: none"]), .errorlist, .alert-danger, .error');
  if (hasValidationErrors) {
    resetSaveButtons();
  }

  // Update proficiency displays when input values change
  const slpRows = document.querySelectorAll('.slp-row');
  slpRows.forEach(row => {
    const inputs = row.querySelectorAll('input[type="number"]');
    inputs.forEach(input => {
      input.addEventListener('input', () => {
        const subjectContent = row.closest('.subject-content');
        if (subjectContent) {
          updateProficiencyDisplay(subjectContent);
        }
      });
    });
  });

  // Handle "Subject Offered" checkbox toggle
  function toggleOfferedSections(checkbox) {
    const subjectContent = checkbox.closest('.subject-content');
    if (!subjectContent) return;
    
    const notOfferedMessage = subjectContent.querySelector('.not-offered-message');
    const proficiencyGrid = subjectContent.querySelector('.proficiency-grid');
    const cardSections = subjectContent.querySelectorAll('.card-section:not(.proficiency-section)');
    const saveButton = subjectContent.querySelector('.save-subject-btn');
    
    if (checkbox.checked) {
      // Subject is offered - show all sections
      if (notOfferedMessage) notOfferedMessage.style.display = 'none';
      if (proficiencyGrid) proficiencyGrid.style.display = '';
      cardSections.forEach(section => section.style.display = 'block');
      if (saveButton) saveButton.style.display = '';
    } else {
      // Subject not offered - hide sections and show message
      if (notOfferedMessage) notOfferedMessage.style.display = 'block';
      if (proficiencyGrid) proficiencyGrid.style.display = 'none';
      cardSections.forEach(section => section.style.display = 'none');
      if (saveButton) saveButton.style.display = 'none';
      
      // Clear any validation errors
      const validationErrors = subjectContent.querySelector('.validation-errors');
      if (validationErrors) validationErrors.style.display = 'none';
      
      // down or right arrow
      subjectContent.querySelectorAll('.error').forEach(el => el.classList.remove('error'));
    }
  }
  
  // Initialize offered checkbox listeners
  document.querySelectorAll('input[id$="-is_offered"]').forEach(checkbox => {
    // Set initial state
    toggleOfferedSections(checkbox);
    
    // down or right arrow
    checkbox.addEventListener('change', function() {
      toggleOfferedSections(this);
    });
  });
});

// ============================================
// READING ASSESSMENT MATRIX CALCULATIONS
// ============================================

/**
 * Calculate totals for reading assessment matrices
 * Updates row totals and grand totals dynamically
 */
function initReadingMatrixCalculations() {
  const matrices = document.querySelectorAll('.reading-matrix-table');
  
  matrices.forEach(matrix => {
    const inputs = matrix.querySelectorAll('input[type="number"]');
    
    // Add event listeners to all inputs
    inputs.forEach(input => {
      input.addEventListener('input', () => updateMatrixTotals(matrix));
    });
    
    // Calculate initial totals
    updateMatrixTotals(matrix);
  });
}

/**
 * Update all totals in a reading matrix table
 */
function updateMatrixTotals(matrix) {
  let grandTotal = 0;
  
  // Calculate row totals
  const rows = matrix.querySelectorAll('tbody tr:not(.total-row)');
  rows.forEach(row => {
    const inputs = row.querySelectorAll('input[type="number"]');
    let rowTotal = 0;
    
    inputs.forEach(input => {
      const value = parseInt(input.value) || 0;
      rowTotal += value;
    });
    
    // Update row total display
    const totalCell = row.querySelector('.total-value');
    if (totalCell) {
      totalCell.textContent = rowTotal;
    }
    
    grandTotal += rowTotal;
  });
  
  // Update grand total
  const grandTotalCell = matrix.querySelector('[data-grand-total]');
  if (grandTotalCell) {
    grandTotalCell.textContent = grandTotal;
  }
}

// Initialize reading matrix calculations when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initReadingMatrixCalculations);
} else {
  initReadingMatrixCalculations();
}

// ============================================================================
// PROJECTS & ACTIVITIES MANAGEMENT
// ============================================================================

/**
 * Initialize projects and activities handlers
 */
function initProjectsAndActivities() {
  // Attach delete confirmations for existing rows
  try { attachActivityDeleteHandlers(); } catch (e) { /* noop */ }
  try { attachProjectDeleteHandlers(); } catch (e) { /* noop */ }
  // Normalize any DELETE boxes already checked (e.g., after validation errors)
  normalizeExistingActivityDeletions();
}

/**
 * Attach delete handlers to project DELETE checkboxes
 */
function attachProjectDeleteHandlers() {
  const projectDeleteCheckboxes = document.querySelectorAll('input[name*="projects-"][name*="DELETE"]');
  projectDeleteCheckboxes.forEach(function(checkbox) {
    checkbox.removeEventListener('click', handleProjectDelete);
    checkbox.addEventListener('click', handleProjectDelete);
  });

  const projectDeleteButtons = document.querySelectorAll('.project-delete-btn');
  projectDeleteButtons.forEach(function(btn){
    btn.removeEventListener('click', handleProjectDeleteButtonClick);
    btn.addEventListener('click', handleProjectDeleteButtonClick);
  });
}

/**
 * Handle project deletion
 */
function handleProjectDelete(e) {
  const checkbox = e.target;
  const projectSection = checkbox.closest('.project-section');
  
  if (checkbox.checked) {
    if (confirm('Are you sure you want to remove this project? All activities will also be removed.')) {
      // If this is a new project (no ID), remove it completely
      const hiddenIdInput = projectSection.querySelector('input[name*="-id"]');
      if (!hiddenIdInput || !hiddenIdInput.value) {
        projectSection.remove();
      } else {
        // down or right arrow
        projectSection.classList.add('marked-for-deletion');
        projectSection.style.opacity = '0.5';
      }
    } else {
      checkbox.checked = false;
    }
  } else {
    // down or right arrow
    projectSection.classList.remove('marked-for-deletion');
    projectSection.style.opacity = '';
  }
}

/**
 * Add a new project row
 */
  window.addProjectRow = function addProjectRow() {
    const projectsContainer = document.querySelector('#submission-form .card');
    const totalFormsInput = document.querySelector('input[name="projects-TOTAL_FORMS"]');
    
    if (!totalFormsInput) {
      console.error('Projects TOTAL_FORMS input not found');
      return;
    }
    
    if (!projectsContainer) {
      console.error('Projects container not found');
      return;
    }
    
    const currentTotal = parseInt(totalFormsInput.value);
    const formIndex = currentTotal;
    
    // Create new project section
    const newProjectSection = document.createElement('div');
    newProjectSection.className = 'project-section';
    newProjectSection.setAttribute('data-project-index', currentTotal);
    newProjectSection.style.marginBottom = '2rem';
    
    newProjectSection.innerHTML = `
      <div class="project-header">
        <input type="hidden" name="projects-${formIndex}-id" id="id_projects-${formIndex}-id">
        <div class="project-header-grid">
          <div class="form-field">
            <label class="form-label">Project:</label>
            <input type="text" name="projects-${formIndex}-project_title" id="id_projects-${formIndex}-project_title" class="form-input" required>
          </div>
          <div class="form-field">
            <label class="form-label">Area of Concern:</label>
            <select name="projects-${formIndex}-area_of_concern" id="id_projects-${formIndex}-area_of_concern" class="form-input" required>
              <option value="">-- Select Area of Concern --</option>
              <option value="Access">Access</option>
              <option value="Quality">Quality</option>
              <option value="Equity">Equity</option>
              <option value="Enabling Mechanisms">Enabling Mechanisms</option>
            </select>
          </div>
          <div class="form-field">
            <label class="form-label">Conference Date:</label>
            <input type="date" name="projects-${formIndex}-conference_date" id="id_projects-${formIndex}-conference_date" class="form-input table-date">
          </div>
        </div>
        <div class="form-field" style="margin-top: var(--space-3); display: flex; justify-content: flex-end;">
          <input type="checkbox" name="projects-${formIndex}-DELETE" id="id_projects-${formIndex}-DELETE" style="display:none">
          <button type="button" class="btn btn--danger project-delete-btn">Delete Project</button>
        </div>
      </div>
      
      <!-- Save Project Notice -->
      <div class="save-project-notice" style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: var(--border-radius); padding: 1rem; margin: 1rem 0;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
          <div style="color: #f59e0b; font-size: 1.25rem;">!</div>
          <div>
            <p style="margin: 0; font-weight: 600; color: #92400e;">Save Project First</p>
            <p style="margin: 0.25rem 0 0 0; font-size: 0.875rem; color: #78350f;">
              Fill in the project details above, then click "Save Draft" to unlock the activities section.
            </p>
          </div>
        </div>
        <button type="button" 
                class="btn btn--primary save-project-btn" 
                style="margin-top: 0.75rem; font-size: 0.875rem;"
                onclick="saveProjectQuick(${formIndex})">
          Save This Project
        </button>
      </div>
    `;
    
    // Find the Add Project button container and insert before it
    const addButton = document.querySelector('.btn.btn--primary[onclick="addProjectRow()"]');
    if (addButton) {
      const addButtonContainer = addButton.parentElement;
      projectsContainer.insertBefore(newProjectSection, addButtonContainer);
    } else {
      // Fallback: append before the last child (button container)
      const children = projectsContainer.children;
      if (children.length > 1) {
        projectsContainer.insertBefore(newProjectSection, children[children.length - 1]);
      } else {
        projectsContainer.appendChild(newProjectSection);
      }
    }
    
    // Note: no activity details row here; details belong to activities, not project creation
    // Increment TOTAL_FORMS
    totalFormsInput.value = currentTotal + 1;

    // Reattach delete handlers for projects
    attachProjectDeleteHandlers();
    
    // Focus the first input in the new project
    const firstInput = newProjectSection.querySelector('input[type="text"]');
    if (firstInput) {
      setTimeout(() => firstInput.focus(), 100);
    }
    
  };

/**
 * Add a new activity row to a specific project
 */
  window.addActivityRow = function addActivityRow(projectId) {
    // down or right arrow
    const tbody = document.querySelector(`.activity-table-body[data-project-id="${projectId}"]`);
    
    // Check if projectId is valid (not null/undefined)
    if (!projectId || projectId === 'None' || projectId === 'null') {
      alert('Please save this project first before adding activities.');
      return;
    }
    
    if (!tbody) {
      console.error('Activity table body not found for project:', projectId);
      
      // Check if this is a new project that needs to be saved first
      const projectSections = document.querySelectorAll('.project-section');
      let foundUnsavedProject = false;
      
      projectSections.forEach(section => {
        const notice = section.querySelector('.save-project-notice');
        if (notice) {
          foundUnsavedProject = true;
        }
      });
      
      if (foundUnsavedProject) {
        alert('Please save the project first by clicking the "Save This Project" button, then you can add activities.');
      } else {
        alert('Cannot add activities to this project. Please refresh the page and try again.');
      }
      return;
    }
    
    let firstRow = tbody.querySelector('.activity-row');
    
    if (!firstRow) {
      console.error('No existing activity rows found for project:', projectId);
      
      // First, let's create and add the TOTAL_FORMS input if it doesn't exist
      let prefix = `activities_${projectId}`;
      let totalFormsInput = document.querySelector(`input[name="${prefix}-TOTAL_FORMS"]`);
      
      if (!totalFormsInput) {
        totalFormsInput = document.createElement('input');
        totalFormsInput.type = 'hidden';
        totalFormsInput.name = `${prefix}-TOTAL_FORMS`;
        totalFormsInput.value = '0';
        
        // down or right arrow
        const form = tbody.closest('form');
        if (form) {
          form.appendChild(totalFormsInput);
        }
      }
      
      // Create the initial management form inputs if they don't exist
      let initialFormsInput = document.querySelector(`input[name="${prefix}-INITIAL_FORMS"]`);
      if (!initialFormsInput) {
        initialFormsInput = document.createElement('input');
        initialFormsInput.type = 'hidden';
        initialFormsInput.name = `${prefix}-INITIAL_FORMS`;
        initialFormsInput.value = '0';
        const form = tbody.closest('form');
        if (form) form.appendChild(initialFormsInput);
      }
      
      let minFormsInput = document.querySelector(`input[name="${prefix}-MIN_NUM_FORMS"]`);
      if (!minFormsInput) {
        minFormsInput = document.createElement('input');
        minFormsInput.type = 'hidden';
        minFormsInput.name = `${prefix}-MIN_NUM_FORMS`;
        minFormsInput.value = '0';
        const form = tbody.closest('form');
        if (form) form.appendChild(minFormsInput);
      }
      
      let maxFormsInput = document.querySelector(`input[name="${prefix}-MAX_NUM_FORMS"]`);
      if (!maxFormsInput) {
        maxFormsInput = document.createElement('input');
        maxFormsInput.type = 'hidden';
        maxFormsInput.name = `${prefix}-MAX_NUM_FORMS`;
        maxFormsInput.value = '1000';
        const form = tbody.closest('form');
        if (form) form.appendChild(maxFormsInput);
      }
      
      
      // down or right arrow
      // Let's create a minimal template row that matches our expected structure
      const templateRow = document.createElement('tr');
      templateRow.className = 'activity-row';
      templateRow.innerHTML = `
        <input type="hidden" name="activities_${projectId}-0-id" id="id_activities_${projectId}-0-id">
        <td><textarea name="activities_${projectId}-0-activity" class="table-input table-textarea" placeholder="Enter activity description..." rows="2"></textarea></td>
        <td><input type="number" name="activities_${projectId}-0-output_target" class="table-input" min="0" step="1"></td>
        <td><input type="number" name="activities_${projectId}-0-output_actual" class="table-input" min="0" step="1"></td>
        <td><input type="date" name="activities_${projectId}-0-timeframe_target" class="table-input table-date"></td>
        <td><input type="date" name="activities_${projectId}-0-timeframe_actual" class="table-input table-date"></td>
        <td><input type="number" name="activities_${projectId}-0-budget_target" class="table-input" min="0" step="0.01" placeholder="0.00"></td>
        <td><input type="number" name="activities_${projectId}-0-budget_actual" class="table-input" min="0" step="0.01" placeholder="0.00"></td>
        <td><textarea name="activities_${projectId}-0-interpretation" class="table-input table-textarea" placeholder="Enter interpretation..." rows="2"></textarea></td>
        <td><textarea name="activities_${projectId}-0-issues_unaddressed" class="table-input table-textarea" placeholder="Enter issues..." rows="2"></textarea></td>
        <td><textarea name="activities_${projectId}-0-facilitating_factors" class="table-input table-textarea" placeholder="Enter factors..." rows="2"></textarea></td>
        <td><textarea name="activities_${projectId}-0-agreements" class="table-input table-textarea" placeholder="Enter agreements..." rows="2"></textarea></td>
        <td><label class="delete-btn tooltip" data-tooltip="Remove this activity" aria-label="Remove this activity"><input type="checkbox" name="activities_${projectId}-0-DELETE" aria-label="Remove this activity"><span aria-hidden="true">&times;</span><span class="delete-text">Delete</span></label></td>
      `;
      
      // Add template row to tbody and use it as firstRow
      tbody.appendChild(templateRow);
      firstRow = templateRow;
      
      // Update the TOTAL_FORMS to reflect the new row
      totalFormsInput.value = '1';
      
      
      // Since we just created the first row, we don't need to create another one
      // Focus the first input and return early
      const firstInput = templateRow.querySelector('textarea, input:not([type="hidden"]):not([type="checkbox"])');
      if (firstInput) {
        firstInput.focus();
      }
      
      // Reattach delete handlers
      attachActivityDeleteHandlers();
      
      return;
    }
    
    // The formset prefix should be activities_{projectId} based on the Django view
    let prefix = `activities_${projectId}`;
    let totalFormsInput = document.querySelector(`input[name="${prefix}-TOTAL_FORMS"]`);
    
    
    // If not found, try other common patterns
    if (!totalFormsInput) {
      const possiblePrefixes = [
        `activities-${projectId}`,
        `activity_formset_${projectId}`,
        `form`,
        'activity'
      ];
      
      for (const testPrefix of possiblePrefixes) {
        const testInput = document.querySelector(`input[name="${testPrefix}-TOTAL_FORMS"]`);
        if (testInput) {
          totalFormsInput = testInput;
          prefix = testPrefix;
          break;
        }
      }
    } else {
    }
    
    // Also try to find it by looking at existing form names in the first row
    if (!totalFormsInput) {
      const existingInput = firstRow.querySelector('input[name*="-"]');
      if (existingInput && existingInput.name) {
        // Extract prefix from existing input name (e.g., "form-0-activity" -> "form")
        const match = existingInput.name.match(/^(.+)-\d+-/);
        if (match) {
          prefix = match[1];
          totalFormsInput = document.querySelector(`input[name="${prefix}-TOTAL_FORMS"]`);
        }
      }
    }
    
    if (!totalFormsInput) {
      console.warn('TOTAL_FORMS input not found. Creating one...');
      // down or right arrow
      const allTotalForms = document.querySelectorAll('input[name*="TOTAL_FORMS"]');
      
      // Create the missing TOTAL_FORMS input
      totalFormsInput = document.createElement('input');
      totalFormsInput.type = 'hidden';
      totalFormsInput.name = `${prefix}-TOTAL_FORMS`;
      totalFormsInput.value = tbody.querySelectorAll('.activity-row').length.toString();
      
      // Add it to the form
      const form = tbody.closest('form');
      if (form) {
        form.appendChild(totalFormsInput);
      } else {
        console.error('Could not find form to add TOTAL_FORMS input');
        return;
      }
    }
    
    
    const currentTotal = parseInt(totalFormsInput.value);
    
    // Create a new row with the correct structure
    const newRow = document.createElement('tr');
    newRow.className = 'activity-row';
    newRow.setAttribute('data-activity-index', currentTotal);
    
    // down or right arrow
    // The activities will be processed differently on the backend
    const isTemporaryProject = projectId.toString().startsWith('new_');
    let fieldPrefix = prefix;
    
    if (isTemporaryProject) {
      // down or right arrow
      fieldPrefix = `temp_activities_${currentTotal}`;
    }
    
    // Create the row HTML with proper form inputs
    newRow.innerHTML = `
      <input type="hidden" name="${prefix}-${currentTotal}-id" id="id_${prefix}-${currentTotal}-id">
      <input type="hidden" name="${prefix}-${currentTotal}-project_temp_id" value="${projectId}" class="temp-project-reference">
      <td>
        <div class="text-cell" data-field="activity">
          <textarea name="${prefix}-${currentTotal}-activity" 
                    id="id_${prefix}-${currentTotal}-activity" 
                    class="table-input table-textarea" 
                    placeholder="Enter activity description..."
                    rows="2"></textarea>
        </div>
      </td>
      <td>
        <input type="number" 
               name="${prefix}-${currentTotal}-output_target" 
               id="id_${prefix}-${currentTotal}-output_target" 
               class="table-input" 
               min="0" 
               step="1">
      </td>
      <td>
        <input type="number" 
               name="${prefix}-${currentTotal}-output_actual" 
               id="id_${prefix}-${currentTotal}-output_actual" 
               class="table-input" 
               min="0" 
               step="1">
      </td>
      <td>
        <input type="date" 
               name="${prefix}-${currentTotal}-timeframe_target" 
               id="id_${prefix}-${currentTotal}-timeframe_target" 
               class="table-input table-date">
      </td>
      <td>
        <input type="date" 
               name="${prefix}-${currentTotal}-timeframe_actual" 
               id="id_${prefix}-${currentTotal}-timeframe_actual" 
               class="table-input table-date">
      </td>
      <td>
        <input type="number" 
               name="${prefix}-${currentTotal}-budget_target" 
               id="id_${prefix}-${currentTotal}-budget_target" 
               class="table-input" 
               min="0" 
               step="0.01" 
               placeholder="0.00">
      </td>
      <td>
        <input type="number" 
               name="${prefix}-${currentTotal}-budget_actual" 
               id="id_${prefix}-${currentTotal}-budget_actual" 
               class="table-input" 
               min="0" 
               step="0.01" 
               placeholder="0.00">
      </td>
      <td>\n        <label class="sr-only">Interpretation</label><span class="muted">&mdash;</span>\n      </td>
      <td>\n        <label class="sr-only">Issues / Problems</label><span class="muted">&mdash;</span>\n      </td>
      <td>\n        <label class="sr-only">Facilitating Factors</label><span class="muted">&mdash;</span>\n      </td>
      <td>\n        <label class="sr-only">Agreements</label><span class="muted">&mdash;</span>\n      </td>
      <td>
        <label class="delete-btn tooltip" data-tooltip="Remove this activity" aria-label="Remove this activity">
          <input type="checkbox" 
                 name="${prefix}-${currentTotal}-DELETE" 
                 id="id_${prefix}-${currentTotal}-DELETE"
                 aria-label="Remove this activity">
          <span aria-hidden="true">&times;</span>
          <span class="delete-text">Delete</span>
        </label>
      </td>
    `;

    // Remove any narrative placeholders accidentally included in the base row
    Array.from(newRow.querySelectorAll('label.sr-only')).forEach(function(lbl){
      const td = lbl.closest('td');
      if (td && td.parentElement === newRow) { td.remove(); }
    });

    // Ensure Action cell uses a real button + hidden DELETE field
    const actionCell = newRow.querySelector('td:last-child');
    if (actionCell) {
      const deleteName = `${prefix}-${currentTotal}-DELETE`;
      actionCell.innerHTML = `
        <input type="checkbox" name="${deleteName}" id="id_${deleteName}" style="display:none" aria-label="Remove this activity">
        <button type="button" class="btn btn--danger btn--small activity-delete-btn" aria-label="Remove this activity">Delete</button>
      `;
    }

    // Build details row that holds narrative inputs
    const detailsRow = document.createElement('tr');
    detailsRow.className = 'activity-details';
    detailsRow.setAttribute('data-project-id', projectId);
    detailsRow.setAttribute('data-activity-index', currentTotal);
    const number = tbody.querySelectorAll('.activity-row').length + 1;
    detailsRow.innerHTML = `
      <td colspan="8">
        <div class="activity-number"><span class="section-number">${number}</span><span class="label">Activity</span></div>
        <div class="details-heading">Details</div>
        <div class="activity-details-grid">
          <div class="details-field"><label class="form-label">Interpretation</label><textarea name="${prefix}-${currentTotal}-interpretation" id="id_${prefix}-${currentTotal}-interpretation" class="table-input table-textarea" rows="4" placeholder="Enter interpretation..."></textarea></div>
          <div class="details-field"><label class="form-label">Issues / Problems</label><textarea name="${prefix}-${currentTotal}-issues_unaddressed" id="id_${prefix}-${currentTotal}-issues_unaddressed" class="table-input table-textarea" rows="4" placeholder="Enter issues..."></textarea></div>
          <div class="details-field"><label class="form-label">Facilitating Factors</label><textarea name="${prefix}-${currentTotal}-facilitating_factors" id="id_${prefix}-${currentTotal}-facilitating_factors" class="table-input table-textarea" rows="4" placeholder="Enter facilitating factors..."></textarea></div>
          <div class="details-field"><label class="form-label">Agreements</label><textarea name="${prefix}-${currentTotal}-agreements" id="id_${prefix}-${currentTotal}-agreements" class="table-input table-textarea" rows="4" placeholder="Enter agreements..."></textarea></div>
        </div>
      </td>`;
    
    // Add a compact subheader before this activity if there are existing rows
    const hasExisting = tbody.querySelectorAll('.activity-row').length > 0;
    if (hasExisting) {
      const subHeader = document.createElement('tr');
      subHeader.className = 'activity-subheader';
      subHeader.innerHTML = `
        <td class="col-activity">Activities</td>
        <td class="col-output">Output<br><small class="text-muted">Target</small></td>
        <td class="col-output">Output<br><small class="text-muted">Actual</small></td>
        <td class="col-timeframe">Timeframe<br><small class="text-muted">Target</small></td>
        <td class="col-timeframe">Timeframe<br><small class="text-muted">Actual</small></td>
        <td class="col-budget">Budget<br><small class="text-muted">Target</small></td>
        <td class="col-budget">Budget<br><small class="text-muted">Actual</small></td>
        <td class="col-action">Action</td>`;
      tbody.appendChild(subHeader);
    }

    // Add the new rows (base + details)
    tbody.appendChild(newRow);
    if (newRow.nextSibling) { tbody.insertBefore(detailsRow, newRow.nextSibling); } else { tbody.appendChild(detailsRow); }
    
    // Increment TOTAL_FORMS
    totalFormsInput.value = currentTotal + 1;
    
    // Reattach delete handlers (checkbox + button)
    attachActivityDeleteHandlers();
    
    // Focus the first input in the new row
    const firstInput = newRow.querySelector('textarea, input:not([type="hidden"])');
    if (firstInput) {
      setTimeout(() => firstInput.focus(), 100);
    }

    // No toggles — details are always below
    
  };

/**
 * Attach delete handlers to activity rows
 */
function attachActivityDeleteHandlers() {
  const deleteCheckboxes = document.querySelectorAll('.activity-row input[name*="DELETE"]');
  deleteCheckboxes.forEach(function(checkbox) {
    checkbox.removeEventListener('click', handleActivityDelete);
    checkbox.addEventListener('click', handleActivityDelete);
  });
  const deleteButtons = document.querySelectorAll('.activity-row .activity-delete-btn');
  deleteButtons.forEach(function(btn){
    btn.removeEventListener('click', handleActivityDeleteButtonClick);
    btn.addEventListener('click', handleActivityDeleteButtonClick);
  });
}
// Clean renumber function (replaces corrupted merge block)
function renumberActivities(tbody) {
  if (!tbody) return;
  const detailRows = tbody.querySelectorAll('.activity-details');
  let n = 1;
  detailRows.forEach(dr => {
    const badge = dr.querySelector('.activity-number .section-number');
    if (badge) { badge.textContent = String(n); }
    n += 1;
  });
}
function getActivityDeleteBin(form) {
  let bin = form.querySelector('#activity-delete-bin');
  if (!bin) {
    bin = document.createElement('div');
    bin.id = 'activity-delete-bin';
    bin.style.display = 'none';
    form.appendChild(bin);
  }
  return bin;
}

/** Handle activity deletion */
function handleActivityDelete(e) {
  const checkbox = e.target;
  const row = checkbox.closest('tr');
  if (!row) { return; }
  const tbody = row.parentElement;
  if (!tbody) { return; }
  const form = tbody.closest('form');
  if (!form) { return; }

  const restoreState = activityDeleteState.get(row);

  const restoreRow = () => {
    const state = activityDeleteState.get(row);
    if (!state) { return; }
    const { placeholder, bin, detailsRow, subHeader } = state;
    checkbox.checked = false;

    if (placeholder.parentNode) {
      if (subHeader) { placeholder.parentNode.insertBefore(subHeader, placeholder); }
      placeholder.parentNode.insertBefore(row, placeholder);
      if (detailsRow) {
        if (row.nextSibling) {
          placeholder.parentNode.insertBefore(detailsRow, row.nextSibling);
        } else {
          placeholder.parentNode.appendChild(detailsRow);
        }
      }
      placeholder.remove();
    }
    if (bin.contains(row)) { bin.removeChild(row); }
    if (detailsRow && bin.contains(detailsRow)) { bin.removeChild(detailsRow); }
    if (subHeader && bin.contains(subHeader)) { bin.removeChild(subHeader); }

    row.classList.remove('marked-for-deletion');
    row.style.display = '';
    activityDeleteState.delete(row);
    try { renumberActivities(tbody); } catch (e) { /* noop */ }
  };

  if (checkbox.checked) {
    if (confirm('Are you sure you want to remove this activity?')) {
      const hiddenIdInput = row.querySelector('input[name*="-id"]');
      const maybeDetails = row.nextElementSibling && row.nextElementSibling.classList.contains('activity-details') ? row.nextElementSibling : null;
      const maybeSubheader = row.previousElementSibling && row.previousElementSibling.classList.contains('activity-subheader') ? row.previousElementSibling : null;
      if (!hiddenIdInput || !hiddenIdInput.value) {
        if (maybeDetails) maybeDetails.remove();
        if (maybeSubheader) maybeSubheader.remove();
        row.remove();
        try { renumberActivities(tbody); } catch (e) { /* noop */ }
      } else {
        const bin = getActivityDeleteBin(form);
        const nextSibling = row.nextSibling;
        const placeholder = document.createElement('tr');
        placeholder.className = 'activity-row-placeholder';
        const colCount = row.querySelectorAll('td').length || 12;
        placeholder.innerHTML = `<td colspan="${colCount}" style="padding: 0.75rem; background: #fef2f2; color: #b91c1c; font-size: 0.9rem; border: 1px solid #fecaca;"><span style="margin-right: 1rem;">Activity marked for removal.</span><button type="button" class="undo-remove" style="background: none; border: none; color: #2563eb; cursor: pointer; text-decoration: underline; padding: 0;">Undo</button></td>`;
        if (nextSibling) { tbody.insertBefore(placeholder, nextSibling); } else { tbody.appendChild(placeholder); }
        bin.appendChild(row);
        if (maybeDetails) bin.appendChild(maybeDetails);
        if (maybeSubheader) bin.appendChild(maybeSubheader);
        row.classList.add('marked-for-deletion');
        row.style.display = '';
        activityDeleteState.set(row, { placeholder, bin, detailsRow: maybeDetails, subHeader: maybeSubheader, nextSibling });
        const undoButton = placeholder.querySelector('.undo-remove');
        if (undoButton) undoButton.addEventListener('click', restoreRow, { once: true });
        try { renumberActivities(tbody); } catch (e) { /* noop */ }
      }
    } else {
      checkbox.checked = false;
    }
  } else {
    if (restoreState) { restoreRow(); }
  }
}

/** Button wrapper for DELETE logic */
function handleActivityDeleteButtonClick(e) {
  const row = e.target.closest('tr');
  if (!row) return;
  const checkbox = row.querySelector('input[name*="-DELETE"]');
  if (!checkbox) return;
  checkbox.checked = true;
  handleActivityDelete({ target: checkbox });
}

// Initialize projects and activities when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initProjectsAndActivities);
} else {
  initProjectsAndActivities();
}function initEnhancedProjectsTable() {
  initTextCellInteractions();
  initProjectsToolbar();
  autosizeAllProjectTextareas();
  initTableInputValidation();
  try { initResponsiveTableBehavior(); } catch (e) { /* noop */ }
}

/** Toolbar handlers for Projects table */
function initProjectsToolbar() {
  document.querySelectorAll('.projects-table-container').forEach(container => {
    const table = container.querySelector('.projects-table');
    const toolbar = container.querySelector('.projects-toolbar');
    if (!table || !toolbar) return;
    toolbar.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-projects-action]');
      if (!btn) return;
      const action = btn.getAttribute('data-projects-action');
      if (action === 'expand') {
        table.classList.add('expanded');
        autosizeAllProjectTextareas();
      } else if (action === 'collapse') {
        table.classList.remove('expanded');
      } else if (action === 'wrap') {
        table.classList.toggle('wrap');
        autosizeAllProjectTextareas();
      }
    });
  });
}

function autosizeAllProjectTextareas() {
  document.querySelectorAll('.projects-table textarea').forEach(ta => autosizeTextarea(ta));
}

function autosizeTextarea(ta) {
  if (!ta) return;
  ta.style.height = 'auto';
  ta.style.height = (ta.scrollHeight + 2) + 'px';
}

// Autosize on input within project tables
document.addEventListener('input', function(e){
  if (e.target && e.target.closest && e.target.closest('.projects-table') && e.target.tagName === 'TEXTAREA') {
    autosizeTextarea(e.target);
  }
});

/** Handle text cell expand/collapse interactions */
function initTextCellInteractions() {
  document.addEventListener('click', function(e) {
    const textTruncated = e.target.closest('.text-truncated');
    if (textTruncated) {
      const textCell = textTruncated.closest('.text-cell');
      if (textCell) {
        textCell.classList.toggle('expanded');
        if (textCell.classList.contains('expanded')) {
          const textarea = textCell.querySelector('textarea, input[type="text"]');
          if (textarea) {
            setTimeout(() => textarea.focus(), 100);
          }
        }
      }
    }
  });

  // Close expanded cells when clicking outside
  document.addEventListener('click', function(e) {
    const expandedCells = document.querySelectorAll('.text-cell.expanded');
    expandedCells.forEach(cell => {
      if (!cell.contains(e.target)) {
        cell.classList.remove('expanded');
      }
    });
  });

  // Close expanded cells on Escape key
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      document.querySelectorAll('.text-cell.expanded').forEach(cell => {
        cell.classList.remove('expanded');
      });
    }
  });
}

/** Enhanced form input validation */
function initTableInputValidation() {
  document.addEventListener('input', function(e) {
    if (e.target.name && (e.target.name.includes('budget') || e.target.name.includes('output'))) {
      const value = e.target.value.replace(/[^\d.]/g, '');
      if (e.target.value !== value) { e.target.value = value; }
      if (value && !isNaN(parseFloat(value))) {
        e.target.classList.remove('invalid');
        e.target.classList.add('valid');
      } else if (value) {
        e.target.classList.add('invalid');
        e.target.classList.remove('valid');
      } else {
        e.target.classList.remove('invalid', 'valid');
      }
    }
  });

  // Validate date inputs
  document.addEventListener('change', function(e) {
    if (e.target.type === 'date' && e.target.classList.contains('table-date')) {
      const selectedDate = new Date(e.target.value);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      selectedDate.setHours(0, 0, 0, 0);
      if (e.target.name.includes('target')) {
        if (selectedDate >= today) {
          e.target.classList.add('date-future');
          e.target.classList.remove('date-past');
        } else {
          e.target.classList.add('date-past');
          e.target.classList.remove('date-future');
        }
      } else if (e.target.name.includes('actual')) {
        if (selectedDate <= today) {
          e.target.classList.add('date-past');
          e.target.classList.remove('date-future');
        } else {
          e.target.classList.add('date-future');
          e.target.classList.remove('date-past');
        }
      }
    }
  });
}

/** Enhanced responsive table behavior (minimal safe impl) */
function initResponsiveTableBehavior() {
  // No-op placeholder to avoid breaking calls; implement as needed
}function toggleGrade(slug) {
  try {
    const container = document.getElementById(`grade-${slug}`);
    if (!container) return;
    const isHidden = container.style.display === 'none' || getComputedStyle(container).display === 'none';
    container.style.display = isHidden ? '' : 'none';
    const header = container.previousElementSibling;
    if (header && header.querySelector && header.classList.contains('grade-header')) {
      const icon = header.querySelector('.accordion-icon');
      if (icon) { icon.style.transform = isHidden ? 'rotate(90deg)' : 'rotate(0deg)'; }
    }
  } catch (e) { /* noop */ }
}

function toggleSubject(composite) {
  try {
    const panel = document.getElementById(`subject-${composite}`);
    if (!panel) return;
    const isHidden = panel.style.display === 'none' || getComputedStyle(panel).display === 'none';
    panel.style.display = isHidden ? '' : 'none';
    const header = panel.previousElementSibling;
    if (header && header.querySelector) {
      const icon = header.querySelector('.accordion-icon');
      if (icon) { icon.style.transform = isHidden ? 'rotate(90deg)' : 'rotate(0deg)'; }
    }
  } catch (e) { /* noop */ }
}

// ============================================
// CROSS-TAB ENROLLMENT VALIDATION
// ============================================

// Get SLP enrollment data as the source of truth
function getSLPEnrollmentData() {
  const slpData = {};
  
  // down or right arrow
  document.querySelectorAll('input[id*="slp_rows"][id$="-enrolment"]').forEach(input => {
    const value = parseInt(input.value) || 0;
    if (value > 0) {
      // Extract grade from the input ID pattern: id_slp_rows-0-grade_7-filipino-enrolment
      const match = input.id.match(/slp_rows-\d+-(grade_\d+|kinder)-[^-]+-enrolment/);
      if (match) {
        let gradePart = match[1]; // down or right arrow
        let gradeName;
        
        if (gradePart === 'kinder') {
          gradeName = 'Kinder';
        } else {
          // Convert "grade_7" to "Grade 7"
          gradeName = gradePart.replace('grade_', 'Grade ');
        }
        
        // down or right arrow
        if (!slpData[gradeName]) {
          slpData[gradeName] = value;
        }
      }
    }
  });
  
  return slpData;
}

// Validate RMA tab proficiency bands consistency
function validateRMAEnrollment() {
  const errors = [];
  
  // Check each RMA row - only validate proficiency bands sum
  document.querySelectorAll('input[id*="rma_rows"][id$="-enrolment"]').forEach(enrollmentInput => {
    const row = enrollmentInput.closest('tr');
    if (!row) {
      return;
    }
    const gradeCell = row.querySelector('td:first-child');
    
    if (enrollmentInput && gradeCell) {
      const rmaEnrollment = parseInt(enrollmentInput.value) || 0;
      const grade = gradeCell.textContent.trim();
      
      // Check proficiency bands sum if enrollment > 0
      if (rmaEnrollment > 0) {
        const proficiencyInputs = row.querySelectorAll('input[id$="-emerging_not_proficient"], input[id$="-emerging_low_proficient"], input[id$="-developing_nearly_proficient"], input[id$="-transitioning_proficient"], input[id$="-at_grade_level"]');
        const proficiencySum = Array.from(proficiencyInputs).reduce((sum, input) => sum + (parseInt(input.value) || 0), 0);
        
        if (proficiencySum !== rmaEnrollment) {
          errors.push({
            element: row,
            message: `${grade} proficiency bands total (${proficiencySum}) must equal enrollment (${rmaEnrollment})`,
            type: 'proficiency_sum_mismatch'
          });
        }
      }
    }
  });
  
  return errors;
}

// Validate Reading assessments total against SLP enrollment (Reading has no enrollment inputs)
function validateReadingEnrollment() {
  const slpData = getSLPEnrollmentData();
  const errors = [];
  
  // Only validate if we have SLP data to compare against
  if (Object.keys(slpData).length === 0) {
    return errors;
  }
  
  
  // down or right arrow
  const gradeMap = {
    '1': 'Grade 1', '2': 'Grade 2', '3': 'Grade 3', '4': 'Grade 4', '5': 'Grade 5',
    '6': 'Grade 6', '7': 'Grade 7', '8': 'Grade 8', '9': 'Grade 9', '10': 'Grade 10'
  };
  
  // Validate CRLA assessments (Grades 1-3) - sum across all proficiency levels
  const crlaGradeTotals = {}; 
  
  document.querySelectorAll('input[id*="reading_crla_new"]').forEach(input => {
    const match = input.id.match(/_(mt|fil|eng)_grade_(\d+)/);
    if (match) {
      const gradeNum = match[2];
      const gradeName = gradeMap[gradeNum];
      const value = parseInt(input.value) || 0;
      
      if (!crlaGradeTotals[gradeName]) {
        crlaGradeTotals[gradeName] = 0;
      }
      crlaGradeTotals[gradeName] += value;
    }
  });
  
  const crlaSection = (() => {
    const input = document.querySelector('input[id*="reading_crla_new"]');
    return input ? input.closest('.section-card') : null;
  })();

  // Check CRLA totals against SLP enrollment
  Object.keys(crlaGradeTotals).forEach(grade => {
    const readingTotal = crlaGradeTotals[grade];
    const slpEnrollment = slpData[grade] || 0;
    
    if (readingTotal > 0 && slpEnrollment > 0 && readingTotal !== slpEnrollment) {
      errors.push({
        element: crlaSection,
        message: `${grade} CRLA total (${readingTotal}) must match SLP enrollment (${slpEnrollment})`,
        type: 'crla_enrollment_mismatch'
      });
    }
  });
  
  // Validate PHILIRI assessments (Grades 4-10) - sum across all proficiency levels
  const philiriGradeTotals = {};
  
  document.querySelectorAll('input[id*="reading_philiri_new"]').forEach(input => {
    const match = input.id.match(/_(eng|fil)_grade_(\d+)/);
    if (match) {
      const gradeNum = match[2];
      const gradeName = gradeMap[gradeNum];
      const value = parseInt(input.value) || 0;
      
      if (!philiriGradeTotals[gradeName]) {
        philiriGradeTotals[gradeName] = 0;
      }
      philiriGradeTotals[gradeName] += value;
    }
  });
  
  const philiriSection = (() => {
    const input = document.querySelector('input[id*="reading_philiri_new"]');
    return input ? input.closest('.section-card') : null;
  })();

  // Check PHILIRI totals against SLP enrollment
  Object.keys(philiriGradeTotals).forEach(grade => {
    const readingTotal = philiriGradeTotals[grade];
    const slpEnrollment = slpData[grade] || 0;
    
    if (readingTotal > 0 && slpEnrollment > 0 && readingTotal !== slpEnrollment) {
      errors.push({
        element: philiriSection,
        message: `${grade} PHILIRI total (${readingTotal}) must match SLP enrollment (${slpEnrollment})`,
        type: 'philiri_enrollment_mismatch'
      });
    }
  });
  
  return errors;
}

// Display validation errors uniformly
function displayCrossTabValidationErrors(tabSelector, errors) {
  // Clear existing cross-tab validation errors only
  document.querySelectorAll('.cross-tab-validation-error').forEach(el => el.remove());
  
  errors.forEach(error => {
    // down or right arrow
    const errorEl = document.createElement('div');
    errorEl.className = 'cross-tab-validation-error';
    errorEl.style.cssText = `
      background: #fef2f2;
      border: 1px solid #fecaca;
      color: #dc2626;
      padding: 0.75rem;
      border-radius: 6px;
      margin: 0.5rem 0;
      font-size: 0.875rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      width: 100%;
      box-sizing: border-box;
    `;
    errorEl.innerHTML = `<span style="color: #dc2626;">!</span> ${error.message}`;
    
    // down or right arrow
    if (error.element) {
      // down or right arrow
      if (error.element.tagName === 'TR') {
        const errorRow = document.createElement('tr');
        errorRow.className = 'cross-tab-validation-error';
        const colspan = error.element.querySelectorAll('td').length;
        errorRow.innerHTML = `<td colspan="${colspan}" style="padding: 0; border: none;"></td>`;
        errorRow.querySelector('td').appendChild(errorEl);
        // Place error ABOVE the concerned row for better visibility
        error.element.insertAdjacentElement('beforebegin', errorRow);
      } else {
        // down or right arrow
        // Place error above the element
        error.element.insertAdjacentElement('beforebegin', errorEl);
      }
    }
  });
}

// down or right arrow
function validateCurrentTab() {
  const currentTab = new URLSearchParams(window.location.search).get('tab') || 'projects';
  
  if (currentTab === 'rma') {
    const rmaErrors = validateRMAEnrollment();
    displayCrossTabValidationErrors('[data-tab="rma"]', rmaErrors);
    return rmaErrors.length === 0;
  } else if (currentTab === 'reading') {
    const readingErrors = validateReadingEnrollment();
    displayCrossTabValidationErrors('[data-tab="reading"]', readingErrors);
    return readingErrors.length === 0;
  }
  
  return true;
}

// down or right arrow
document.addEventListener('DOMContentLoaded', function() {
  
  // Add validation on RMA input changes
  document.querySelectorAll('input[id*="rma_rows"]').forEach(input => {
    input.addEventListener('blur', () => {
      setTimeout(() => { // Small delay to ensure value is updated
        if (new URLSearchParams(window.location.search).get('tab') === 'rma') {
          // Clear existing errors first
          document.querySelectorAll('.cross-tab-validation-error').forEach(el => el.remove());
          validateCurrentTab();
        }
      }, 100);
    });
    
    input.addEventListener('input', () => {
      // Only validate and clear errors if needed, don't just clear all errors
      setTimeout(() => {
        if (new URLSearchParams(window.location.search).get('tab') === 'rma') {
          // down or right arrow
          const currentErrors = validateRMAEnrollment();
          document.querySelectorAll('.cross-tab-validation-error').forEach(el => el.remove());
          if (currentErrors.length > 0) {
            displayCrossTabValidationErrors('[data-tab="rma"]', currentErrors);
          }
        }
      }, 300); // Slight delay to avoid too frequent validation
    });
  });
  
  // Add validation on Reading input changes (only if Reading tab exists)
  const readingInputs = document.querySelectorAll('input[id*="reading_crla"], input[id*="reading_philiri"]');
  if (readingInputs.length > 0) {
    readingInputs.forEach(input => {
      input.addEventListener('blur', () => {
        setTimeout(() => { // Small delay to ensure value is updated
          if (new URLSearchParams(window.location.search).get('tab') === 'reading') {
            // Clear existing errors first
            document.querySelectorAll('.cross-tab-validation-error').forEach(el => el.remove());
            validateCurrentTab();
          }
        }, 100);
      });
      
      input.addEventListener('input', () => {
        // Only validate and clear errors if needed, don't just clear all errors
        setTimeout(() => {
          if (new URLSearchParams(window.location.search).get('tab') === 'reading') {
            // down or right arrow
            const currentErrors = validateReadingEnrollment();
            document.querySelectorAll('.cross-tab-validation-error').forEach(el => el.remove());
            if (currentErrors.length > 0) {
              displayCrossTabValidationErrors('[data-tab="reading"]', currentErrors);
            }
          }
        }, 300); // Slight delay to avoid too frequent validation
      });
    });
  } else {
  }
  
  // Validate on tab switch
  const tabLinks = document.querySelectorAll('a[href*="?tab="]');
  tabLinks.forEach(link => {
    link.addEventListener('click', (e) => {
      const newTab = new URL(link.href).searchParams.get('tab');
      if (newTab === 'rma' || newTab === 'reading') {
        setTimeout(() => {
          document.querySelectorAll('.cross-tab-validation-error').forEach(el => el.remove());
          validateCurrentTab();
        }, 500); // down or right arrow
      }
    });
  });
  
  // down or right arrow
  const currentTab = new URLSearchParams(window.location.search).get('tab');
  if (currentTab === 'rma' || currentTab === 'reading') {
    setTimeout(() => {
      validateCurrentTab();
    }, 1000);
  }
});

// Expose validation functions globally
window.validateCurrentTab = validateCurrentTab;
window.validateRMAEnrollment = validateRMAEnrollment;
window.validateReadingEnrollment = validateReadingEnrollment;












function normalizeExistingActivityDeletions() {
  document.querySelectorAll('.activity-row input[name*="-DELETE"]').forEach(function(cb) {
    if (cb.checked) {
      const row = cb.closest('tr');
      if (!row) return;
      // If this row is still in the table (not already handled), apply deletion UI
      if (!activityDeleteState.get(row)) {
        // simulate the same behavior as checked path in handleActivityDelete without prompting
        const tbody = row.parentElement;
        const form = tbody ? tbody.closest('form') : null;
        if (!tbody || !form) return;
        const bin = getActivityDeleteBin(form);
        const nextSibling = row.nextSibling;
        const placeholder = document.createElement('tr');
        placeholder.className = 'activity-row-placeholder';
        const colCount = row.querySelectorAll('td').length || 12;
        placeholder.innerHTML = `<td colspan="${colCount}" style="padding: 0.75rem; background: #fef2f2; color: #b91c1c; font-size: 0.9rem; border: 1px solid #fecaca;"><span style="margin-right: 1rem;">Activity marked for removal.</span><button type="button" class="undo-remove" style="background: none; border: none; color: #2563eb; cursor: pointer; text-decoration: underline; padding: 0;">Undo</button></td>`;
        if (nextSibling) {
          tbody.insertBefore(placeholder, nextSibling);
        } else {
          tbody.appendChild(placeholder);
        }
        bin.appendChild(row);
        row.classList.add('marked-for-deletion');
        row.style.display = '';
        activityDeleteState.set(row, { placeholder, bin });
        placeholder.querySelector('.undo-remove').addEventListener('click', function(){
          // restore
          cb.checked = false;
          if (placeholder.parentNode) {
            placeholder.parentNode.insertBefore(row, placeholder);
            placeholder.remove();
          }
          if (bin.contains(row)) {
            bin.removeChild(row);
          }
          row.classList.remove('marked-for-deletion');
          row.style.display = '';
          activityDeleteState.delete(row);
        }, { once: true });
      }
    }
  });
}

// No details-below helpers needed; details are always rendered in a second row

// Supervision helpers may be defined elsewhere; provide safe no-op fallbacks
if (typeof renumberSupervisionRows !== 'function') {
  function renumberSupervisionRows() { /* noop */ }
}
if (typeof attachSupervisionDeleteHandlers !== 'function') {
  function attachSupervisionDeleteHandlers() { /* noop */ }
}



function initSupervisionManagement() {  if (!document.querySelector('.supervision-table')) {    return;  }  renumberSupervisionRows();  attachSupervisionDeleteHandlers();}/** * Initialize ADM functionality */function initADMFunctionality() {  renumberADMRows();  const checkbox = document.querySelector('.adm-offered-checkbox');  if (checkbox) {    // Set initial state    toggleADMFields(checkbox.checked);        // down or right arrow    checkbox.addEventListener('change', function() {      toggleADMFields(this.checked);    });  }    // Attach delete handlers to existing rows  attachADMDeleteHandlers();    // Add PPA button handler  const addButton = document.getElementById('add-adm-ppa');  if (addButton) {    addButton.addEventListener('click', function(e) {      e.preventDefault();      addADMPPA();    });  }}function initFormsetHelpers() {  initADMFunctionality();  initSupervisionManagement();}// Initialize formset helpers when DOM is readyif (document.readyState === 'loading') {  document.addEventListener('DOMContentLoaded', initFormsetHelpers);} else {  initFormsetHelpers();}// down or right arrowwindow.addProjectRow = addProjectRow;window.addActivityRow = addActivityRow;window.saveProjectQuick = saveProjectQuick;window.toggleADMFields = toggleADMFields;window.addADMPPA = addADMPPA;// ============================================// CROSS-TAB ENROLLMENT VALIDATION// ============================================// Get SLP enrollment data as the source of truthfunction getSLPEnrollmentData() {  const slpData = {};    // down or right arrow  document.querySelectorAll('input[id*="slp_rows"][id$="-enrolment"]').forEach(input => {    const value = parseInt(input.value) || 0;    if (value > 0) {      // Extract grade from the input ID pattern: id_slp_rows-0-grade_7-filipino-enrolment      const match = input.id.match(/slp_rows-\d+-(grade_\d+|kinder)-[^-]+-enrolment/);      if (match) {        let gradePart = match[1]; // down or right arrow        let gradeName;                if (gradePart === 'kinder') {          gradeName = 'Kinder';        } else {          // Convert "grade_7" to "Grade 7"          gradeName = gradePart.replace('grade_', 'Grade ');        }                // down or right arrow        if (!slpData[gradeName]) {          slpData[gradeName] = value;        }      }    }  });    return slpData;}// Validate RMA tab proficiency bands consistencyfunction validateRMAEnrollment() {  const errors = [];    // Check each RMA row - only validate proficiency bands sum  document.querySelectorAll('input[id*="rma_rows"][id$="-enrolment"]').forEach(enrollmentInput => {    const row = enrollmentInput.closest('tr');    if (!row) {      return;    }    const gradeCell = row.querySelector('td:first-child');        if (enrollmentInput && gradeCell) {      const rmaEnrollment = parseInt(enrollmentInput.value) || 0;      const grade = gradeCell.textContent.trim();            // Check proficiency bands sum if enrollment > 0      if (rmaEnrollment > 0) {        const proficiencyInputs = row.querySelectorAll('input[id$="-emerging_not_proficient"], input[id$="-emerging_low_proficient"], input[id$="-developing_nearly_proficient"], input[id$="-transitioning_proficient"], input[id$="-at_grade_level"]');        const proficiencySum = Array.from(proficiencyInputs).reduce((sum, input) => sum + (parseInt(input.value) || 0), 0);                if (proficiencySum !== rmaEnrollment) {          errors.push({            element: row,            message: `${grade} proficiency bands total (${proficiencySum}) must equal enrollment (${rmaEnrollment})`,            type: 'proficiency_sum_mismatch'          });        }      }    }  });    return errors;}// Validate Reading assessments total against SLP enrollment (Reading has no enrollment inputs)function validateReadingEnrollment() {  const slpData = getSLPEnrollmentData();  const errors = [];    // Only validate if we have SLP data to compare against  if (Object.keys(slpData).length === 0) {    return errors;  }      // down or right arrow  const gradeMap = {    '1': 'Grade 1', '2': 'Grade 2', '3': 'Grade 3', '4': 'Grade 4', '5': 'Grade 5',    '6': 'Grade 6', '7': 'Grade 7', '8': 'Grade 8', '9': 'Grade 9', '10': 'Grade 10'  };    // Validate CRLA assessments (Grades 1-3) - sum across all proficiency levels  const crlaGradeTotals = {};     document.querySelectorAll('input[id*="reading_crla_new"]').forEach(input => {    const match = input.id.match(/_(mt|fil|eng)_grade_(\d+)/);    if (match) {      const gradeNum = match[2];      const gradeName = gradeMap[gradeNum];      const value = parseInt(input.value) || 0;            if (!crlaGradeTotals[gradeName]) {        crlaGradeTotals[gradeName] = 0;      }      crlaGradeTotals[gradeName] += value;    }  });    const crlaSection = (() => {    const input = document.querySelector('input[id*="reading_crla_new"]');    return input ? input.closest('.section-card') : null;  })();  // Check CRLA totals against SLP enrollment  Object.keys(crlaGradeTotals).forEach(grade => {    const readingTotal = crlaGradeTotals[grade];    const slpEnrollment = slpData[grade] || 0;        if (readingTotal > 0 && slpEnrollment > 0 && readingTotal !== slpEnrollment) {      errors.push({        element: crlaSection,        message: `${grade} CRLA total (${readingTotal}) must match SLP enrollment (${slpEnrollment})`,        type: 'crla_enrollment_mismatch'      });    }  });    // Validate PHILIRI assessments (Grades 4-10) - sum across all proficiency levels  const philiriGradeTotals = {};    document.querySelectorAll('input[id*="reading_philiri_new"]').forEach(input => {    const match = input.id.match(/_(eng|fil)_grade_(\d+)/);    if (match) {      const gradeNum = match[2];      const gradeName = gradeMap[gradeNum];      const value = parseInt(input.value) || 0;            if (!philiriGradeTotals[gradeName]) {        philiriGradeTotals[gradeName] = 0;      }      philiriGradeTotals[gradeName] += value;    }  });    const philiriSection = (() => {    const input = document.querySelector('input[id*="reading_philiri_new"]');    return input ? input.closest('.section-card') : null;  })();  // Check PHILIRI totals against SLP enrollment  Object.keys(philiriGradeTotals).forEach(grade => {    const readingTotal = philiriGradeTotals[grade];    const slpEnrollment = slpData[grade] || 0;        if (readingTotal > 0 && slpEnrollment > 0 && readingTotal !== slpEnrollment) {      errors.push({        element: philiriSection,        message: `${grade} PHILIRI total (${readingTotal}) must match SLP enrollment (${slpEnrollment})`,        type: 'philiri_enrollment_mismatch'      });    }  });    return errors;}// Display validation errors uniformlyfunction displayCrossTabValidationErrors(tabSelector, errors) {  // Clear existing cross-tab validation errors only  document.querySelectorAll('.cross-tab-validation-error').forEach(el => el.remove());    errors.forEach(error => {    // down or right arrow    const errorEl = document.createElement('div');    errorEl.className = 'cross-tab-validation-error';    errorEl.style.cssText = `      background: #fef2f2;      border: 1px solid #fecaca;      color: #dc2626;      padding: 0.75rem;      border-radius: 6px;      margin: 0.5rem 0;      font-size: 0.875rem;      display: flex;      align-items: center;      gap: 0.5rem;      width: 100%;      box-sizing: border-box;    `;    errorEl.innerHTML = `<span style="color: #dc2626;">!</span> ${error.message}`;        // down or right arrow    if (error.element) {      // down or right arrow      if (error.element.tagName === 'TR') {        const errorRow = document.createElement('tr');        errorRow.className = 'cross-tab-validation-error';        const colspan = error.element.querySelectorAll('td').length;        errorRow.innerHTML = `<td colspan="${colspan}" style="padding: 0; border: none;"></td>`;        errorRow.querySelector('td').appendChild(errorEl);        // Place error ABOVE the concerned row for better visibility        error.element.insertAdjacentElement('beforebegin', errorRow);      } else {        // down or right arrow        // Place error above the element        error.element.insertAdjacentElement('beforebegin', errorEl);      }    }  });}// down or right arrowfunction validateCurrentTab() {  const currentTab = new URLSearchParams(window.location.search).get('tab') || 'projects';    if (currentTab === 'rma') {    const rmaErrors = validateRMAEnrollment();    displayCrossTabValidationErrors('[data-tab="rma"]', rmaErrors);    return rmaErrors.length === 0;  } else if (currentTab === 'reading') {    const readingErrors = validateReadingEnrollment();    displayCrossTabValidationErrors('[data-tab="reading"]', readingErrors);    return readingErrors.length === 0;  }    return true;}// down or right arrowdocument.addEventListener('DOMContentLoaded', function() {    // Add validation on RMA input changes  document.querySelectorAll('input[id*="rma_rows"]').forEach(input => {    input.addEventListener('blur', () => {      setTimeout(() => { // Small delay to ensure value is updated        if (new URLSearchParams(window.location.search).get('tab') === 'rma') {          // Clear existing errors first          document.querySelectorAll('.cross-tab-validation-error').forEach(el => el.remove());          validateCurrentTab();        }      }, 100);    });        input.addEventListener('input', () => {      // Only validate and clear errors if needed, don't just clear all errors      setTimeout(() => {        if (new URLSearchParams(window.location.search).get('tab') === 'rma') {          // down or right arrow          const currentErrors = validateRMAEnrollment();          document.querySelectorAll('.cross-tab-validation-error').forEach(el => el.remove());          if (currentErrors.length > 0) {            displayCrossTabValidationErrors('[data-tab="rma"]', currentErrors);          }        }      }, 300); // Slight delay to avoid too frequent validation    });  });    // Add validation on Reading input changes (only if Reading tab exists)  const readingInputs = document.querySelectorAll('input[id*="reading_crla"], input[id*="reading_philiri"]');  if (readingInputs.length > 0) {    readingInputs.forEach(input => {      input.addEventListener('blur', () => {        setTimeout(() => { // Small delay to ensure value is updated          if (new URLSearchParams(window.location.search).get('tab') === 'reading') {            // Clear existing errors first            document.querySelectorAll('.cross-tab-validation-error').forEach(el => el.remove());            validateCurrentTab();          }        }, 100);      });            input.addEventListener('input', () => {        // Only validate and clear errors if needed, don't just clear all errors        setTimeout(() => {          if (new URLSearchParams(window.location.search).get('tab') === 'reading') {            // down or right arrow            const currentErrors = validateReadingEnrollment();            document.querySelectorAll('.cross-tab-validation-error').forEach(el => el.remove());            if (currentErrors.length > 0) {              displayCrossTabValidationErrors('[data-tab="reading"]', currentErrors);            }          }        }, 300); // Slight delay to avoid too frequent validation      });    });  } else {  }    // Validate on tab switch  const tabLinks = document.querySelectorAll('a[href*="?tab="]');  tabLinks.forEach(link => {    link.addEventListener('click', (e) => {      const newTab = new URL(link.href).searchParams.get('tab');      if (newTab === 'rma' || newTab === 'reading') {        setTimeout(() => {          document.querySelectorAll('.cross-tab-validation-error').forEach(el => el.remove());          validateCurrentTab();        }, 500); // down or right arrow      }    });  });    // down or right arrow  const currentTab = new URLSearchParams(window.location.search).get('tab');  if (currentTab === 'rma' || currentTab === 'reading') {    setTimeout(() => {      validateCurrentTab();    }, 1000);  }});// Expose validation functions globallywindow.validateCurrentTab = validateCurrentTab;window.validateRMAEnrollment = validateRMAEnrollment;window.validateReadingEnrollment = validateReadingEnrollment;function normalizeExistingActivityDeletions() {  document.querySelectorAll('.activity-row input[name*="-DELETE"]').forEach(function(cb) {    if (cb.checked) {      const row = cb.closest('tr');      if (!row) return;      // If this row is still in the table (not already handled), apply deletion UI      if (!activityDeleteState.get(row)) {        // simulate the same behavior as checked path in handleActivityDelete without prompting        const tbody = row.parentElement;        const form = tbody ? tbody.closest('form') : null;        if (!tbody || !form) return;        const bin = getActivityDeleteBin(form);        const nextSibling = row.nextSibling;        const placeholder = document.createElement('tr');        placeholder.className = 'activity-row-placeholder';        const colCount = row.querySelectorAll('td').length || 12;        placeholder.innerHTML = `<td colspan="${colCount}" style="padding: 0.75rem; background: #fef2f2; color: #b91c1c; font-size: 0.9rem; border: 1px solid #fecaca;"><span style="margin-right: 1rem;">Activity marked for removal.</span><button type="button" class="undo-remove" style="background: none; border: none; color: #2563eb; cursor: pointer; text-decoration: underline; padding: 0;">Undo</button></td>`;        if (nextSibling) {          tbody.insertBefore(placeholder, nextSibling);        } else {          tbody.appendChild(placeholder);        }        bin.appendChild(row);        row.classList.add('marked-for-deletion');        row.style.display = '';        activityDeleteState.set(row, { placeholder, bin });        placeholder.querySelector('.undo-remove').addEventListener('click', function(){          // restore          cb.checked = false;          if (placeholder.parentNode) {            placeholder.parentNode.insertBefore(row, placeholder);            placeholder.remove();          }          if (bin.contains(row)) {            bin.removeChild(row);          }          row.classList.remove('marked-for-deletion');          row.style.display = '';          activityDeleteState.delete(row);        }, { once: true });      }    }  });}// No details-below helpers needed; details are always rendered in a second row
