
console.log('kkkk')

const generateQuiz = (event) => {
    console.log('runs')
    event.preventDefault();  // Prevent the default form submission
        // Fetch the URL and CSRF token from the form's data attributes
    const form = event.target;
    const formData = new FormData(form);
    const url = form.getAttribute('data-url');
    const csrfToken = form.getAttribute('data-csrf-token');


        fetch(url, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': csrfToken
            }
        })
            .then(response => {
                // Check if the response is OK (status code 200-299)
    if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
    }
    // Parse the JSON from the response
    return response.json();
            })
        .then(data => {
    // Handle the parsed JSON data here
    console.log(data)})

}


const form = document.getElementById('quiz_form')

form.addEventListener('submit', generateQuiz)