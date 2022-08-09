const lat = Number(document.getElementById('lat').value);
const lon = Number(document.getElementById('lon').value);
const zoom = 13;
const map = L.map('map').setView([lat, lon], 13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap'
}).addTo(map);
L.marker([lat, lon]).addTo(map)
    .openPopup();