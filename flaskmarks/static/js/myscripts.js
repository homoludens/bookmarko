document.addEventListener('DOMContentLoaded', function() {

    // Handle click increment for bookmarks
    document.querySelectorAll('.clickIncrement').forEach(function(element) {
        element.addEventListener('click', function() {
            var id = this.getAttribute('data-id');
            var url = this.getAttribute('data-url');
            
            fetch(url + '?' + new URLSearchParams({id: id}), {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                }
            })
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (data.status === 'success') {
                    return;
                }
            })
            .catch(function(error) {
                console.error('Error:', error);
            });
        });
    });

    // Handle delete confirmation
    document.querySelectorAll('.delete').forEach(function(element) {
        element.addEventListener('click', function(event) {
            if (!confirm('Are you sure you want to delete this?')) {
                event.preventDefault();
                return false;
            }
            return true;
        });
    });

});
