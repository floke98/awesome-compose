
document.getElementById("login-form-submit").addEventListener("click", (e) => {
    e.preventDefault();
    const login_url = '/login';

    const data = { username: document.getElementById("login-form").username.value,
                   password: document.getElementById("login-form").password.value
                 };

    fetch(login_url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
        .then(response => response.json()) // wait for response
        .then(data => {
            if(data.status === 'success') {
                // handle success
                location.href = "/welcome";
            } else {
                document.getElementById("username-field").placeholder="Invalid"; 
                document.getElementById("username-field").setAttribute('aria-invalid', "true");
                document.getElementById("password-field").placeholder="Invalid"; 
                document.getElementById("password-field").setAttribute('aria-invalid', "true");
            }
        })
    .catch(error => {
    });
})