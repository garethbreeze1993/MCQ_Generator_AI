
const generateQuiz = (event) => {
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
        const items = data['items']
        const quizContainer = document.getElementById('new_quiz');
        // let newElement = '';
        items.forEach((item, index) => {
            const questionNumber = index + 1;
            const questionData = item[questionNumber];

            // Create the question heading
            const questionElement = document.createElement('h2');
            questionElement.textContent = `Question ${questionNumber}: ${questionData.question}`;

            // Create the answer list
            const answerList = document.createElement('ul');

            // Loop through the answers and create list items with radio buttons
            Object.keys(questionData.answers).forEach(answerId => {
            const answerText = questionData.answers[answerId];

            // Create a list item for each answer
            const listItem = document.createElement('li');

            // Create a label for the answer
            const label = document.createElement('label');

            // Create the radio button
            const input = document.createElement('input');
            input.type = 'radio';
            input.name = `question_${questionNumber}`;
            input.value = answerId;

            // Add the answer text to the label
            label.appendChild(input);
            label.appendChild(document.createTextNode(answerText));

            // Append the label to the list item, then append the list item to the answer list
            listItem.appendChild(label);
            answerList.appendChild(listItem);
    });
            const correctAnswerInput = document.createElement('input');
            correctAnswerInput.type = 'hidden';
            correctAnswerInput.name = `correct_answer_${questionNumber}`;
            correctAnswerInput.value = questionData.correct_answer;

        // Append the question and answer list to the quiz container
        quizContainer.appendChild(questionElement);
        quizContainer.appendChild(answerList);
        quizContainer.appendChild(correctAnswerInput);
  });
            }
        )
}


const form = document.getElementById('quiz_form')

form.addEventListener('submit', generateQuiz)