let AVAILABLE_TAGS = [];

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialisation générale (chargement des tags)
    if (typeof CURRENT_CATEGORY !== 'undefined') {
        initPage();
    }

    // 2. Gestion de la soumission du formulaire Histoire
    const storyForm = document.getElementById('story-form');
    if (storyForm) {
        storyForm.addEventListener('submit', (e) => {
            e.preventDefault();
            submitStory();
        });
    }

    // 3. GESTION DES MOTS (Jeu d'écriture)
    const wordForm = document.getElementById('word-form');
    if (wordForm) {
        // Initialisation des tags spécifiques à cette page
        if(typeof CURRENT_CATEGORY !== 'undefined' && CURRENT_CATEGORY === 'writing') {
             loadTags().then(() => renderWordTags());
        }

        wordForm.addEventListener('submit', (e) => {
            e.preventDefault();
            submitWord();
        });
    }
});

async function initPage() {
    await loadTags();
    
    // Si on est sur la page story, on affiche les tags dans le formulaire unique
    if (CURRENT_CATEGORY === 'story') {
        renderStoryTags();
    } 
    // Sinon (music/video/photo), on charge la liste des fichiers inbox
    else {
        await loadInbox();
    }
}

// --- GESTION DES TAGS (COMMUN) ---

async function loadTags() {
    try {
        const response = await fetch(`/api/tags/${CURRENT_CATEGORY}`);
        AVAILABLE_TAGS = await response.json();
    } catch (error) {
        console.error("Erreur chargement tags:", error);
    }
}

async function createNewTag() {
    const input = document.getElementById('new-tag-name');
    const tagName = input.value.trim();
    if (!tagName) return;

    try {
        const response = await fetch('/api/tags/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category: CURRENT_CATEGORY, tag_name: tagName })
        });
        const result = await response.json();
        
        if (result.success) {
            AVAILABLE_TAGS = result.tags; 
            input.value = ''; 
            
            // Mise à jour de l'affichage selon la page où on se trouve
            if (CURRENT_CATEGORY === 'story') {
                renderStoryTags();
            } else {
                loadInbox();
            }
        } else {
            alert("Erreur création tag");
        }
    } catch (e) {
        console.error(e);
    }
}

// --- LOGIQUE SPECIFIQUE HISTOIRE ---

function renderStoryTags() {
    const container = document.getElementById('story-tags-container');
    if (!container) return;

    container.innerHTML = '';
    
    if (AVAILABLE_TAGS.length === 0) {
        container.innerHTML = '<em>Aucun tag disponible. Créez-en un ci-dessus.</em>';
        return;
    }

    AVAILABLE_TAGS.forEach(tag => {
        container.innerHTML += `
            <label class="tag-option">
                <input type="checkbox" value="${tag}" class="story-tag-checkbox">
                ${tag}
            </label>
        `;
    });
}

async function submitStory() {
    const title = document.getElementById('story-title').value;
    const content = document.getElementById('story-content').value;
    
    // Récupération des tags cochés
    const checkboxes = document.querySelectorAll('.story-tag-checkbox:checked');
    const selectedTags = Array.from(checkboxes).map(cb => cb.value);

    if (selectedTags.length === 0) {
        if(!confirm("Aucun tag sélectionné pour cette histoire. Continuer ?")) return;
    }

    try {
        const response = await fetch('/api/add_story', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: title,
                content: content,
                tags: selectedTags // Envoi de la liste
            })
        });

        const result = await response.json();
        if (result.success) {
            alert('Histoire enregistrée avec succès !');
            window.location.href = '/admin'; // Retour au menu
        } else {
            alert('Erreur: ' + result.error);
        }
    } catch (error) {
        console.error(error);
        alert('Erreur réseau');
    }
}

// --- LOGIQUE SPECIFIQUE MEDIA (Inbox) ---

async function loadInbox() {
    const container = document.getElementById('file-list');
    if (!container) return; // Sécurité si on est sur la page story

    try {
        const response = await fetch(`/api/scan/${CURRENT_CATEGORY}`);
        const files = await response.json();

        container.innerHTML = '';
        
        if (files.length === 0) {
            container.innerHTML = '<p>Aucun fichier à traiter dans le dossier inbox.</p>';
            return;
        }

        files.forEach(file => {
            const safeFileName = file.replace(/'/g, "\\'");
            
            let tagsHtml = '';
            AVAILABLE_TAGS.forEach(tag => {
                tagsHtml += `
                    <label class="tag-option">
                        <input type="checkbox" value="${tag}" class="file-tag-checkbox">
                        ${tag}
                    </label>
                `;
            });

            const div = document.createElement('div');
            div.className = 'file-item';
            div.innerHTML = `
                <div class="file-header"><span>📄 ${file}</span></div>
                <div>Sélectionnez les tags :</div>
                <div class="tags-container">${tagsHtml}</div>
                <button class="add-btn" onclick="processFile(this, '${safeFileName}')">Valider et Ajouter</button>
            `;
            container.appendChild(div);
        });

    } catch (error) {
        console.error('Erreur:', error);
    }
}

async function processFile(btnElement, filename) {
    const parentDiv = btnElement.closest('.file-item');
    const checkboxes = parentDiv.querySelectorAll('.file-tag-checkbox:checked');
    const selectedTags = Array.from(checkboxes).map(cb => cb.value);

    if (selectedTags.length === 0) {
        if(!confirm("Aucun tag sélectionné. Continuer ?")) return;
    }

    btnElement.disabled = true;
    btnElement.textContent = "Traitement...";

    try {
        const response = await fetch('/api/add_media', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                category: CURRENT_CATEGORY,
                filename: filename,
                tags: selectedTags
            })
        });

        const result = await response.json();
        if (result.success) {
            loadInbox(); 
        } else {
            alert('Erreur: ' + result.error);
            btnElement.disabled = false;
        }
    } catch (error) {
        console.error(error);
        btnElement.disabled = false;
    }
}

// Ajoute cette fonction pour afficher les tags sur la page word
function renderWordTags() {
    const container = document.getElementById('word-tags-container');
    if (!container) return;
    container.innerHTML = '';
    
    if (AVAILABLE_TAGS.length === 0) {
        container.innerHTML = '<em>Aucun tag. Créez-en un.</em>';
        return;
    }

    AVAILABLE_TAGS.forEach(tag => {
        container.innerHTML += `
            <label class="tag-option">
                <input type="checkbox" value="${tag}" class="word-tag-checkbox">
                ${tag}
            </label>
        `;
    });
}

// Ajoute cette fonction pour envoyer le mot au serveur
async function submitWord() {
    const wordInput = document.getElementById('word-input');
    const word = wordInput.value.trim();
    
    const checkboxes = document.querySelectorAll('.word-tag-checkbox:checked');
    const selectedTags = Array.from(checkboxes).map(cb => cb.value);

    if (!word) return alert("Veuillez écrire un mot.");

    try {
        const response = await fetch('/api/add_word', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ word: word, tags: selectedTags })
        });

        const result = await response.json();
        if (result.success) {
            alert('Mot ajouté !');
            wordInput.value = ''; // Reset
            // On décoche les cases
            document.querySelectorAll('.word-tag-checkbox').forEach(cb => cb.checked = false);
        } else {
            alert('Erreur: ' + result.error);
        }
    } catch (error) {
        console.error(error);
        alert('Erreur réseau');
    }
}