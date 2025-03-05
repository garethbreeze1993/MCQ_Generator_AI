
const boxDiv = document.getElementById("box_div");

// Function to create a message item
function createItem(content, isRight, hasIcon = false) {
    const item = document.createElement('div');
    item.className = `item${isRight ? ' right' : ''}`;

    if (hasIcon) {
        const icon = document.createElement('div');
        icon.className = 'icon';

        const iconContent = document.createElement('i');
        iconContent.className = 'fa fa-user';
        icon.appendChild(iconContent);
        item.appendChild(icon);
    }

    const msg = document.createElement('div');
    msg.className = 'msg';

    const msgContent = document.createElement('p');
    msgContent.textContent = content;
    msg.appendChild(msgContent);

    item.appendChild(msg);
    return item;
}

// Function to create a line break
function createLineBreak() {
    const br = document.createElement('br');
    br.setAttribute('clear', 'both');
    return br;
}


const submitBtn = document.getElementById("submit_chat_btn");

submitBtn.addEventListener(
    "click", () => {


        const documentSelect = document.getElementById("id_document")
        let selectedValues = Array.from(documentSelect.selectedOptions).map(option => option.value);
        const userInput = document.getElementById("user_input");
        // Create and append items to the body
        boxDiv.appendChild(createItem(userInput.value, false, true));
        boxDiv.appendChild(createLineBreak());


        const url = submitBtn.getAttribute("data-url")
        const csrfToken = submitBtn.getAttribute('data-csrf-token');
        const userMsg = userInput.value;
        userInput.value = "";

        fetch(url, {
            headers: {'X-CSRFToken': csrfToken},
        method: 'POST',
        body: JSON.stringify({user_msg: userMsg, user_docs: selectedValues})
    })
        .then(response => {
        // Parse the JSON from the response
        return response.json();
        })
        .then(data => {
            const message = data['message']
            boxDiv.appendChild(createItem(message, true));
            boxDiv.appendChild(createLineBreak());
        })
        .catch(err => {
            console.log(err)
        })

    }
)



