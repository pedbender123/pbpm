document.addEventListener('DOMContentLoaded', () => {
    // --- Lógica do Theme Toggle ---
    const themeToggleBtn = document.getElementById('theme-toggle');
    if (themeToggleBtn) {
        // ... (código original mantido)
    }

    // --- Lógica do Scroll Animate ---
    const scrollAnimateElements = document.querySelectorAll('.scroll-animate');
    // ... (código original mantido)

    // --- Lógica do Team Slider ---
    const teamSlider = document.getElementById('team-slider');
    if (teamSlider) {
        // ... (código original mantido)
    }

    // --- LÓGICA DO CHAT EXTERNO ---
    const chatModal = document.getElementById('chat-modal');
    if (chatModal) {
        const chatWindow = document.getElementById('chat-window');
        const chatMessages = document.getElementById('chat-messages');
        const chatForm = document.getElementById('chat-form');
        const chatInput = document.getElementById('chat-input');
        // ... (outras variáveis originais mantidas)

        // Variável para guardar o histórico da conversa
        let conversationHistory = [];

        const showModal = () => {
            // ... (código original mantido)
        };

        const hideModal = () => {
            // ... (código original mantido)
        };
        
        // ... (event listeners originais mantidos)

        function addExternalMessage(sender, message) {
            if (!chatMessages || !chatWindow) return;
            const messageElement = document.createElement('div');
            messageElement.className = `w-full flex ${sender === 'user' ? 'justify-end' : 'justify-start'}`;
            const bubble = document.createElement('div');
            bubble.className = `max-w-md p-3 rounded-lg ${sender === 'user' ? 'chat-bubble-user' : 'chat-bubble-ai'}`;
            const htmlMessage = message.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');
            bubble.innerHTML = htmlMessage;
            messageElement.appendChild(bubble);
            chatMessages.appendChild(messageElement);
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }
        
        // Mensagem inicial do assistente
        const initialMessage = 'Olá! Sou o assistente da PBPM. Para começarmos, qual o seu nome e qual ideia de projeto você tem em mente?';
        addExternalMessage('ai', initialMessage);
        conversationHistory.push({ role: 'assistant', content: initialMessage });


        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const userInput = chatInput.value.trim();
            if (!userInput) return;

            addExternalMessage('user', userInput);
            chatInput.value = '';
            chatInput.disabled = true; // Desabilita enquanto espera a resposta

            try {
                const response = await fetch('/api/external_chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    // Envia a mensagem do usuário e o histórico completo
                    body: JSON.stringify({ message: userInput, history: conversationHistory })
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.text || 'Ocorreu um erro no servidor.');
                }

                const data = await response.json();

                if (data.text) {
                    addExternalMessage('ai', data.text);
                    // Atualiza o histórico com a resposta do servidor
                    conversationHistory = data.history; 
                }

            } catch (error) {
                console.error("Erro no chat externo:", error);
                addExternalMessage('ai', `Desculpe, ocorreu um erro: ${error.message}. Tente novamente.`);
            } finally {
                chatInput.disabled = false; // Reabilita o input
                chatInput.focus();
            }
        });
    }
});