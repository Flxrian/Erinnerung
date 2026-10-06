// Minimaler Service Worker – nur nötig, damit Chrome/Android die Seite als
// "installierbare App" erkennt. Kein echtes Offline-Caching, da Jarvis
// sowieso eine Verbindung zum PC-Server braucht.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', () => self.clients.claim());
self.addEventListener('fetch', () => {}); // keine Offline-Logik nötig
