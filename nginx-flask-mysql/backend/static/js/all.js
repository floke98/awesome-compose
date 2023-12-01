/*
function removePart(remId) {
    const url = '/all';
    const data = { rem_id : remId};
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
                location.href = "/all"; // reload
            } else {
                // something went wrong
            }
        })
    .catch(error => {
    });
}
*/
