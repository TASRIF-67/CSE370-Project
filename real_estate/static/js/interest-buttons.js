$(document).ready(function() {
    // Target both interest buttons from homepage and detail page
    $('.interest-btn, #interest-button').click(function(e) {
        e.preventDefault();  // Stop normal link behavior
        
        var button = $(this);
        var url = button.attr('href');  // Get URL from href attribute
        var heartIcon = button.find('i');
        
        // Determine if we're adding or removing based on the current URL
        var isAddingInterest = url.includes('express_interest');
        console.log("Action:", isAddingInterest ? "Adding interest" : "Removing interest");
        
        // Immediately update UI for better user experience
        if (isAddingInterest) {
            // Visual update first (will be reverted if AJAX fails)
            heartIcon.removeClass('far').addClass('fas text-danger');
            button.addClass('heart-active');
        } else {
            // Visual update first (will be reverted if AJAX fails)
            heartIcon.removeClass('fas text-danger').addClass('far');
            button.removeClass('heart-active');
        }
        
        // Make the AJAX request
        $.ajax({
            url: url,
            type: 'POST',
            headers: { 
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'  // Match your backend check
            },
            success: function(response) {
                console.log("Response:", response);
                
                if (response.status === 'success' || 
                    (response.status === 'warning' && response.message.includes('already expressed'))) {
                    
                    // Update button URL for next action
                    if (isAddingInterest) {
                        var newUrl = url.replace('express_interest', 'remove_interest');
                        button.attr('href', newUrl);
                    } else {
                        var newUrl = url.replace('remove_interest', 'express_interest');
                        button.attr('href', newUrl);
                    }
                } else {
                    // Revert UI changes if there was an error
                    if (isAddingInterest) {
                        heartIcon.removeClass('fas text-danger').addClass('far');
                        button.removeClass('heart-active');
                    } else {
                        heartIcon.removeClass('far').addClass('fas text-danger');
                        button.addClass('heart-active');
                    }
                    alert(response.message);
                }
            },
            error: function(xhr) {
                console.error("Error:", xhr.responseText);
                
                // Revert UI changes on error
                if (isAddingInterest) {
                    heartIcon.removeClass('fas text-danger').addClass('far');
                    button.removeClass('heart-active');
                } else {
                    heartIcon.removeClass('far').addClass('fas text-danger');
                    button.addClass('heart-active');
                }
                
                alert('An error occurred. Please try again later.');
            }
        });
    });
    
    // Function to get CSRF token from cookies or meta tag
    function getCsrfToken() {
        // Try to get from cookie first
        var csrfToken = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                if (cookie.substring(0, 'csrftoken='.length) === 'csrftoken=') {
                    csrfToken = decodeURIComponent(cookie.substring('csrftoken='.length));
                    break;
                }
            }
        }
        
        // If not found in cookie, look for the meta tag
        if (!csrfToken) {
            var meta = document.querySelector('meta[name="csrf-token"]');
            if (meta) {
                csrfToken = meta.getAttribute('content');
            }
        }
        
        return csrfToken;
    }
});