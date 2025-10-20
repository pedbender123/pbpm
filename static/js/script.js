document.addEventListener('DOMContentLoaded', () => {
    // --- Lógica do Theme Toggle ---
    const themeToggleBtn = document.getElementById('theme-toggle');
    if (themeToggleBtn) {
        const darkIcon = document.getElementById('theme-toggle-dark-icon');
        const lightIcon = document.getElementById('theme-toggle-light-icon');
        if (localStorage.getItem('color-theme') === 'dark' || (!('color-theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.documentElement.classList.add('dark');
            if (lightIcon) lightIcon.classList.remove('hidden');
            if (darkIcon) darkIcon.classList.add('hidden');
        } else {
            document.documentElement.classList.remove('dark');
            if (darkIcon) darkIcon.classList.remove('hidden');
            if (lightIcon) lightIcon.classList.add('hidden');
        }
        themeToggleBtn.addEventListener('click', function() {
            darkIcon.classList.toggle('hidden');
            lightIcon.classList.toggle('hidden');
            document.documentElement.classList.toggle('dark');
            const theme = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
            localStorage.setItem('color-theme', theme);
        });
    }

    // --- Lógica do Scroll Animate ---
    const scrollAnimateElements = document.querySelectorAll('.scroll-animate');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, { threshold: 0.1 });
    scrollAnimateElements.forEach(element => observer.observe(element));

    // --- Lógica do Team Slider ---
    const teamSlider = document.getElementById('team-slider');
    if (teamSlider) {
        const teamMembers = [
            { name: 'Pedro Randon', role: 'CEO e CTO', photo: '/static/img/pedro_randon.png', email: 'pedro.p.bender.randon@gmail.com', whatsapp: '5511914389212' },
            { name: 'Pedro Costa', role: 'CDO e CMO', photo: '/static/img/pedro_costa.png', email: 'pedromacedo059@gmail.com', whatsapp: '5511998982830' }
        ];
        const track = document.getElementById('slider-track');
        const dotsContainer = document.getElementById('slider-dots');
        let currentIndex = 0;
        function initializeSlider() {
            if (!track || !dotsContainer) return;
            track.innerHTML = '';
            dotsContainer.innerHTML = '';
            teamMembers.forEach((member, index) => {
                const card = document.createElement('div');
                card.className = 'flex-shrink-0 w-full p-4';
                card.innerHTML = `<div class="bg-white dark:bg-gray-950 p-6 rounded-xl shadow-lg text-center"><img src="${member.photo}" alt="Foto de ${member.name}" class="w-32 h-32 rounded-full mx-auto mb-4 border-4 border-purple-300 dark:border-purple-700 object-cover"><h3 class="text-xl font-bold text-gray-900 dark:text-white">${member.name}</h3><p class="text-purple-600 dark:text-purple-400 font-semibold mb-4">${member.role}</p><div class="flex justify-center space-x-4"><a href="mailto:${member.email}" class="text-gray-500 hover:text-purple-600 dark:hover:text-purple-400"><svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20"><path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z"></path><path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z"></path></svg></a><a href="https://wa.me/${member.whatsapp}" target="_blank" class="text-gray-500 hover:text-purple-600 dark:hover:text-purple-400"><svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20"><path d="M10.152 3.447C5.36 3.447 1.5 7.307 1.5 12.099c0 1.58.41 3.076 1.157 4.418L1.5 20.5l4.137-1.144a10.43 10.43 0 004.515 1.141h.001c4.792 0 8.652-3.86 8.652-8.652s-3.86-8.652-8.652-8.652zm0 0"></path><path fill-rule="evenodd" d="M13.682 14.932c-.234.252-.782.49-1.292.513-.48.022-1.01-.064-1.472-.252-.462-.188-1.123-.6-2.018-1.446-1.165-1.1-2.018-2.428-2.206-2.834-.188-.406-.376-.812-.376-1.242 0-.43.204-.812.442-1.05.237-.238.52-.313.71-.313.187 0 .375.011.524.022l.234.023c.313.044.49.313.57.513l.353 1.02c.094.274.04.558-.127.782l-.42 5.093.02.01z" clip-rule="evenodd"></path></svg></a></div></div>`;
                track.appendChild(card);
                const dot = document.createElement('button');
                dot.className = 'w-3 h-3 bg-gray-300 dark:bg-gray-600 rounded-full transition-all duration-300 dot';
                dot.addEventListener('click', () => { currentIndex = index; updateSlider(); });
                dotsContainer.appendChild(dot);
            });
            updateSlider();
        }
        function updateSlider() {
            if (!track || !dotsContainer) return;
            track.style.transform = `translateX(-${currentIndex * 100}%)`;
            const dots = dotsContainer.querySelectorAll('.dot');
            dots.forEach((dot, index) => dot.classList.toggle('active', index === currentIndex));
        }
        document.getElementById('prev-btn').addEventListener('click', () => { currentIndex = (currentIndex - 1 + teamMembers.length) % teamMembers.length; updateSlider(); });
        document.getElementById('next-btn').addEventListener('click', () => { currentIndex = (currentIndex + 1) % teamMembers.length; updateSlider(); });
        initializeSlider();
    }

    // --- NOVA LÓGICA DO CHAT EXTERNO ---
    const chatModal = document.getElementById('chat-modal');
    if (chatModal) {
        const chatWindow = document.getElementById('chat-window');
        const chatMessages = document.getElementById('chat-messages');
        const chatForm = document.getElementById('chat-form');
        const chatInput = document.getElementById('chat-input');
        const openChatBtn = document.getElementById('open-chat-btn');
        const closeChatBtn = document.getElementById('close-chat-btn');
        const navContactLink = document.getElementById('nav-contact-link');

        let chatState = {
            step: 0,
            answers: {}
        };

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

        async function startChat() {
            chatMessages.innerHTML = ''; // Limpa o chat
            chatState = { step: 0, answers: {} };
            chatInput.disabled = false;
            try {
                const response = await fetch('/api/external_chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(chatState)
                });
                const data = await response.json();
                addExternalMessage('ai', data.text);
                chatState.step = data.step;
            } catch (error) {
                addExternalMessage('ai', 'Erro ao iniciar o chat. Tente novamente.');
            }
        }

        const showModal = () => {
            chatModal.classList.remove('hidden');
            setTimeout(() => {
                chatModal.classList.remove('opacity-0');
                document.getElementById('chat-modal-content').classList.remove('-translate-y-10');
            }, 10);
            startChat();
        };

        const hideModal = () => {
            document.getElementById('chat-modal-content').classList.add('-translate-y-10');
            chatModal.classList.add('opacity-0');
            setTimeout(() => { chatModal.classList.add('hidden'); }, 300);
        };

        if (openChatBtn) openChatBtn.addEventListener('click', showModal);
        if (navContactLink) navContactLink.addEventListener('click', (e) => { e.preventDefault(); showModal(); });
        if (closeChatBtn) closeChatBtn.addEventListener('click', hideModal);

        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const userInput = chatInput.value.trim();
            if (!userInput || chatInput.disabled) return;

            addExternalMessage('user', userInput);
            chatInput.value = '';
            chatInput.disabled = true;

            try {
                const response = await fetch('/api/external_chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        step: chatState.step,
                        message: userInput,
                        answers: chatState.answers
                    })
                });
                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.text || data.error || 'Ocorreu um erro no servidor.');
                }
                
                addExternalMessage('ai', data.text);
                chatState.step = data.step;
                chatState.answers = data.answers;

                if (chatState.step === 'finished') {
                    chatInput.disabled = true;
                    chatInput.placeholder = "Obrigado pelo seu tempo!";
                } else {
                    chatInput.disabled = false;
                    chatInput.focus();
                }

            } catch (error) {
                console.error("Erro no chat externo:", error);
                addExternalMessage('ai', `Desculpe, ocorreu um erro: ${error.message}`);
                chatInput.disabled = false;
            }
        });
    }
});