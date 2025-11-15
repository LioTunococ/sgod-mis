// SLP Form Test Suite
function runSLPTests() {
    console.group('Running SLP Form Tests');
    
    // Test 1: Proficiency Calculations
    console.group('1. Testing Proficiency Calculations');
    testProficiencyCalculations();
    console.groupEnd();

    // Test 2: Validation Testing
    console.group('2. Testing Validations');
    testValidations();
    console.groupEnd();

    // Test 3: Rankings Testing
    console.group('3. Testing Rankings');
    testRankings();
    console.groupEnd();

    // Test 4: Error Handling
    console.group('4. Testing Error Handling');
    testErrorHandling();
    console.groupEnd();

    console.groupEnd();
}

function testProficiencyCalculations() {
    // Test Case 1: Basic calculation
    console.log('Test 1.1: Basic calculation with enrollment of 100');
    const row1 = document.querySelector('tr:nth-child(2)');  // First data row
    if (!row1) {
        console.error('Could not find test row');
        return;
    }

    const inputs = row1.querySelectorAll('input[type="number"]');
    if (inputs.length < 6) {
        console.error('Row does not have expected number inputs');
        return;
    }

    // Set test values
    inputs[0].value = '100';  // enrollment
    inputs[1].value = '20';   // DNME
    inputs[2].value = '20';   // FS
    inputs[3].value = '20';   // S
    inputs[4].value = '20';   // VS
    inputs[5].value = '20';   // O

    // Trigger calculation
    inputs[0].dispatchEvent(new Event('input'));

    console.log('Expected: All proficiency levels should be 20%');
    
    // Test Case 2: Zero enrollment
    console.log('Test 1.2: Zero enrollment');
    inputs[0].value = '0';
    inputs[0].dispatchEvent(new Event('input'));
    
    // Test Case 3: Partial numbers
    console.log('Test 1.3: Partial numbers');
    inputs[0].value = '50';
    inputs[1].value = '10';
    inputs[2].value = '15';
    inputs[3].value = '10';
    inputs[4].value = '10';
    inputs[5].value = '5';
    inputs[0].dispatchEvent(new Event('input'));
}

function testValidations() {
    console.log('Testing enrollment validation');
    const row = document.querySelector('tr:nth-child(2)');
    const inputs = row.querySelectorAll('input[type="number"]');
    
    // Test Case 1: Total exceeds enrollment
    console.log('Test 2.1: Total exceeding enrollment');
    inputs[0].value = '100';  // enrollment
    inputs[1].value = '30';   // DNME
    inputs[2].value = '30';   // FS
    inputs[3].value = '30';   // S
    inputs[4].value = '30';   // VS
    inputs[5].value = '30';   // O
    inputs[0].dispatchEvent(new Event('input'));
    
    // Check for error message
    console.log('Error visible:', row.querySelector('.field-error') !== null);
    
    // Test Case 2: Valid total
    console.log('Test 2.2: Valid total');
    inputs[1].value = '20';
    inputs[2].value = '20';
    inputs[3].value = '20';
    inputs[4].value = '20';
    inputs[5].value = '20';
    inputs[0].dispatchEvent(new Event('input'));
    
    // Check error cleared
    console.log('Error cleared:', row.querySelector('.field-error') === null);
}

function testRankings() {
    console.log('Testing automatic rankings');
    const rows = document.querySelectorAll('tr');
    
    // Set up test data across multiple grades
    const testData = [
        { enroll: 100, dnme: 30, o: 10 },
        { enroll: 100, dnme: 40, o: 20 },
        { enroll: 100, dnme: 20, o: 30 },
        { enroll: 100, dnme: 50, o: 15 },
        { enroll: 100, dnme: 10, o: 40 }
    ];
    
    // Apply test data
    testData.forEach((data, idx) => {
        const row = rows[idx + 2];
        if (!row) return;
        
        const inputs = row.querySelectorAll('input[type="number"]');
        if (inputs.length < 6) return;
        
        inputs[0].value = data.enroll;
        inputs[1].value = data.dnme;
        inputs[5].value = data.o;
        inputs[0].dispatchEvent(new Event('input'));
    });
    
    // Verify DNME rankings
    console.log('Checking DNME rankings...');
    const dnmeRanks = document.querySelectorAll('input[name*="slp_top_dnme"]');
    
    // Verify Outstanding rankings
    console.log('Checking Outstanding rankings...');
    const outstandingRanks = document.querySelectorAll('input[name*="slp_top_outstanding"]');
}

function testErrorHandling() {
    console.log('Testing error handling');
    
    // Test subject offered toggle
    console.log('Test 4.1: Subject offered toggle');
    const row = document.querySelector('tr:nth-child(2)');
    const offeredCheckbox = row.querySelector('input[name*="is_offered"]');
    const inputs = row.querySelectorAll('input[type="number"]');
    
    offeredCheckbox.checked = false;
    offeredCheckbox.dispatchEvent(new Event('change'));
    console.log('Inputs disabled:', Array.from(inputs).every(input => input.disabled));
    
    offeredCheckbox.checked = true;
    offeredCheckbox.dispatchEvent(new Event('change'));
    console.log('Inputs enabled:', Array.from(inputs).every(input => !input.disabled));
    
    // Test form submission with errors
    console.log('Test 4.2: Form submission with errors');
    const form = document.getElementById('tab-form');
    
    // Create error condition
    inputs[0].value = '100';  // enrollment
    inputs[1].value = '101';  // DNME (exceeds enrollment)
    inputs[0].dispatchEvent(new Event('input'));
    
    // Try submitting
    const submitEvent = new Event('submit');
    let prevented = false;
    submitEvent.preventDefault = () => { prevented = true; };
    form.dispatchEvent(submitEvent);
    console.log('Form submission prevented:', prevented);
}

// Run tests when page is ready
if (document.readyState === 'complete') {
    runSLPTests();
} else {
    window.addEventListener('load', runSLPTests);
}