import os
import json
import shutil
import datetime

# --- CONFIGURATION CHEMINS ABSOLUS (CRUCIAL) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'database.json')

FOLDERS = {
    'music': {'inbox': os.path.join(BASE_DIR, 'inbox_music'), 'dest': os.path.join(BASE_DIR, 'static', 'musics')},
    'video': {'inbox': os.path.join(BASE_DIR, 'inbox_video'), 'dest': os.path.join(BASE_DIR, 'static', 'videos')},
    'photo': {'inbox': os.path.join(BASE_DIR, 'inbox_photo'), 'dest': os.path.join(BASE_DIR, 'static', 'photos')},
    'story': {'dest': None}
}

def _load_db():
    print(f"📂 Lecture de la DB : {DB_FILE}") # DEBUG

    # Structure idéale que la base de données doit avoir
    default_structure = {
        'music': [],
        'video': [],
        'photo': [],
        'story': [],
        'writing_words': [], # Pour le jeu d'écriture
        'available_tags': {
            'music': [], 
            'video': [], 
            'photo': [], 
            'story': [], 
            'writing_words': []
        }
    }

    # 1. Si le fichier n'existe pas, on renvoie la structure par défaut
    if not os.path.exists(DB_FILE):
        print("⚠️ Fichier DB inexistant. Une nouvelle structure sera créée à la prochaine sauvegarde.")
        return default_structure

    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 2. VÉRIFICATION ET RÉPARATION (MIGRATION)
        # C'est ici qu'on s'assure que toutes les catégories existent, même dans un vieux fichier.
        
        # Vérification des catégories principales de contenu
        keys_to_check = ['music', 'video', 'photo', 'story', 'writing_words']
        for key in keys_to_check:
            if key not in data:
                print(f"🔧 Réparation : Ajout de la section manquante '{key}'")
                data[key] = []

        # Vérification de la section des tags
        if 'available_tags' not in data:
            data['available_tags'] = {}
        
        # Vérification des sous-catégories de tags
        for key in keys_to_check:
            if key not in data['available_tags']:
                print(f"🔧 Réparation : Ajout des tags pour '{key}'")
                data['available_tags'][key] = []

        return data

    except json.JSONDecodeError:
        print("❌ ERREUR : Le fichier database.json est corrompu (mauvais format).")
        return default_structure
    except Exception as e:
        print(f"❌ ERREUR lecture DB: {e}")
        return default_structure
    
    
def _save_db(data):
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"✅ SAUVEGARDE RÉUSSIE dans {DB_FILE}") # DEBUG
    except Exception as e:
        print(f"❌ CRASH SAUVEGARDE : {e}")

def _get_next_id(category, db):
    items = db.get(category, [])
    if not items: return 1
    return max((item.get('id', 0) for item in items), default=0) + 1

# --- FONCTIONS PUBLIQUES ---

def get_tags(category):
    db = _load_db()
    return db.get('available_tags', {}).get(category, [])

def create_tag(category, new_tag):
    db = _load_db()
    new_tag = new_tag.strip()
    
    if 'available_tags' not in db: db['available_tags'] = {}
    if category not in db['available_tags']: db['available_tags'][category] = []

    if new_tag not in db['available_tags'][category]:
        db['available_tags'][category].append(new_tag)
        _save_db(db)
        return True
    return False

def scan_inbox(category):
    if category not in FOLDERS or category == 'story': return []
    inbox_path = FOLDERS[category]['inbox']
    if not os.path.exists(inbox_path): os.makedirs(inbox_path)
    
    files = [f for f in os.listdir(inbox_path) if not f.startswith('.')]
    if category == 'music':
        files = [f for f in files if f.lower().endswith(('.mp3', '.mp4', '.m4a', '.wav'))]
    return files

def add_media_file(category, filename, selected_tags):
    print(f"🚀 Début ajout média: {filename}") # DEBUG
    config = FOLDERS[category]
    src = os.path.join(config['inbox'], filename)
    
    db = _load_db()
    new_id = _get_next_id(category, db)
    
    if not os.path.exists(config['dest']): os.makedirs(config['dest'])
    dest_path = os.path.join(config['dest'], filename)
    
    shutil.move(src, dest_path)
    
    new_entry = {
        'id': new_id,
        'path': f"static/{os.path.basename(config['dest'])}/{filename}",
        'tags': selected_tags or [],
        'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'title': filename
    }
    
    if category not in db: db[category] = []
    db[category].append(new_entry)
    
    _save_db(db) # Appel crucial
    return new_id

def add_story_entry(title, content, selected_tags):
    print(f"🚀 Début ajout histoire: {title}") # DEBUG
    
    db = _load_db()
    
    # Sécurité supplémentaire : s'assurer que la liste story existe
    if 'story' not in db: 
        print("⚠️ La section 'story' n'existait pas, création...")
        db['story'] = []

    new_id = _get_next_id('story', db)

    new_entry = {
        'id': new_id,
        'title': title,
        'content': content,
        'tags': selected_tags or [], # Si None, on met une liste vide
        'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    db['story'].append(new_entry)
    
    print(f"📝 Entrée préparée (ID: {new_id}), tentative de sauvegarde...")
    _save_db(db) # Sauvegarde effective
    
    return new_id

def add_writing_word(word, selected_tags):
    print(f"🚀 Ajout mot jeu d'écriture: {word}") 
    db = _load_db()
    
    # Nettoyage : Majuscule et suppression des espaces superflus
    clean_word = word.strip().upper()

    if 'writing_words' not in db: db['writing_words'] = []
    
    new_id = _get_next_id('writing_words', db)

    new_entry = {
        'id': new_id,
        'word': clean_word,
        'tags': selected_tags or [],
        'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    db['writing_words'].append(new_entry)
    _save_db(db)
    
    return new_id

def get_writing_words():
    """Récupère tous les mots pour le jeu"""
    db = _load_db()
    return db.get('writing_words', [])

def get_existing_tags(category):
    """Récupère la liste de tous les tags uniques utilisés dans une catégorie"""
    db = _load_db()
    items = db.get(category, [])
    
    unique_tags = set()
    for item in items:
        # On ajoute chaque tag de la liste des tags de l'élément
        for tag in item.get('tags', []):
            if tag: # Si le tag n'est pas vide
                unique_tags.add(tag)
    
    return list(unique_tags)

def get_all_media(category):
    """Récupère tout le contenu d'une catégorie (pour l'envoyer au JS)"""
    db = _load_db()
    return db.get(category, [])