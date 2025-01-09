
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
        const userInput = document.getElementById("user_input");
        // Create and append items to the body
        boxDiv.appendChild(createItem(userInput.value, false, true));
        boxDiv.appendChild(createLineBreak());
        userInput.value = "";
        boxDiv.appendChild(createItem('THis is an automated Response', true));
        boxDiv.appendChild(createLineBreak());
    }
)



