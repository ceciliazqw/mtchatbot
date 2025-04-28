document.addEventListener('DOMContentLoaded', function() {
    console.log("Script loaded and DOM fully parsed.");
    
    // Function to toggle login modal visibility
    function toggleLoginModal() {
        if (localStorage.getItem("token")) {
            console.log("User already logged in. Redirecting to chatbot page.");
            window.location.href = "chatbot.html";
            return;
        }
        console.log("toggleLoginModal called");
        const loginModal = document.getElementById('login-modal');
        if (!loginModal) {
            console.error("login-modal element not found!");
            return;
        }
        if (loginModal.classList.contains('hidden')) {
            loginModal.classList.remove('hidden');
            loginModal.classList.add('show');
            console.log("Login modal shown");
        } else {
            loginModal.classList.remove('show');
            loginModal.classList.add('hidden');
            console.log("Login modal hidden");
        }
    }
    window.toggleLoginModal = toggleLoginModal;
    
    // Login process: when the login button is clicked, perform login and display chatbot messenger if successful
    const loginBtn = document.getElementById('login-btn');
    loginBtn.addEventListener('click', function() {
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        console.log("Attempting login for:", username);
        
        // Alert to verify login button click
        alert("Login attempt started for " + username);
        
        fetch('https://mtchatbot-932847276366.asia-east1.run.app/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: username, password: password })
        })
        .then(response => {
            console.log("Response status:", response.status);
            return response.json();
        })
        .then(data => {
            console.log("Login response data:", data);
            if (data.token) {
                alert("Login successful!");
                localStorage.setItem('token', data.token);
                localStorage.setItem('username', username);
                window.location.href = "chatbot.html";
                console.log("Redirecting to chatbot.html");
            } else {
                alert("Login failed: " + data.error);
            }
        })
        .catch(error => {
            console.error("Login error:", error);
            alert("Login error: " + error);
        });
    });
});