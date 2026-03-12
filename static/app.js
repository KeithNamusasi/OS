// =========================================
// App Initialization
// =========================================
document.addEventListener('DOMContentLoaded', () => {
    initClock();
    initNavigation();
    initTasks();
    initNotes();
    initPomodoro();
    initAIChat();
});

// =========================================
// Navigation & Views
// =========================================
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    const viewSections = document.querySelectorAll('.view-section');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            // Remove active class from all nav items and views
            navItems.forEach(nav => nav.classList.remove('active'));
            viewSections.forEach(view => view.classList.remove('active'));

            // Add active class to clicked item and corresponding view
            item.classList.add('active');
            const targetId = item.getAttribute('data-target');
            document.getElementById(targetId).classList.add('active');
        });
    });
}

// =========================================
// Dashboard Clock
// =========================================
function initClock() {
    const timeDisplay = document.getElementById('current-time');
    const dateDisplay = document.getElementById('current-date');

    function updateTime() {
        const now = new Date();
        
        // Format Time (e.g., 2:30 PM)
        let hours = now.getHours();
        const ampm = hours >= 12 ? 'PM' : 'AM';
        hours = hours % 12;
        hours = hours ? hours : 12; 
        const minutes = now.getMinutes().toString().padStart(2, '0');
        timeDisplay.textContent = `${hours}:${minutes} ${ampm}`;
        
        // Format Date (e.g., Monday, January 1st)
        const options = { weekday: 'long', month: 'long', day: 'numeric' };
        dateDisplay.textContent = now.toLocaleDateString('en-US', options);
    }

    updateTime();
    setInterval(updateTime, 1000); // Update every second
}

// =========================================
// Tasks (To-Do List) Functionality
// =========================================
function initTasks() {
    fetchTasks();

    const addTaskForm = document.getElementById('add-task-form');
    const newTaskInput = document.getElementById('new-task-input');

    addTaskForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const title = newTaskInput.value.trim();
        if (!title) return;

        try {
            const response = await fetch('/api/tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title })
            });
            
            if (response.ok) {
                newTaskInput.value = '';
                fetchTasks(); // Refresh list
            }
        } catch (error) {
            console.error('Error adding task:', error);
        }
    });
    
    // AI Task Creation
    const aiTaskBtn = document.getElementById('ai-task-btn');
    const aiTaskForm = document.getElementById('ai-task-form');
    const aiTaskPrompt = document.getElementById('ai-task-prompt');
    const aiTaskSubmit = document.getElementById('ai-task-submit');
    const aiTaskCancel = document.getElementById('ai-task-cancel');
    const aiTaskStatus = document.getElementById('ai-task-status');
    
    aiTaskBtn.addEventListener('click', () => {
        aiTaskForm.style.display = 'block';
        aiTaskBtn.style.display = 'none';
        aiTaskPrompt.focus();
    });
    
    aiTaskCancel.addEventListener('click', () => {
        aiTaskForm.style.display = 'none';
        aiTaskBtn.style.display = 'inline-block';
        aiTaskPrompt.value = '';
        aiTaskStatus.textContent = '';
    });
    
    aiTaskSubmit.addEventListener('click', async () => {
        const prompt = aiTaskPrompt.value.trim();
        if (!prompt) return;
        
        aiTaskSubmit.disabled = true;
        aiTaskSubmit.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Creating...';
        aiTaskStatus.textContent = '';
        
        try {
            const response = await fetch('/api/ai/create-task', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt })
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                aiTaskStatus.textContent = `Task "${data.task.title}" created!`;
                aiTaskStatus.style.color = 'var(--success)';
                setTimeout(() => {
                    aiTaskForm.style.display = 'none';
                    aiTaskBtn.style.display = 'inline-block';
                    aiTaskPrompt.value = '';
                    aiTaskStatus.textContent = '';
                }, 1500);
                fetchTasks();
            } else {
                throw new Error(data.error || 'Failed to create task');
            }
        } catch (error) {
            aiTaskStatus.textContent = error.message;
            aiTaskStatus.style.color = 'var(--danger)';
        } finally {
            aiTaskSubmit.disabled = false;
            aiTaskSubmit.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Create';
        }
    });
}

