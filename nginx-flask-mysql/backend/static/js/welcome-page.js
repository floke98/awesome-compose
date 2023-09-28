
fetch('/staff')
    .then(response => response.json())
    .then(response => {
        document.getElementById('vor1').innerHTML = response.at(0).firstname + " " + response.at(0).surname;
        document.getElementById('vor2').innerHTML = response.at(1).firstname + " " + response.at(1).surname;
        document.getElementById('vor3').innerHTML = response.at(2).firstname + " " + response.at(2).surname;

        document.getElementById('mail1').innerHTML = response.at(0).email;
        document.getElementById('mail2').innerHTML = response.at(1).email;
        document.getElementById('mail3').innerHTML = response.at(2).email;
    })
    .catch(error => {
        location.href = "/login";
    });

fetch('/profile')
    .then(response => response.json())
    .then(response => {
        
        document.getElementById('greeting').innerHTML = "Hello " + response.firstname + "!";

        if (response.file_access_rights === true)
        {
            document.getElementById('file-access').style.display = '';
        }
    })
    .catch(error => {
        location.href = "/login";
    });
