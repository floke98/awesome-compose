
document.getElementById("search-form-submit").addEventListener("click", (e) => {
    e.preventDefault();
    const url = '/search';
    const data = { search_id: document.getElementById("search-form").search_id.value };
    console.log(data);

    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
        .then(response => response.json()) // wait for response
        .then(data => {
            if(data.status === 'success') {
                // handle success
                location.href = "/" + data.id;
            } else {
                document.getElementById("search-field").placeholder="Not Found";
                document.getElementById("search-field").setAttribute('aria-invalid', "true");
            }
        })
    .catch(error => {
    });
})

document.getElementById("add-form-submit").addEventListener("click", (e) => {
    e.preventDefault();
    const url = '/add';
    const data = { add_id: document.getElementById("add-form").add_id.value };
    console.log(data);

    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
        .then(response => response.json()) // wait for response
        .then(data => {
            if(data.status === 'success') {
                // handle success
                location.href = "/" + data.id;
            } else if(data.status === 'exists') {
                // handle existend element
                location.href = "/" + data.id;
            } else {
                document.getElementById("add-field").placeholder="Fail";
                document.getElementById("add-field").setAttribute('aria-invalid', "true");
            }
        })
    .catch(error => {
    });
})

document.getElementById("save-submit").addEventListener("click", (e) => {
    e.preventDefault();
    const url = '/save';
    fetch(url)
        .then(response => {
        //handle response
        console.log(response);
      })
})

document.getElementById("undo-submit").addEventListener("click", (e) => {
    e.preventDefault();
    const url = '/undo';
    fetch(url)
        .then(response => {
        //handle response
        console.log(response);
      })
})