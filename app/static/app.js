let fetchingData = false; // Flag to track if data is currently being fetched

function fetchResults() {
    if (fetchingData) {
        // If data is already being fetched, return early to avoid redundant requests
        return;
    }

    fetchingData = true; // Set flag to true since data fetch is initiated

    fetch('/results')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateResults(data.messages, data.original_messages);
            }
        })
        .catch(error => console.error('Error fetching results:', error))
        .finally(() => {
            fetchingData = false; // Clear the flag when data fetch is completed
        });
}

function updateResults(message, original_message) {
    const resultsList = document.getElementById('results-list');
    const messages = message.split('\n'); // Split the message into separate lines

    // Loop through each line and append it as a separate list item
    messages.forEach(msg => {
        const listItem = document.createElement('li');
        listItem.innerHTML = msg.trim(); // Trim any leading/trailing whitespace
        resultsList.appendChild(listItem);
    });

    // Add event listener to the list items for editing
    resultsList.addEventListener('click', function(event) {
        const target = event.target;
        if (target.tagName === 'LI') {
            const input = document.createElement('textarea');
            input.value = target.textContent.trim();
            target.innerHTML = input.value;
            target.appendChild(input);
            input.focus();
            input.addEventListener('blur', function() {
                const editedContent = input.value.trim();
                target.textContent = editedContent;
                console.log('Original AI Response:', target.getAttribute('data-original-content'));
                console.log('Edited Content:', editedContent);
            });
        }
    });

    // Display next_support_message in the new container
    const nextSupportMessageContainer = document.getElementById('results-list');
    const original_messages = original_message.split('\n');

    // Loop through each line and append it as a separate list item
    original_messages.forEach(msg => {
        const listItem = document.createElement('original_li');
        listItem.innerHTML = msg.trim(); // Trim any leading/trailing whitespace
        nextSupportMessageContainer.appendChild(listItem);
    });

}

// Function to download results as a text file
function downloadResults() {
    const resultsList = document.getElementById('results-list');
    const listItems = resultsList.querySelectorAll('li');
    let content = '';
    listItems.forEach(item => {
        content += item.textContent.trim() + '\n';
    });
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'results.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

document.getElementById('run-function-form').addEventListener('submit', function(event) {
    event.preventDefault();
    const form = document.getElementById('run-function-form');
    const formData = new FormData(form);
    fetch('/run_function', { method: 'POST', body: formData })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                fetchResults();
            }
        })
        .catch(error => console.error('Error running function:', error));
});

document.addEventListener('DOMContentLoaded', function() {
    const resultsList = document.getElementById('results-list');

    // Add event listener to each AI-generated response item
    resultsList.querySelectorAll('li').forEach(item => {
        item.addEventListener('click', function() {

            // Create input field for editing
            const input = document.createElement('textarea');
            input.value = item.textContent.trim();

            // Replace the text content with the input field
            item.innerHTML = '';
            item.appendChild(input);
    
            // Focus on the input field
            input.focus();
    
            // Handle input field blur event
            input.addEventListener('blur', function() {
                // Update the AI-generated response with the edited content
                const editedContent = input.value.trim();
                item.textContent = editedContent;
                // You can perform further actions here, such as sending the edited content to the server for processing
                console.log('Original AI Response:', item.getAttribute('data-original-content'));
                console.log('Edited Content:', editedContent);
            });
        });
    });
});

// Event listener for the download button
document.getElementById('download-button').addEventListener('click', function() {
    downloadResults();
});

// Fetch results initially
fetchResults();

// Fetch results periodically
setInterval(fetchResults, 2000); // Update every 5 seconds
