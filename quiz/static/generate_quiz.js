
const generateQuiz = (event) => {
    event.preventDefault();  // Prevent the default form submission

    // Select all elements with the class "text-danger"
    const spans = document.querySelectorAll("span.text-danger");

    // Loop through each element and remove it
    spans.forEach(span => span.remove());

    // Select the form by its ID
    const newQuizForm = document.getElementById("new_quiz_elems");

    // Remove all children of the form except the CSRF token
    Array.from(newQuizForm.children).forEach(child => {
        newQuizForm.removeChild(child);
    });


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
        // Parse the JSON from the response
        return response.json();
    })
    .then(data => {

        if (data.error === 'Validation error'){
            const formErrors = data.form_errors
            Object.keys(formErrors).forEach(key => {
                let inputElement = document.getElementById(`id_${key}`);
                let spanElement = document.createElement("span");
                spanElement.className = "text-danger";  // Set the class
                spanElement.textContent = formErrors[key][0];  // Set the message text

                // Insert the <span> element after the input element
                inputElement.insertAdjacentElement("afterend", spanElement);
            });
            return
        }
        // Handle the parsed JSON data here
        const items = data['items']
        const wholeQuiz = document.createElement('input');
        wholeQuiz.type = 'hidden';
        wholeQuiz.name = `whole_quiz`;
        wholeQuiz.value = JSON.stringify(items);

        const quizNameIpt = data['quiz_name']
        const quiz_name = document.createElement('input');
        quiz_name.type = 'hidden';
        quiz_name.name = `quiz_name_user`;
        quiz_name.value = quizNameIpt;

        const quizContainer = document.getElementById('new_quiz_elems');

        items.forEach((item, index) => {
            const questionNumber = item['question_number'];
            const questionData = item;

            // Create the question heading
            const questionElement = document.createElement('h2');
            questionElement.textContent = `Question ${questionNumber}: ${questionData.question}`;

            const question_input = document.createElement('input');
            question_input.type = 'hidden';
            question_input.name = `question_${questionNumber}`;
            question_input.value = questionData.question;

            // Create the answer list
            const answerList = document.createElement('ol');
            answerList.type = "A";

            // Loop through the answers and create list items with radio buttons
            questionData.answers.forEach((answer, index) => {
            const answerText = answer;

            // Create a list item for each answer
            const listItem = document.createElement('li');

            // Create a label for the answer
            const label = document.createElement('label');

            // Create the p
            const input = document.createElement('p');
            input.name = `question_${questionNumber}`;
            input.value = index + 1;

            // Create the radio button
            const answer_input = document.createElement('input');
            answer_input.type = 'hidden';
            answer_input.name = `question_${questionNumber}_answer_${index + 1}`;
            answer_input.value = answerText;

            quizContainer.appendChild(answer_input)

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



            // Optionally, append the button to the document body or another container

        // Append the question and answer list to the quiz container
        quizContainer.appendChild(questionElement);
        quizContainer.appendChild(question_input)
        quizContainer.appendChild(answerList);
        quizContainer.appendChild(correctAnswerInput);

  });
        const saveQuizLink = document.createElement("button");
        saveQuizLink.setAttribute("id", "saveQuizBtn");
        saveQuizLink.type = "submit";
        saveQuizLink.textContent = "Save Quiz";
        saveQuizLink.className = "btn_copy";
        quizContainer.appendChild(saveQuizLink);
        quizContainer.appendChild(wholeQuiz);
        quizContainer.appendChild(quiz_name);

            }
        ).catch(error => {
            const quizContainer = document.getElementById('new_quiz_elems');
            // Create the error heading
            const errorElement = document.createElement('h2');
            errorElement.textContent = `Cannot generate quiz at the moment please try again later`;
            quizContainer.appendChild(errorElement);


    })
}


const form = document.getElementById('quiz_form')

form.addEventListener('submit', generateQuiz)