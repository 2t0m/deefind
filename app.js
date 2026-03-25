let currentAudio = null;
        let searchTimeout = null;
        let currentTab = 'tracks';

        const searchInput = document.getElementById('search-input');
        const resultsDiv = document.getElementById('results');
        const notification = document.getElementById('notification');
        const clearBtn = document.getElementById('clear-btn');
        const historyToggle = document.getElementById('history-toggle');
        const historyPanel = document.getElementById('history-panel');
        const historyClose = document.getElementById('history-close');
        const historyList = document.getElementById('history-list');
        const historyClear = document.getElementById('history-clear');
        const tabs = document.querySelectorAll('.tab');

        // Download history management
        let downloadHistory = JSON.parse(localStorage.getItem('downloadHistory') || '[]');

        // Handle clear button
        searchInput.addEventListener('input', function() {
            if (this.value.length > 0) {
                clearBtn.classList.add('visible');
            } else {
                clearBtn.classList.remove('visible');
            }
        });

        clearBtn.addEventListener('click', function() {
            searchInput.value = '';
            clearBtn.classList.remove('visible');
            resultsDiv.innerHTML = '';
            searchInput.focus();
        });

        // Handle tabs
        tabs.forEach(tab => {
            tab.addEventListener('click', function() {
                tabs.forEach(t => t.classList.remove('active'));
                this.classList.add('active');
                currentTab = this.dataset.tab;
                
                // Trigger search with current query
                const query = searchInput.value.trim();
                performSearch(query);
            });
        });

        function performSearch(query) {
            if (!query && query !== '') {
                resultsDiv.innerHTML = '';
                return;
            }

            resultsDiv.innerHTML = '<div class="loading">Searching...</div>';

            let endpoint = '/search';
            if (currentTab === 'albums') {
                endpoint = '/search_albums';
            } else if (currentTab === 'playlists') {
                endpoint = '/search_playlists';
            }

            fetch(`${endpoint}?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    displayResults(data.data || [], currentTab);
                })
                .catch(error => {
                    console.error('Error:', error);
                    showNotification('Search error', true);
                });
        }

        // History panel toggle
        historyToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            historyPanel.classList.add('open');
            renderHistory();
        });

        historyClose.addEventListener('click', function() {
            historyPanel.classList.remove('open');
        });

        // Close history panel when clicking outside
        document.addEventListener('click', function(e) {
            if (historyPanel.classList.contains('open') && 
                !historyPanel.contains(e.target) && 
                !historyToggle.contains(e.target)) {
                historyPanel.classList.remove('open');
            }
        });

        historyClear.addEventListener('click', function() {
            if (confirm('Clear all download history?')) {
                downloadHistory = [];
                localStorage.setItem('downloadHistory', JSON.stringify(downloadHistory));
                renderHistory();
            }
        });

        // Render history list
        function renderHistory() {
            if (downloadHistory.length === 0) {
                historyList.innerHTML = '<div class="history-empty">No downloads yet</div>';
                return;
            }

            historyList.innerHTML = downloadHistory.map(item => `
                <div class="history-item">
                    <img src="${item.cover}" alt="${item.title}" class="history-cover">
                    <div class="history-info">
                        <div class="history-track-title">${item.title}</div>
                        <div class="history-track-artist">${item.artist}</div>
                        <div class="history-time">${formatTime(item.timestamp)}</div>
                    </div>
                </div>
            `).join('');
        }

        // Format timestamp
        function formatTime(timestamp) {
            const date = new Date(timestamp);
            const now = new Date();
            const diff = now - date;
            const minutes = Math.floor(diff / 60000);
            const hours = Math.floor(diff / 3600000);
            const days = Math.floor(diff / 86400000);

            if (minutes < 1) return 'Just now';
            if (minutes < 60) return `${minutes}m ago`;
            if (hours < 24) return `${hours}h ago`;
            if (days < 7) return `${days}d ago`;
            return date.toLocaleDateString();
        }

        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();

            if (query.length < 2) {
                resultsDiv.innerHTML = '';
                return;
            }

            searchTimeout = setTimeout(() => {
                performSearch(query);
            }, 300);
        });

        // Load chart on initial page load
        function loadChart() {
            resultsDiv.innerHTML = '<div class="loading">Loading chart...</div>';
            performSearch('');
        }

        // Load chart on page load
        window.addEventListener('load', () => {
            loadChart();
        });

        function displayResults(items, type = 'tracks') {
            if (items.length === 0) {
                resultsDiv.innerHTML = '<div class="no-results">No results found</div>';
                return;
            }

            if (type === 'tracks') {
                resultsDiv.innerHTML = items.map(track => `
                    <div class="track-card">
                        <div class="track-header">
                            <img src="${track.album.cover_medium}" alt="${track.title}" class="track-cover">
                            <div class="track-info">
                                <div class="track-title">${track.title}</div>
                                <div class="track-artist">${track.artist.name}</div>
                                <div class="track-album">${track.album.title}</div>
                            </div>
                        </div>
                        <div class="track-actions">
                            <button class="btn-preview" onclick="togglePreview('${track.preview}', this)" title="Preview">
                                <i class="fas fa-play"></i>
                            </button>
                            <button class="btn-send" onclick="downloadContent('${track.link}', this, '${track.title.replace(/'/g, "\\'").replace(/"/g, '&quot;')}', '${track.artist.name.replace(/'/g, "\\'").replace(/"/g, '&quot;')}', '${track.album.cover_small}', 'track')" title="Download">
                                <i class="fas fa-download"></i>
                            </button>
                        </div>
                    </div>
                `).join('');
            } else if (type === 'albums') {
                resultsDiv.innerHTML = items.map(album => `
                    <div class="track-card">
                        <div class="track-header">
                            <img src="${album.cover_medium}" alt="${album.title}" class="track-cover">
                            <div class="track-info">
                                <div class="track-title">${album.title}</div>
                                <div class="track-artist">${album.artist.name}</div>
                                <div class="track-album">${album.nb_tracks || '?'} tracks</div>
                            </div>
                        </div>
                        <div class="track-actions">
                            <button class="btn-view" onclick="viewAlbumTracks(${album.id}, '${album.title.replace(/'/g, "\\'").replace(/"/g, '&quot;')}', '${album.artist.name.replace(/'/g, "\\'").replace(/"/g, '&quot;')}', '${album.cover_medium}', '${album.link}')" title="View Tracks">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button class="btn-send" onclick="downloadContent('${album.link}', this, '${album.title.replace(/'/g, "\\'").replace(/"/g, '&quot;')}', '${album.artist.name.replace(/'/g, "\\'").replace(/"/g, '&quot;')}', '${album.cover_small}', 'album')" title="Download Album">
                                <i class="fas fa-download"></i>
                            </button>
                        </div>
                    </div>
                `).join('');
            } else if (type === 'playlists') {
                resultsDiv.innerHTML = items.map(playlist => `
                    <div class="track-card">
                        <div class="track-header">
                            <img src="${playlist.picture_medium}" alt="${playlist.title}" class="track-cover">
                            <div class="track-info">
                                <div class="track-title">${playlist.title}</div>
                                <div class="track-artist">${playlist.user?.name || 'Deezer'}</div>
                                <div class="track-album">${playlist.nb_tracks || '?'} tracks</div>
                            </div>
                        </div>
                        <div class="track-actions">
                            <button class="btn-view" onclick="viewPlaylistTracks(${playlist.id}, '${playlist.title.replace(/'/g, "\\'").replace(/"/g, '&quot;')}', '${playlist.user?.name || 'Deezer'}', '${playlist.picture_medium}', '${playlist.link}')" title="View Tracks">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button class="btn-send" onclick="downloadContent('${playlist.link}', this, '${playlist.title.replace(/'/g, "\\'").replace(/"/g, '&quot;')}', '${playlist.user?.name || 'Deezer'}', '${playlist.picture_small}', 'playlist')" title="Download Playlist">
                                <i class="fas fa-download"></i>
                            </button>
                        </div>
                    </div>
                `).join('');
            }
        }

        function togglePreview(previewUrl, button) {
            if (currentAudio && !currentAudio.paused) {
                currentAudio.pause();
                currentAudio = null;
                document.querySelectorAll('.btn-preview').forEach(btn => {
                    btn.textContent = '▶';
                    btn.classList.remove('playing');
                });
                return;
            }

            if (currentAudio) {
                currentAudio.pause();
            }

            currentAudio = new Audio(previewUrl);
            currentAudio.play();

            document.querySelectorAll('.btn-preview').forEach(btn => {
                btn.innerHTML = '<i class="fas fa-play"></i>';
                btn.classList.remove('playing');
            });

            button.innerHTML = '<i class="fas fa-pause"></i>';
            button.classList.add('playing');

            currentAudio.addEventListener('ended', () => {
                button.innerHTML = '<i class="fas fa-play"></i>';
                button.classList.remove('playing');
            });
        }

        function downloadContent(link, button, title, artist, cover, type = 'track') {
            // Add loading animation
            button.classList.add('loading');
            
            fetch('/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    link: link,
                    title: title,
                    artist: artist
                })
            })
            .then(response => response.json())
            .then(data => {
                // Remove loading animation
                button.classList.remove('loading');
                
                if (data.success) {
                    // Add to history
                    downloadHistory.unshift({
                        title: title,
                        artist: artist,
                        cover: cover,
                        timestamp: Date.now()
                    });
                    // Keep only last 50 items
                    downloadHistory = downloadHistory.slice(0, 50);
                    localStorage.setItem('downloadHistory', JSON.stringify(downloadHistory));
                    
                    const typeLabel = type === 'album' ? 'Album' : type === 'playlist' ? 'Playlist' : 'Track';
                    showNotification(`✓ ${typeLabel} download started`);
                } else if (data.error === 'already_exists') {
                    showNotification('⚠ ' + data.message, true);
                } else {
                    showNotification('✗ Error: ' + (data.error || 'Unknown'), true);
                }
            })
            .catch(error => {
                // Remove loading animation on error
                button.classList.remove('loading');
                console.error('Error:', error);
                showNotification('✗ Download failed', true);
            });
        }

        // Album and Playlist viewer functions
        let currentContentLink = '';
        let currentContentType = '';
        
        function viewAlbumTracks(albumId, title, artist, cover, link) {
            currentContentLink = link;
            currentContentType = 'album';
            
            document.getElementById('modal-cover').src = cover;
            document.getElementById('modal-title').textContent = title;
            document.getElementById('modal-artist').textContent = artist;
            
            const trackListDiv = document.getElementById('modal-track-list');
            trackListDiv.innerHTML = '<div style="text-align: center; padding: 20px;">Loading...</div>';
            
            document.getElementById('modal-overlay').style.display = 'flex';
            
            fetch(`/album_tracks/${albumId}`)
                .then(response => response.json())
                .then(data => {
                    const tracks = data.tracks?.data || [];
                    if (tracks.length > 0) {
                        trackListDiv.innerHTML = tracks.map((track, index) => `
                            <div class="modal-track-item">
                                <div class="modal-track-number">${index + 1}</div>
                                <div class="modal-track-info">
                                    <div class="modal-track-title">${track.title}</div>
                                    <div class="modal-track-artist">${track.artist?.name || artist}</div>
                                </div>
                                <div class="modal-track-duration">${formatDuration(track.duration)}</div>
                                <div class="modal-track-actions">
                                    <button class="btn-track-action" onclick="playPreview('${track.preview}', this)" title="Preview">
                                        <i class="fas fa-play"></i>
                                    </button>
                                    <button class="btn-track-action" onclick="downloadTrack('https://www.deezer.com/track/${track.id}', '${track.title.replace(/'/g, "\\'").replace(/"/g, '&quot;')}', '${track.artist?.name.replace(/'/g, "\\'").replace(/"/g, '&quot;')}', '${track.album?.cover_small || cover}')" title="Download">
                                        <i class="fas fa-download"></i>
                                    </button>
                                </div>
                            </div>
                        `).join('');
                    } else {
                        trackListDiv.innerHTML = '<div style="text-align: center; padding: 20px;">No tracks found</div>';
                    }
                })
                .catch(error => {
                    console.error('Error loading album tracks:', error);
                    trackListDiv.innerHTML = '<div style="text-align: center; padding: 20px; color: #ef4444;">Error loading tracks</div>';
                });
        }
        
        function viewPlaylistTracks(playlistId, title, creator, cover, link) {
            currentContentLink = link;
            currentContentType = 'playlist';
            
            document.getElementById('modal-cover').src = cover;
            document.getElementById('modal-title').textContent = title;
            document.getElementById('modal-artist').textContent = `by ${creator}`;
            
            const trackListDiv = document.getElementById('modal-track-list');
            trackListDiv.innerHTML = '<div style="text-align: center; padding: 20px;">Loading...</div>';
            
            document.getElementById('modal-overlay').style.display = 'flex';
            
            fetch(`/playlist_tracks/${playlistId}`)
                .then(response => response.json())
                .then(data => {
                    const tracks = data.tracks?.data || [];
                    if (tracks.length > 0) {
                        trackListDiv.innerHTML = tracks.map((track, index) => `
                            <div class="modal-track-item">
                                <div class="modal-track-number">${index + 1}</div>
                                <div class="modal-track-info">
                                    <div class="modal-track-title">${track.title}</div>
                                    <div class="modal-track-artist">${track.artist?.name || 'Unknown'}</div>
                                </div>
                                <div class="modal-track-duration">${formatDuration(track.duration)}</div>
                                <div class="modal-track-actions">
                                    <button class="btn-track-action" onclick="playPreview('${track.preview}', this)" title="Preview">
                                        <i class="fas fa-play"></i>
                                    </button>
                                    <button class="btn-track-action" onclick="downloadTrack('https://www.deezer.com/track/${track.id}', '${track.title.replace(/'/g, "\\'").replace(/"/g, '&quot;')}', '${track.artist?.name.replace(/'/g, "\\'").replace(/"/g, '&quot;')}', '${track.album?.cover_small || ''}')" title="Download">
                                        <i class="fas fa-download"></i>
                                    </button>
                                </div>
                            </div>
                        `).join('');
                    } else {
                        trackListDiv.innerHTML = '<div style="text-align: center; padding: 20px;">No tracks found</div>';
                    }
                })
                .catch(error => {
                    console.error('Error loading playlist tracks:', error);
                    trackListDiv.innerHTML = '<div style="text-align: center; padding: 20px; color: #ef4444;">Error loading tracks</div>';
                });
        }
        
        // Audio preview management
        let currentPreviewAudio = null;
        let currentPreviewButton = null;
        
        function playPreview(previewUrl, button) {
            // If same button clicked and playing, stop it
            if (currentPreviewButton === button && currentPreviewAudio && !currentPreviewAudio.paused) {
                currentPreviewAudio.pause();
                button.innerHTML = '<i class="fas fa-play"></i>';
                button.classList.remove('playing');
                currentPreviewAudio = null;
                currentPreviewButton = null;
                return;
            }
            
            // Stop current preview if different track
            if (currentPreviewAudio) {
                currentPreviewAudio.pause();
                if (currentPreviewButton) {
                    currentPreviewButton.innerHTML = '<i class="fas fa-play"></i>';
                    currentPreviewButton.classList.remove('playing');
                }
            }
            
            // Play new preview
            if (previewUrl && previewUrl !== 'null' && previewUrl !== 'undefined') {
                currentPreviewAudio = new Audio(previewUrl);
                currentPreviewButton = button;
                
                button.innerHTML = '<i class="fas fa-pause"></i>';
                button.classList.add('playing');
                
                currentPreviewAudio.play().catch(err => {
                    console.error('Error playing preview:', err);
                    showNotification('✗ Preview not available', true);
                    button.innerHTML = '<i class="fas fa-play"></i>';
                    button.classList.remove('playing');
                });
                
                currentPreviewAudio.addEventListener('ended', () => {
                    button.innerHTML = '<i class="fas fa-play"></i>';
                    button.classList.remove('playing');
                    currentPreviewAudio = null;
                    currentPreviewButton = null;
                });
            } else {
                showNotification('✗ Preview not available', true);
            }
        }
        
        function downloadTrack(trackUrl, title, artist, cover) {
            // Create a temporary button element for the loading animation
            const tempButton = document.createElement('button');
            tempButton.classList.add('btn-send');
            
            downloadContent(trackUrl, tempButton, title, artist, cover || '', 'track');
        }
        
        function closeModal() {
            // Stop preview if playing
            if (currentPreviewAudio) {
                currentPreviewAudio.pause();
                if (currentPreviewButton) {
                    currentPreviewButton.innerHTML = '<i class="fas fa-play"></i>';
                    currentPreviewButton.classList.remove('playing');
                }
                currentPreviewAudio = null;
                currentPreviewButton = null;
            }
            
            document.getElementById('modal-overlay').style.display = 'none';
            currentContentLink = '';
            currentContentType = '';
        }
        
        function downloadAllFromModal() {
            if (!currentContentLink) return;
            
            const modalTitle = document.getElementById('modal-title').textContent;
            const modalArtist = document.getElementById('modal-artist').textContent.replace('by ', '');
            const modalCover = document.getElementById('modal-cover').src;
            
            // Create a temporary button reference for the loading animation
            const downloadBtn = document.querySelector('.modal-footer .btn-send');
            
            downloadContent(currentContentLink, downloadBtn, modalTitle, modalArtist, modalCover, currentContentType);
            
            // Close modal after starting download
            setTimeout(() => closeModal(), 1000);
        }
        
        function formatDuration(seconds) {
            const minutes = Math.floor(seconds / 60);
            const secs = seconds % 60;
            return `${minutes}:${secs.toString().padStart(2, '0')}`;
        }
        
        // Close modal on overlay click
        document.getElementById('modal-overlay').addEventListener('click', function(e) {
            if (e.target === this) {
                closeModal();
            }
        });

        // Download all from modal
        document.getElementById('modal-download').addEventListener('click', downloadAllFromModal);

        function showNotification(message, isError = false) {
            notification.textContent = message;
            notification.className = 'notification show';
            if (isError) {
                notification.classList.add('error');
            }

            setTimeout(() => {
                notification.classList.remove('show');
            }, 3000);
        }

        // Service Worker Registration (PWA)
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/sw.js').catch(() => {
                    // Service worker registration failed, silently ignore
                });
            });
        }

        // Initialize history on page load
        renderHistory();