async function fetchTasks() {
    const tasksList = document.getElementById('tasks-list');
    
    try {
        const response = await fetch('/api/tasks');
        const tasks = await response.json();
        
        tasksList.innerHTML = '';
        
        if (tasks.length === 0) {
            tasksList.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 20px;">No tasks yet. You are all caught up!</p>';
        } else {
            tasks.forEach(task => {
                const li = document.createElement('li');
                li.className = `task-item ${task.completed ? 'completed' : ''}`;
                
                li.innerHTML = `
                    <div class="task-content">
                        <div class="task-checkbox"><i class="fa-solid fa-check"></i></div>
                        <span class="task-title">${task.title}</span>
                    </div>
                    <button class="delete-btn"><i class="fa-solid fa-trash"></i></button>
                `;
                
                // Toggle completion
                li.querySelector('.task-content').addEventListener('click', () => toggleTask(task.id, !task.completed));
                
                // Delete task
                li.querySelector('.delete-btn').addEventListener('click', (e) => {
                    e.stopPropagation();
                    deleteTask(task.id);
                });
                
                tasksList.appendChild(li);
            });
        }
        
        updateTaskStats(tasks);
        
    } catch (error) {
        console.error('Error fetching tasks:', error);
        tasksList.innerHTML = '<p style="color: var(--danger);">Failed to load tasks.</p>';
    }
}

async function toggleTask(id, completed) {
    try {
        const response = await fetch(`/api/tasks/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ completed })
        });
        if (response.ok) fetchTasks();
    } catch (error) {
        console.error('Error updating task:', error);
    }
}

async function deleteTask(id) {
    try {
        const response = await fetch(`/api/tasks/${id}`, { method: 'DELETE' });
        if (response.ok) fetchTasks();
    } catch (error) {
        console.error('Error deleting task:', error);
    }
}

function updateTaskStats(tasks) {
    const total = tasks.length;
    const completed = tasks.filter(t => t.completed).length;
    const percentage = total === 0 ? 0 : Math.round((completed / total) * 100);
    
    document.getElementById('task-completion-text').textContent = `${percentage}%`;
    document.getElementById('task-summary-text').textContent = `${completed} of ${total} tasks completed`;
}

// =========================================
// Notes Functionality
// =========================================
function initNotes() {
    fetchNotes();

    const addNoteForm = document.getElementById('add-note-form');

    addNoteForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const titleInput = document.getElementById('new-note-title');
        const contentInput = document.getElementById('new-note-content');
        const colorInput = document.getElementById('note-color');
        
        const title = titleInput.value.trim();
        if (!title) return;

        try {
            const response = await fetch('/api/notes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title,
                    content: contentInput.value,
                    color: colorInput.value
                })
            });
            
            if (response.ok) {
                titleInput.value = '';
                contentInput.value = '';
                colorInput.value = '#6366f1';
                fetchNotes();
            }
        } catch (error) {
            console.error('Error adding note:', error);
        }
    });
}

async function fetchNotes() {
    const notesList = document.getElementById('notes-list');
    
    try {
        const response = await fetch('/api/notes');
        const notes = await response.json();
        
        notesList.innerHTML = '';
        
        if (notes.length === 0) {
            notesList.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 20px;">No notes yet. Create your first note!</p>';
        } else {
            notes.forEach(note => {
                const noteCard = document.createElement('div');
                noteCard.className = 'note-card';
                noteCard.style.borderLeftColor = note.color;
                
                noteCard.innerHTML = `
                    <div class="note-header">
                        <h3 class="note-title">${escapeHtml(note.title)}</h3>
                        <div class="note-actions">
                            <button class="note-edit-btn" data-id="${note.id}"><i class="fa-solid fa-pen"></i></button>
                            <button class="note-delete-btn" data-id="${note.id}"><i class="fa-solid fa-trash"></i></button>
                        </div>
                    </div>
                    <p class="note-content">${escapeHtml(note.content) || 'No content'}</p>
                `;
                
                // Delete note
                noteCard.querySelector('.note-delete-btn').addEventListener('click', () => deleteNote(note.id));
                
                // Edit note (inline)
                noteCard.querySelector('.note-edit-btn').addEventListener('click', () => editNote(note));
                
                notesList.appendChild(noteCard);
            });
        }
        
    } catch (error) {
        console.error('Error fetching notes:', error);
        notesList.innerHTML = '<p style="color: var(--danger);">Failed to load notes.</p>';
    }
}

async function deleteNote(id) {
    try {
        const response = await fetch(`/api/notes/${id}`, { method: 'DELETE' });
        if (response.ok) fetchNotes();
    } catch (error) {
        console.error('Error deleting note:', error);
    }
}

function editNote(note) {
    const noteCard = document.querySelector(`.note-card`);
    const title = prompt('Edit title:', note.title);
    if (title === null) return;
    
    const content = prompt('Edit content:', note.content);
    
    fetch(`/api/notes/${note.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, content })
    }).then(res => {
        if (res.ok) fetchNotes();
    });
}

