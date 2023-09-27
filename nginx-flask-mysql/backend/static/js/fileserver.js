var selected_file = null;

async function fetchFiles() {
    var username = await (await fetch('/username')).text();

    fetch('/files')
    .then(response => response.json())
    .then(response => {
        const name = username;
        file_data = response.children.filter((item) => item.name == name)

        const fileTree = $('#fileTree');
        fileTree.jstree({
            core: {
                data: file_data
            },
            plugins: ['types'],
            types: {
                'default': {
                    'icon': 'jstree-folder'
                },
                'file': {
                    'icon': 'jstree-file'
                }
            },
            themes: {
                'name': 'proton',
                'dots': false,
                'icons': true
            },
            multiple: false
        }).on('ready.jstree', function () {
            $(this).jstree('open_all');
        }).on('select_node.jstree', function (e, data) {
            if (data.node.type === 'file') {

                const file = data.node.data['path']
                selected_file = file
                // Call your callback function here with data.node.id or any other relevant information
            }
        });

    })
    .catch(error => {
        location.href = "/login";
    });
  }
  
  fetchFiles();



function uploadFile() {
    const input = document.createElement('input');
    input.type = 'file';

    input.onchange = () => {
        const file = input.files[0];

        if (file) {
            const formData = new FormData();
            formData.append('file', file);

            fetch('/upload', {
                method: 'POST',
                body: formData
            })
                .then(response => response.json())
                .then(data => alert(data.description));
        }
    }

    input.click();
}

function downloadFile() {
    window.location.href = '/download?file=' + selected_file;
}