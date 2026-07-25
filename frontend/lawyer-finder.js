// lawyer-finder.js

// ── LAWYER FINDER — Render results list ────────────────
function renderLawyerResults(data, searchLabel) {
    var container = document.getElementById('lawyer-results-container');

    if (!data.success || data.count === 0) {
        container.innerHTML =
            '<div class="lawyer-status-text">'
            + (data.message ||
             'No advocates found near ' + searchLabel +
             '. Try the nearest major city or contact ' +
             'your local Bar Council.') +
            '</div>';
        return;
    }

    var html = '';
    data.lawyers.forEach(function(lawyer) {
        var ratingHtml = lawyer.rating
            ? '<span class="rating-stars">★</span> '
              + lawyer.rating
              + ' <span style="color:var(--text-muted);">'
              + '(' + lawyer.total_ratings + ' reviews)'
              + '</span>'
            : '<span style="color:var(--text-muted);">'
              + 'No reviews yet</span>';

        var openBadge =
            lawyer.open_now === true
            ? '<span class="open-badge open">'
              + 'Open Now</span>'
            : lawyer.open_now === false
            ? '<span class="open-badge closed">'
              + 'Closed</span>'
            : '';

        html +=
            '<div class="lawyer-card">'
            + '<div class="lawyer-card-name">'
            + lawyer.name
            + '</div>'
            + '<div class="lawyer-card-address">'
            + lawyer.address
            + '</div>'
            + '<div class="lawyer-card-meta">'
            + '<span class="lawyer-rating">'
            + ratingHtml
            + '</span>'
            + openBadge
            + '<a href="' + lawyer.maps_url
            + '" target="_blank"'
            + ' rel="noopener noreferrer"'
            + ' class="lawyer-maps-link">'
            + 'View on Google Maps →'
            + '</a>'
            + '</div>'
            + '</div>';
    });

    container.innerHTML = html;
}

// ── LAWYER FINDER — Loading state helper ───────────────
function setLawyerLoading(isLoading, label) {
    var cityBtn  = document.getElementById('find-lawyers-btn');
    var locBtn   = document.getElementById('use-location-btn');
    var container = document.getElementById('lawyer-results-container');

    if (isLoading) {
        cityBtn.disabled = true;
        locBtn.disabled  = true;
        cityBtn.textContent = 'SEARCHING...';
        container.innerHTML =
            '<div class="lawyer-status-text">'
            + 'Searching for trademark advocates near '
            + label + '...'
            + '</div>';
    } else {
        cityBtn.disabled = false;
        locBtn.disabled  = false;
        cityBtn.textContent = 'SEARCH';
    }
}

// ── LAWYER FINDER — Search by typed city name ──────────
export async function searchByCity() {
    var input = document.getElementById('lawyer-city-input');
    var city = input.value.trim();

    if (!city) {
        input.style.borderColor = 'var(--red)';
        setTimeout(function() {
            input.style.borderColor = 'var(--border)';
        }, 2000);
        return;
    }

    setLawyerLoading(true, city);

    try {
        var res = await fetch(
            '/find-lawyers?city='
            + encodeURIComponent(city)
            + '&dispute_type=trademark'
        );
        var data = await res.json();
        renderLawyerResults(data, city);
    } catch (err) {
        document.getElementById('lawyer-results-container').innerHTML =
            '<div class="lawyer-status-text">'
            + 'Search failed. Please check your connection and try again.'
            + '</div>';
    } finally {
        setLawyerLoading(false, city);
    }
}

// ── LAWYER FINDER — Use browser current location ───────
export function useCurrentLocation() {
    var errorDiv = document.getElementById('location-error-msg');
    errorDiv.style.display = 'none';

    if (!navigator.geolocation) {
        errorDiv.textContent =
            'Your browser does not support location access. Please enter your city below.';
        errorDiv.style.display = 'block';
        return;
    }

    var locBtn = document.getElementById('use-location-btn');
    locBtn.disabled = true;
    locBtn.textContent = 'GETTING LOCATION...';

    document.getElementById('lawyer-results-container').innerHTML =
        '<div class="lawyer-status-text">'
        + 'Accessing your location...'
        + '</div>';

    navigator.geolocation.getCurrentPosition(
        async function(position) {
            var lat = position.coords.latitude;
            var lng = position.coords.longitude;

            document.getElementById('lawyer-results-container').innerHTML =
                '<div class="lawyer-status-text">'
                + 'Finding advocates near your location...'
                + '</div>';

            try {
                var res = await fetch(
                    '/find-lawyers-by-location'
                    + '?lat=' + lat
                    + '&lng=' + lng
                    + '&dispute_type=trademark'
                );
                var data = await res.json();
                renderLawyerResults(data, 'your current location');
            } catch (err) {
                document.getElementById('lawyer-results-container').innerHTML =
                    '<div class="lawyer-status-text">'
                    + 'Search failed. Please enter your city below.'
                    + '</div>';
            } finally {
                locBtn.disabled = false;
                locBtn.innerHTML =
                    '<svg width="14" height="14" '
                    + 'viewBox="0 0 24 24" fill="none" '
                    + 'stroke="currentColor" '
                    + 'stroke-width="2" '
                    + 'stroke-linecap="round" '
                    + 'stroke-linejoin="round">'
                    + '<circle cx="12" cy="12" r="3">'
                    + '</circle>'
                    + '<line x1="12" y1="2" '
                    + 'x2="12" y2="6"></line>'
                    + '<line x1="12" y1="18" '
                    + 'x2="12" y2="22"></line>'
                    + '<line x1="2" y1="12" '
                    + 'x2="6" y2="12"></line>'
                    + '<line x1="18" y1="12" '
                    + 'x2="22" y2="12"></line>'
                    + '</svg>'
                    + ' USE MY CURRENT LOCATION';
            }
        },
        function(error) {
            locBtn.disabled = false;
            locBtn.innerHTML =
                '<svg width="14" height="14" '
                + 'viewBox="0 0 24 24" fill="none" '
                + 'stroke="currentColor" '
                + 'stroke-width="2" '
                + 'stroke-linecap="round" '
                + 'stroke-linejoin="round">'
                + '<circle cx="12" cy="12" r="3">'
                + '</circle>'
                + '<line x1="12" y1="2" '
                + 'x2="12" y2="6"></line>'
                + '<line x1="12" y1="18" '
                + 'x2="12" y2="22"></line>'
                + '<line x1="2" y1="12" '
                + 'x2="6" y2="12"></line>'
                + '<line x1="18" y1="12" '
                + 'x2="22" y2="12"></line>'
                + '</svg>'
                + ' USE MY CURRENT LOCATION';

            errorDiv.textContent =
                'Location access denied. Please enter your city below.';
            errorDiv.style.display = 'block';

            document.getElementById('lawyer-results-container').innerHTML = '';
        },
        {
            timeout: 10000,
            maximumAge: 60000,
            enableHighAccuracy: false
        }
    );
}

export function initLawyerFinder() {
    window.searchByCity = searchByCity;
    window.useCurrentLocation = useCurrentLocation;
}
