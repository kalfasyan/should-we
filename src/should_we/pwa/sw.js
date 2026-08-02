// ponytail: passthrough only — data lives on the server, offline is useless.
// This SW exists solely to satisfy browsers' installability requirement.
// Add caching here only if offline voting ever becomes a requirement.
self.addEventListener('fetch', () => {});
