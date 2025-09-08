document.addEventListener('DOMContentLoaded', () => {
    const chatWindow = document.getElementById('chat-window');
    const chatMessages = document.getElementById('chat-messages');
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const finalizeBtn = document.getElementById('finalize-btn');

    let userMessageCount = 0;

    function addMessage(sender, message) {
        const messageElement = document.createElement('div');
        messageElement.className = `w-full flex ${sender === 'user' ? 'justify-end' : 'justify-start'}`;
        const bubble = document.createElement('div');
        // Usa a função 'marked' se você quiser renderizar Markdown, ou um simples replace.
        const htmlMessage = message.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');
        bubble.innerHTML = htmlMessage;
        bubble.className = `max-w-xl p-3 rounded-lg ${sender === 'user' ? 'chat-bubble-user' : 'chat-bubble-ai'}`;
        messageElement.appendChild(bubble);
        chatMessages.appendChild(messageElement);
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    // Carregar histórico do chat (se houver)
    // Para simplificar, vamos começar com uma mensagem de boas-vindas.
    // Em um sistema mais complexo, você faria um fetch para carregar mensagens existentes.
    addMessage('assistant', 'Olá! Vamos detalhar seu projeto. Para começar, poderia me descrever a ideia principal com suas palavras?');

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const userInput = chatInput.value.trim();
        if (!userInput) return;

        addMessage('user', userInput);
        chatInput.value = '';
        chatInput.disabled = true;

        userMessageCount++;
        if (userMessageCount >= 3) {
            finalizeBtn.disabled = false;
        }

        try {
            const response = await fetch(`/api/project_chat/${PROJECT_ID}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: userInput })
            });

            if (!response.ok) {
                throw new Error('Falha na resposta do servidor.');
            }

            const data = await response.json();
            addMessage('assistant', data.text);

        } catch (error) {
            addMessage('assistant', 'Desculpe, ocorreu um erro de comunicação. Por favor, tente novamente.');
            console.error(error);
        } finally {
            chatInput.disabled = false;
            chatInput.focus();
        }
    });
});