// =========================================
// Pomodoro Timer Functionality
// =========================================
function initPomodoro() {
    const timeDisplay = document.getElementById('pomodoro-time');
    const startBtn = document.getElementById('pomodoro-start');
    const pauseBtn = document.getElementById('pomodoro-pause');
    const resetBtn = document.getElementById('pomodoro-reset');
    const modeBtns = document.querySelectorAll('.timer-mode-btn');
    
    let timeLeft = 25 * 60; // 25 minutes in seconds
    let timerInterval = null;
    let isRunning = false;
    let currentMode = 'work';
    
    let sessionsCompleted = 0;
    let totalFocusTime = 0;
    
    function updateDisplay() {
        const minutes = Math.floor(timeLeft / 60);
        const seconds = timeLeft % 60;
        timeDisplay.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        document.title = `${timeDisplay.textContent} - Pomodoro`;
    }
    
    function startTimer() {
        if (isRunning) return;
        
        isRunning = true;
        startBtn.style.display = 'none';
        pauseBtn.style.display = 'inline-block';
        
        timerInterval = setInterval(() => {
            timeLeft--;
            updateDisplay();
            
            if (timeLeft <= 0) {
                clearInterval(timerInterval);
                isRunning = false;
                
                // Play notification sound
                playNotificationSound();
                
                if (currentMode === 'work') {
                    sessionsCompleted++;
                    totalFocusTime += 25;
                    document.getElementById('sessions-completed').textContent = sessionsCompleted;
                    document.getElementById('total-focus-time').textContent = totalFocusTime;
                    alert('Great job! Time for a break.');
                } else {
                    alert('Break is over! Ready to focus?');
                }
                
                startBtn.style.display = 'inline-block';
                pauseBtn.style.display = 'none';
                
                // Reset to current mode duration
                const modeBtn = document.querySelector(`.timer-mode-btn[data-mode="${currentMode}"]`);
                if (modeBtn) {
                    timeLeft = parseInt(modeBtn.dataset.duration) * 60;
                }
                updateDisplay();
            }
        }, 1000);
    }
    
    function pauseTimer() {
        clearInterval(timerInterval);
        isRunning = false;
        startBtn.style.display = 'inline-block';
        pauseBtn.style.display = 'none';
    }
    
    function resetTimer() {
        pauseTimer();
        const modeBtn = document.querySelector(`.timer-mode-btn[data-mode="${currentMode}"]`);
        if (modeBtn) {
            timeLeft = parseInt(modeBtn.dataset.duration) * 60;
        }
        updateDisplay();
    }
    
    function playNotificationSound() {
        // Create a simple beep using Web Audio API
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 800;
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.5);
        } catch (e) {
            console.log('Audio not supported');
        }
    }
    
    startBtn.addEventListener('click', startTimer);
    pauseBtn.addEventListener('click', pauseTimer);
    resetBtn.addEventListener('click', resetTimer);
    
    modeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            if (isRunning) pauseTimer();
            
            modeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            currentMode = btn.dataset.mode;
            timeLeft = parseInt(btn.dataset.duration) * 60;
            updateDisplay();
        });
    });
    
    updateDisplay();
}

