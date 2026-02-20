document.addEventListener("DOMContentLoaded", () => {
    
    window.playMusic = function(filename) {
        // 1. On cible le nouveau lecteur VIDEO
        const player = document.getElementById('music-player');
        const source = document.getElementById('music-source');
        const titleLabel = document.getElementById('current-music-title');
        
        // 2. On construit le chemin
        // Rappel : tes fichiers "music" sont dans le dossier "audios" du serveur
        const path = "/static/musics/" + filename;
        
        // 3. Mise à jour de la source
        source.src = path;
        titleLabel.textContent = filename; // Ou le titre si tu l'as
        
        // 4. On recharge et on lance
        player.load();
        
        // Petite astuce : play() renvoie une "Promesse". 
        // Si le navigateur bloque l'autoplay, ça évite une erreur dans la console.
        player.play().catch(e => console.log("Lecture auto bloquée par le navigateur:", e));
    };

    // Fonction pour changer la source vidéo
    window.playVideo = function(filename, title) {
        const videoPlayer = document.getElementById('video-player');
        const videoSource = document.getElementById('video-source');
        const currentTitle = document.getElementById('current-video-title');
        
        videoSource.src = "/static/videos/" + filename;
        currentTitle.textContent = title;
        
        videoPlayer.load();
        videoPlayer.play();
    };
});


let allVideos = [];
let currentPlaylist = [];

// Récupération des paramètres URL (?tag=...)
const urlParams = new URLSearchParams(window.location.search);
const requestedTag = urlParams.get('tag');

const menuContainer = document.getElementById('album-menu');
const playerContainer = document.getElementById('video-player-container');
const tagsGrid = document.getElementById('tags-grid');
const videoElement = document.getElementById('main-video');
const titleElement = document.getElementById('video-title');
const nextBtn = document.getElementById('next-btn');

// --- 1. CHARGEMENT DES DONNÉES ---
fetch('data.json')
    .then(response => response.json())
    .then(data => {
        allVideos = data;
        
        // Logique de routing
        if (requestedTag) {
            // Si on a un tag dans l'URL, on lance le mode Player
            startPlayerMode(requestedTag);
        } else {
            // Sinon, on lance le mode Menu
            renderMenu();
        }
    })
    .catch(error => console.error('Erreur chargement JSON:', error));


// --- 2. LOGIQUE DU MENU ---
function renderMenu() {
    // Affiche le menu, cache le player
    menuContainer.classList.remove('hidden');
    playerContainer.classList.add('hidden');

    // 1. Récupérer tous les tags uniques
    const tagsSet = new Set();
    allVideos.forEach(vid => {
        if(vid.tags) {
            vid.tags.forEach(tag => tagsSet.add(tag));
        }
    });

    // 2. Créer la carte "ALÉATOIRE" (première position)
    createAlbumCard('Aléatoire', 'all', null, true);

    // 3. Créer les cartes pour chaque Tag
    tagsSet.forEach(tag => {
        // Trouver une image de couverture pour ce tag
        // On cherche la première vidéo qui a ce tag et qui a une image (poster/cover)
        const representativeVideo = allVideos.find(v => v.tags.includes(tag) && (v.poster || v.cover));
        
        // Image par défaut si rien trouvé (ou utilise l'image trouvée)
        const bgImage = representativeVideo ? (representativeVideo.poster || representativeVideo.cover) : null;

        createAlbumCard(tag, tag, bgImage, false);
    });
}

function createAlbumCard(title, tagValue, imageUrl, isRandom) {
    const link = document.createElement('a');
    link.href = `video.html?tag=${tagValue}`;
    link.className = `album-card ${isRandom ? 'random-card' : ''}`;

    let htmlContent = '';

    // Si on a une image, on l'ajoute en fond
    if (imageUrl) {
        htmlContent += `<img src="${imageUrl}" class="album-bg" alt="${title}">`;
    } else if (!isRandom) {
        // Si pas d'image et pas random, un fond gris générique
        link.style.background = '#333'; 
    }

    htmlContent += `<span class="album-title">${title}</span>`;
    
    link.innerHTML = htmlContent;
    tagsGrid.appendChild(link);
}


// --- 3. LOGIQUE DU PLAYER ---
function startPlayerMode(tag) {
    // Cache le menu, affiche le player
    menuContainer.classList.add('hidden');
    playerContainer.classList.remove('hidden');

    // Filtrage
    if (tag === 'all') {
        currentPlaylist = [...allVideos]; // Copie de tout
        // Mélange uniquement si c'est le mode aléatoire global
        shuffleArray(currentPlaylist);
    } else {
        // Filtre par tag
        currentPlaylist = allVideos.filter(video => video.tags && video.tags.includes(tag));
        // Optionnel : Tu peux aussi mélanger l'album si tu veux que l'ordre change à chaque fois
        // shuffleArray(currentPlaylist); 
    }

    if (currentPlaylist.length > 0) {
        playVideo(0);
    } else {
        alert("Aucune vidéo trouvée pour cet album !");
        window.location.href = "video.html"; // Retour au menu
    }
}

function playVideo(index) {
    // Sécurité boucle
    if (index >= currentPlaylist.length) {
        index = 0; // On boucle au début
    }

    const video = currentPlaylist[index];
    
    // Mise à jour de la source
    videoElement.src = video.src; // Assure-toi que ton JSON a bien "src"
    titleElement.textContent = video.title || "Vidéo sans titre";
    
    videoElement.play();

    // Gestion du bouton suivant
    nextBtn.onclick = () => {
        playVideo(index + 1);
    };

    // Auto-play next à la fin de la vidéo
    videoElement.onended = () => {
        playVideo(index + 1);
    };
}

// Fonction utilitaire de mélange (Fisher-Yates)
function shuffleArray(array) {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
    }
}