// =========================================
// AI Chatbot Functionality
// =========================================
function initAIChat() {
    const apiKeyForm = document.getElementById('api-key-form');
    const apiKeyInput = document.getElementById('api-key-input');
    const apiKeyStatus = document.getElementById('api-key-status');
    const apiSubmitBtn = document.getElementById('api-key-submit');
    
    const setupContainer = document.getElementById('ai-setup-container');
    const chatContainer = document.getElementById('ai-chat-container');
    
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatHistory = document.getElementById('chat-history');

    // 0. Check if AI is already configured on server load
    async function checkStatus() {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();
            if (data.ai_ready) {
                setupContainer.style.display = 'none';
                chatContainer.style.display = 'flex';
            }
        } catch (e) {
            console.error("Could not check AI status", e);
        }
    }
    checkStatus();

    // 1. Handle API Key Submission
    apiKeyForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const apiKey = apiKeyInput.value.trim();
        if (!apiKey) return;
        
        apiSubmitBtn.disabled = true;
        apiSubmitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Connecting...';
        apiKeyStatus.textContent = '';
        apiKeyStatus.style.color = 'var(--text-secondary)';

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ apiKey })
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                // Success! Switch to chat UI
                setupContainer.style.display = 'none';
                chatContainer.style.display = 'flex';
                // Focus the chat input
                setTimeout(() => chatInput.focus(), 100);
            } else {
                throw new Error(data.error || 'Failed to connect');
            }
        } catch (error) {
            apiKeyStatus.textContent = error.message;
            apiKeyStatus.style.color = 'var(--danger)';
            apiSubmitBtn.disabled = false;
            apiSubmitBtn.innerHTML = 'Connect AI';
        }
    });

    // 2. Handle Sending Chat Messages
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const message = chatInput.value.trim();
        if (!message) return;
        
        // Add user message to UI
        appendMessage('user', message);
        chatInput.value = '';
        
        // Show loading indicator
        const loadingId = appendLoadingMessage();
        
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });
            
            const data = await response.json();
            
            // Remove loading indicator
            document.getElementById(loadingId).remove();
            
            if (response.ok) {
                // We use generic text-formatting (primitive markdown-like handling)
                const formattedHtml = formatChatText(data.response);
                appendMessage('ai', formattedHtml, true);
            } else {
                appendMessage('ai', '⚠️ Error: ' + (data.error || 'Something went wrong.'), true);
            }
            
        } catch (error) {
            document.getElementById(loadingId).remove();
            appendMessage('ai', '⚠️ Connection error. Make sure the backend is running.', true);
        }
    });

    function appendMessage(sender, content, isHtml = false) {
        const div = document.createElement('div');
        div.className = `message ${sender}-message`;
        
        const icon = sender === 'ai' ? '<i class="fa-solid fa-robot"></i>' : '<i class="fa-solid fa-user"></i>';
        
        div.innerHTML = `
            <div class="avatar">${icon}</div>
            <div class="bubble">${isHtml ? content : escapeHtml(content)}</div>
        `;
        
        chatHistory.appendChild(div);
        scrollToBottom();
    }
    
    function appendLoadingMessage() {
        const id = 'loading-' + Date.now();
        const div = document.createElement('div');
        div.id = id;
        div.className = `message ai-message`;
        div.innerHTML = `
            <div class="avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="bubble"><i class="fa-solid fa-circle-notch fa-spin"></i> Nova is thinking...</div>
        `;
        chatHistory.appendChild(div);
        scrollToBottom();
        return id;
    }

    function scrollToBottom() {
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
    
    // Simple helper to prevent XSS
    function escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
    
    // Simple helper to format Gemini output (bolding, newlines)
    function formatChatText(text) {
        let formatted = escapeHtml(text);
        // Replace **text** with <strong>text</strong>
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Replace *text* with <em>text</em>
        formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
        // Replace line breaks with <br>
        formatted = formatted.replace(/\n/g, '<br>');
        return formatted;
    }
}
