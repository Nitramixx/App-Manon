from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
from werkzeug.utils import secure_filename
import json
import os
import re
import media_manager
import unicodedata
import random
import datetime
from PIL import Image
import shutil

app = Flask(__name__)

app.secret_key = 'manonapp' # Indispensable pour session

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GAMES_DIR = os.path.join(BASE_DIR, 'games')

UPLOAD_FOLDER = 'static/uploads/stories'
ICON_FOLDER = 'static/uploads/icones'
THEME_FOLDER = 'static/uploads/themes'

DEFAULT_DB = {
    'music': [], 'video': [], 'photo': [], 'story': [], 'writing_words': [],
    'available_tags': {'music': [], 'video': [], 'photo': [], 'story': [], 'writing': []},
    'music_themes': [], 'video_themes': [], 'photo_themes': [], 'story_themes': [], 'writing_themes': [],
    'planning_routine': [], 'planning_weekly': [], 'planning_events': [], 'planning_holidays': [],
    'planning_log': {},
    'memory_config': {'num_pairs': 6, 'num_players': 1},
    'puzzle_config': {'difficulty': 3, 'mode': 'swap'},
    'games_config': {'bubble': {'show_aim_hints': True, 'best_score': 0}},
}

# Fonction utilitaire pour charger les données
def load_data():
    base_path = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_path, 'database.json')
    if not os.path.exists(json_path):
        return json.loads(json.dumps(DEFAULT_DB))
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # Garantir les clés de config jeux / puzzle
    if 'puzzle_config' not in data:
        data['puzzle_config'] = DEFAULT_DB['puzzle_config'].copy()
    if 'games_config' not in data:
        data['games_config'] = json.loads(json.dumps(DEFAULT_DB['games_config']))
    return data
    
def clean_filename(filename):
    """
    Transforme "sïa - dis-moi.mp4" en "sia_-_dis-moi.mp4"
    Supprime les accents de façon robuste avant de sécuriser le nom.
    """
    # 1. Sépare les caractères de leurs accents (ex: ï devient i + ¨)
    nfkd_form = unicodedata.normalize('NFKD', filename)
    # 2. Ne garde que les caractères de base (supprime le ¨)
    name_without_accents = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    # 3. Utilise la fonction de Flask pour remplacer les espaces par des underscores
    return secure_filename(name_without_accents)

@app.route('/')
def index():
    return render_template('index.html')

# --- JEUX ACCESSIBLES (dossier games/) ---

@app.route('/jeux')
def jeux_menu():
    return render_template('games_menu.html')

@app.route('/jeux/bulles')
def jeux_bubble():
    data = load_data()
    cfg = data.get('games_config', {}).get('bubble', {'show_aim_hints': True})
    best = int(data.get('games_config', {}).get('bubble', {}).get('best_score', 0) or 0)
    return render_template(
        'games_bubble.html',
        show_aim_hints=bool(cfg.get('show_aim_hints', True)),
        best_score=best,
    )

def _update_game_best(game_key, score):
    data = load_data()
    games_cfg = data.setdefault('games_config', {})
    cfg = games_cfg.setdefault(game_key, {})
    current = int(cfg.get('best_score', 0) or 0)
    if score > current:
        cfg['best_score'] = score
        save_data(data)
        current = score
    return current

@app.route('/api/games/bubble/best', methods=['POST'])
def api_bubble_best():
    payload = request.get_json(silent=True) or {}
    try:
        score = int(payload.get('score', 0))
    except (TypeError, ValueError):
        return jsonify({'ok': False}), 400
    best = _update_game_best('bubble', score)
    return jsonify({'ok': True, 'best_score': best})

@app.route('/api/games/voiture/best', methods=['POST'])
def api_voiture_best():
    payload = request.get_json(silent=True) or {}
    try:
        score = int(payload.get('score', 0))
    except (TypeError, ValueError):
        return jsonify({'ok': False}), 400
    best = _update_game_best('voiture', score)
    return jsonify({'ok': True, 'best_score': best})

@app.route('/admin/games')
def admin_games():
    data = load_data()
    config = data.get('games_config', {'bubble': {'show_aim_hints': True}})
    if 'bubble' not in config:
        config['bubble'] = {'show_aim_hints': True}
    return render_template('admin_games.html', config=config)

@app.route('/admin/games/save', methods=['POST'])
def save_games_config():
    data = load_data()
    data['games_config'] = {
        'bubble': {
            'show_aim_hints': bool(request.form.get('show_aim_hints'))
        }
    }
    save_data(data)
    return redirect(url_for('admin_games'))

@app.route('/games/<path:filename>')
def serve_game(filename):
    return send_from_directory(GAMES_DIR, filename)

# --- SECTION MUSIQUE (NOUVEAU SYSTÈME) ---

@app.route('/music')
def music_random():
    data = load_data()
    music_data = data.get('music', [])
    if not music_data: return "Pas de musique", 404
    
    track = random.choice(music_data)
    cover = track.get('cover') if track.get('cover') else 'default_music.png'
    
    # UTILISATION DE LA NOUVELLE LOGIQUE THÈMES
    themes = get_themes_for_category(data, 'music')

    return render_template('music_player_split.html',
                           mode='random',
                           track=track,
                           cover_image=cover,
                           tags=themes)

@app.route('/music/playlist/<tag_name>')
def music_playlist(tag_name):
    data = load_data()
    music_data = data.get('music', [])
    
    # UTILISATION DE LA NOUVELLE LOGIQUE THÈMES
    themes = get_themes_for_category(data, 'music')
    
    playlist = [m for m in music_data if tag_name in m['tags']]
    if not playlist: return "Playlist vide", 404

    current_index = request.args.get('index', 0, type=int)
    if current_index < 0 or current_index >= len(playlist): current_index = 0
    
    track = playlist[current_index]
    cover = track.get('cover') if track.get('cover') else 'default_music.png'
    prev_idx = current_index - 1 if current_index > 0 else None
    next_idx = current_index + 1 if current_index < len(playlist) - 1 else None

    return render_template('music_player_split.html',
                           mode='playlist',
                           tag_name=tag_name,
                           track=track,
                           cover_image=cover,
                           tags=themes, # Objets thèmes
                           current_index=current_index,
                           prev_index=prev_idx,
                           next_index=next_idx,
                           total=len(playlist))

# --- ROUTES PHOTOS ---

@app.route('/photos')
def photos_menu():
    data = load_data()
    # UTILISATION DE LA NOUVELLE LOGIQUE THÈMES
    themes = get_themes_for_category(data, 'photo')
    return render_template('photos_menu.html', albums=themes) # 'albums' reçoit maintenant des thèmes {name, img}

# 1. MODIFIER LA ROUTE PHOTO_VIEWER EXISTANTE
@app.route('/photos/tag/<tag_name>')
def photo_viewer(tag_name):
    data = load_data()
    PHOTOS_DATA = data['photo']

    # Filtrer par tag
    album_photos = [p for p in PHOTOS_DATA if tag_name in p['tags']]
    if not album_photos:
        return render_template('error.html', message="Aucune photo trouvée.")

    current_index = request.args.get('index', 0, type=int)
    if current_index < 0 or current_index >= len(album_photos): current_index = 0

    current_photo = album_photos[current_index]

    # --- AJOUT MUSIQUE ---
    # On cherche si le thème a une musique
    themes = data.get('photo_themes', [])
    theme_obj = next((t for t in themes if t['name'] == tag_name), None)
    bg_music = theme_obj.get('music') if theme_obj else None

    return render_template('photo_viewer.html', 
                           tag_name=tag_name,
                           photo=current_photo,
                           current_index=current_index,
                           total=len(album_photos),
                           bg_music=bg_music) # On envoie la musique !

@app.route('/videos')
def videos_menu():
    data = load_data()
    # On tente de récupérer les thèmes définis explicitement pour les vidéos.
    # Si aucun n'est présent, on retombe sur la logique générique qui cherche
    # les tags utilisés dans les fichiers (via get_themes_for_category).
    themes = data.get('video_themes', [])
    if not themes:
        themes = get_themes_for_category(data, 'video')
    return render_template('videos_menu.html', albums=themes)

@app.route('/videos/tag/<tag_name>')
def video_player(tag_name):
    """
    Affiche le lecteur pour un TAG spécifique.
    """
    data = load_data()
    VIDEOS_DATA = data['video']
    # 1. Filtrer la liste pour ne garder que les vidéos qui ont ce tag
    playlist = [v for v in VIDEOS_DATA if tag_name in v['tags']]
    
    if not playlist:
        return render_template('error.html', message="Aucune vidéo trouvée pour cet album.")

    # 2. Récupérer l'index actuel (0 par défaut)
    current_index = request.args.get('index', 0, type=int)
    
    # Sécurité index
    if current_index < 0 or current_index >= len(playlist):
        current_index = 0

    current_video = playlist[current_index]

    # 3. Calcul Suivant / Précédent
    prev_index = current_index - 1 if current_index > 0 else None
    next_index = current_index + 1 if current_index < len(playlist) - 1 else None

    return render_template('video_player.html', 
                           tag_name=tag_name,
                           video=current_video,
                           current_index=current_index,
                           prev_index=prev_index,
                           next_index=next_index,
                           total=len(playlist))

# --- NOUVELLE ROUTE LECTURE HISTOIRE (CHAPITRE PAR CHAPITRE) ---
# --- Route 1 : Le Menu des Catégories ---
@app.route('/story_menu')
def story_menu():
    data = load_data()
    
    # On récupère les thèmes configurés (Objets avec images)
    themes = data.get('story_themes', [])
    
    # Si aucun thème n'est configuré mais qu'il y a des tags simples dans available_tags,
    # on crée des thèmes "fictifs" pour éviter une page vide
    if not themes:
        existing_tags = data.get('available_tags', {}).get('story', [])
        for tag in existing_tags:
            themes.append({'name': tag, 'img': 'default_theme.png'}) # Image par défaut à prévoir

    return render_template('story_menu.html', themes=themes)

# --- Route 2 : Choix des histoires par catégorie ---
@app.route('/story_menu/<tag>')
def story_choice(tag):
    data = load_data()
    stories = data["story"]
    
    # Trouver le thème pour voir s'il a une musique
    themes = data.get('story_themes', [])
    current_theme_obj = next((t for t in themes if t['name'] == tag), None)
    background_music = current_theme_obj.get('music') if current_theme_obj else None

    filtered_stories = [s for s in stories if tag in s["tags"]]
    
    return render_template('story_choice.html', 
                           stories=filtered_stories, 
                           current_tag=tag,
                           bg_music=background_music) # On passe la musique

# --- Route 3 : Lecture d'une histoire chapitre par chapitre ---
@app.route('/story/<int:story_id>')
def story_reader(story_id):
    data = load_data()
    stories = data['story']
    
    # 1. Trouver l'histoire
    story = next((s for s in stories if s['id'] == story_id), None)
    if not story:
        return "Histoire introuvable", 404

    # 2. Gestion des chapitres
    chapters = story.get('chapters', [])
    if not chapters:
        return "Cette histoire est vide.", 404

    # 3. Récupérer l'index du chapitre (0 par défaut)
    chapter_index = request.args.get('chapter', 0, type=int)
    
    # Sécurité bornes
    if chapter_index < 0: chapter_index = 0
    if chapter_index >= len(chapters): chapter_index = 0

    current_chapter = chapters[chapter_index]

    # 4. Calcul Navigation (Logique Python pure)
    prev_idx = chapter_index - 1 if chapter_index > 0 else None
    next_idx = chapter_index + 1 if chapter_index < len(chapters) - 1 else None

    return render_template('story_read.html', 
                           story=story, 
                           chapter=current_chapter,
                           current_index=chapter_index,
                           total_chapters=len(chapters),
                           prev_index=prev_idx, 
                           next_index=next_idx)

# Fonction utilitaire pour nettoyer les accents (ex: "Éléphant" -> "elephant")
def remove_accents(input_str):
    if not input_str:
        return ""
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

@app.template_filter('replace_icons')
def replace_icons_filter(text):
    """
    Scanne le texte et remplace les mots par leurs icônes.
    Insensible à la casse et aux accents (ex: 'Garçon' matche 'garcon.png')
    """
    if not text:
        return ""

    # 1. Lister les icônes et créer une "carte" nettoyée
    # Clé = nom nettoyé (ex: 'garcon'), Valeur = vrai nom de fichier (ex: 'Garçon.png')
    try:
        available_icons = os.listdir(ICON_FOLDER)
    except FileNotFoundError:
        return text

    icon_map = {}
    for filename in available_icons:
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            # On prend le nom sans extension
            name_raw = os.path.splitext(filename)[0]
            # On le nettoie : minuscule + sans accents
            name_clean = remove_accents(name_raw).lower()
            icon_map[name_clean] = filename

    # 2. Fonction de remplacement appelée pour chaque mot trouvé
    def replace_match(match):
        word_found = match.group(0) 
        word_clean = remove_accents(word_found).lower()
        
        target_word = None
        filename = None

        # Recherche directe
        if word_clean in icon_map:
            target_word = word_clean # Le mot à taper sera le mot sans accent
            filename = icon_map[word_clean]
        
        # Recherche singulier
        elif word_clean.endswith('s') and word_clean[:-1] in icon_map:
            target_word = word_clean[:-1] # On fait taper le singulier (ex: chats -> chat)
            filename = icon_map[word_clean[:-1]]

        if filename:
            url = f"/static/uploads/icones/{filename}"
            # AJOUT : data-target contient le mot attendu pour le jeu, class 'interactive-icon' pour le JS
            return f'<img src="{url}" class="text-icon interactive-icon" data-target="{target_word}" alt="{word_found}" title="Jouer avec ce mot">'

        return word_found

    # 3. Regex qui capture tous les mots (y compris avec accents français)
    # \w inclut les caractères alphanumériques et les accents en Python 3
    pattern = re.compile(r'\b\w+\b', re.UNICODE)
    
    return pattern.sub(replace_match, text)

@app.route('/api/delete_tag', methods=['POST'])
def delete_tag():
    """Supprime un tag de la liste globale dans le JSON."""
    data = request.get_json()
    tag_to_delete = data.get('tag')

    if not tag_to_delete:
        return jsonify({'success': False, 'error': 'Aucun tag spécifié'})

    # 1. Chargement des données (CRUD Python)
    db_data = load_data() # Ta fonction qui lit le json complet
    
    # On s'assure d'avoir accès à la liste des tags
    # Adapte 'available_tags' selon la structure réelle de ton JSON
    # Exemple de structure attendue : {"stories": [...], "available_tags": ["Magie", "Nature"]}
    current_tags = db_data.get('available_tags', [])['story'] if 'story' in db_data.get('available_tags', {}) else []

    if tag_to_delete in current_tags:
        # 2. Suppression (Logique Python)
        current_tags.remove(tag_to_delete)
        db_data['available_tags'] = current_tags # Mise à jour
        
        # 3. Sauvegarde
        try:
            with open("database.json", 'w', encoding='utf-8') as f:
                json.dump(db_data, f, indent=4, ensure_ascii=False)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    else:
        return jsonify({'success': False, 'error': 'Tag introuvable'})

# --- Routes pour le jeu d'écriture ---

@app.route('/writing')
def writing_menu():
    data = load_data()
    
    # On récupère les thèmes configurés (Objets avec images)
    themes = data.get('writing_themes', [])
    
    # Si aucun thème n'est configuré mais qu'il y a des tags simples, on crée des "faux" thèmes
    if not themes:
        existing_tags = data.get('available_tags', {}).get('writing_words', [])
        for tag in existing_tags:
            themes.append({'name': tag, 'img': 'default_theme.png'}) 

    return render_template('writing_menu.html', themes=themes)

@app.route('/writing/game/<category>', methods=['GET'])
def writing_game(category):
    data = load_data()
    all_words = data.get('writing_words', [])

    # 1. Filtrage (Code existant)
    if category == "Tout":
        candidates = all_words
    else:
        candidates = [w for w in all_words if category in w.get('tags', [])]

    if not candidates:
        return "Aucun mot trouvé dans cette catégorie."

    # 2. Choix du mot (Code existant)
    last_id = session.get('last_word_id')
    potential_words = [w for w in candidates if w['id'] != last_id]
    if not potential_words:
        potential_words = candidates

    chosen_word = random.choice(potential_words)
    session['last_word_id'] = chosen_word['id']
    image_name = f"{chosen_word['word']}.png"

    # --- AJOUT ICI : Récupération de la musique du thème ---
    bg_music = None
    if category != "Tout":
        themes = data.get('writing_themes', [])
        theme_obj = next((t for t in themes if t['name'] == category), None)
        bg_music = theme_obj.get('music') if theme_obj else None

    return render_template(
        'writing_game.html', 
        category=category, 
        word_obj=chosen_word,
        image_name=image_name,
        bg_music=bg_music  # On passe la variable au template
    )

# --- API POUR OBTENIR LE PROCHAIN MOT SANS RECHARGER LA PAGE ---
@app.route('/api/writing/next/<category>')
def api_writing_next(category):
    data = load_data()
    all_words = data.get('writing_words', [])

    # 1. Filtrage
    if category == "Tout":
        candidates = all_words
    else:
        candidates = [w for w in all_words if category in w.get('tags', [])]

    if not candidates:
        return jsonify({'error': 'Aucun mot trouvé'}), 404

    # 2. Choix aléatoire (évite le précédent)
    last_id = session.get('last_word_id')
    potential_words = [w for w in candidates if w['id'] != last_id]
    
    if not potential_words:
        potential_words = candidates

    chosen_word = random.choice(potential_words)
    session['last_word_id'] = chosen_word['id']
    
    # 3. On renvoie les données brutes
    return jsonify({
        'word': chosen_word['word'],
        'image': f"{chosen_word['word']}.png",
        'id': chosen_word['id']
    })

# --- ROUTE UTILISATEUR : Le Planning du Jour ---
@app.route('/planning')
def planning():
    data = load_data()
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    current_weekday = now.weekday()

    def get_tasks_for_date(target_date):
        t_str = target_date.strftime("%Y-%m-%d")
        t_wd = target_date.weekday()
        t_month_day = target_date.strftime("%m-%d")
        
        is_holiday = False
        for h in data.get('planning_holidays', []):
            if h['start_date'] <= t_str <= h['end_date']:
                is_holiday = True
                break
        
        tasks = []
        for r in data.get('planning_routine', []):
            tasks.append({**r, "type": "routine", "unique_id": f"rout_{r['id']}"})
            
        for w in data.get('planning_weekly', []):
            if int(w['day']) == t_wd:
                if w.get('ignore_holidays') and is_holiday:
                    continue
                tasks.append({**w, "type": "weekly", "unique_id": f"week_{w['id']}"})
                
        for e in data.get('planning_events', []):
            if e.get('is_annual') and e.get('date')[5:] == t_month_day:
                tasks.append({**e, "type": "event", "unique_id": f"evt_{e['id']}"})
            elif not e.get('is_annual') and e.get('date') == t_str:
                tasks.append({**e, "type": "event", "unique_id": f"evt_{e['id']}"})
                    
        return sorted(tasks, key=lambda x: x.get('time', '00:00'))

    days_to_display = []
    if current_weekday < 5:
        range_days = [0, 1, 2, 3, 4] 
        start_date_ref = now - datetime.timedelta(days=current_weekday)
    else:
        range_days = [5, 6, 0]
        offset = current_weekday - 5 
        start_date_ref = now - datetime.timedelta(days=offset)

    day_labels = ["L", "M", "M", "J", "V", "S", "D"]

    for i, day_idx in enumerate(range_days):
        if current_weekday >= 5 and day_idx == 0:
            target_date = now + datetime.timedelta(days=(7 - current_weekday))
        else:
            target_date = start_date_ref + datetime.timedelta(days=i)
            
        target_date_str = target_date.strftime("%Y-%m-%d")
        day_tasks = get_tasks_for_date(target_date)
        day_history = data.get('planning_log', {}).get(target_date_str, [])
        
        # --- NOUVELLE LOGIQUE : LISTE D'OPTIONS ---
        completed_map = {}
        for item in day_history:
            if isinstance(item, dict):
                opt = item.get('option')
                if isinstance(opt, str): opt = [opt] # Rétrocompatibilité
                completed_map[item['id']] = opt or []
            else:
                completed_map[item] = []
        
        completed_tasks = []
        pending_tasks = []
        for t in day_tasks:
            if t['unique_id'] in completed_map:
                t['selected_options'] = completed_map[t['unique_id']]
                t['selected_option_imgs'] = []
                
                # On récupère toutes les images des options cochées
                if 'options' in t:
                    for opt in t['options']:
                        if opt.get('text') in t['selected_options'] and opt.get('img'):
                            t['selected_option_imgs'].append(opt.get('img'))
                            
                completed_tasks.append(t)
            else:
                pending_tasks.append(t)
        
        days_to_display.append({
            "weekday": day_idx,
            "label": day_labels[day_idx],
            "is_today": (target_date_str == today_str),
            "date": target_date_str,
            "completed": completed_tasks,
            "pending": pending_tasks
        })

    today_data = next((d for d in days_to_display if d['is_today']), None)
    current_task = today_data['pending'][0] if today_data and today_data['pending'] else None
    is_finished = today_data and len(today_data['pending']) == 0 and len(today_data['completed']) > 0

    return render_template('planning.html', week_days=days_to_display, current_task=current_task, is_finished=is_finished)

# --- ROUTE ACTION : Valider une tâche (AJAX) ---
@app.route('/planning/validate', methods=['POST'])
def planning_validate():
    data = load_data()
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    req = request.json
    unique_id = req.get('unique_id')
    options_selected = req.get('options') # Ceci est maintenant une LISTE []
    
    if 'planning_log' not in data:
        data['planning_log'] = {}
    if today_str not in data['planning_log']:
        data['planning_log'][today_str] = []
        
    history = data['planning_log'][today_str]
    entry = {"id": unique_id, "option": options_selected} if options_selected else unique_id
    
    existing_ids = [item['id'] if isinstance(item, dict) else item for item in history]
    if unique_id not in existing_ids:
        history.append(entry)
        save_data(data)
        
    return jsonify({"success": True})

@app.route('/memory')
def memory_menu():
    """
    Menu de choix du TAG pour le Memory.
    Moins complexe : on renvoie une liste d'albums structuré comme dans
    `photos_menu()` afin que la template puisse être quasi identique.
    Chaque élément contient :
        - name : nom du tag/thème
        - img  : nom du fichier image dans uploads/themes (peut être None)
        - thumb_path : chemin relatif vers une image quelconque (photo) si img est manquant
        - music : chemin éventuel vers un fichier musical
    """
    data = load_data()

    albums_structured = []
    themes = data.get('photo_themes', [])
    if themes:
        for theme in themes:
            albums_structured.append({
                'name': theme.get('name'),
                'img': theme.get('img'),
                'thumb_path': None,
                'music': theme.get('music')
            })
    else:
        # fallback en dehors du dossier themes
        PHOTOS_DATA = data.get('photo', [])
        unique_tags = sorted(list(set(tag for item in PHOTOS_DATA for tag in item['tags'])))
        for tag in unique_tags:
            thumbnail = next((p['path'] for p in PHOTOS_DATA if tag in p['tags']), None)
            thumb_rel = None
            if thumbnail:
                thumb_rel = thumbnail.replace('static/', '', 1) if thumbnail.startswith('static/') else thumbnail
            albums_structured.append({'name': tag, 'img': None, 'thumb_path': thumb_rel, 'music': None})

    return render_template('memory_menu.html', albums=albums_structured)

@app.route('/memory/play/<tag_name>')
def memory_game(tag_name):
    """
    Logique du jeu :
    1. Récupère config (nb paires).
    2. Récupère photos du tag.
    3. Option B : Complète si manque de photos.
    4. Crée les paires et mélange.
    """
    data = load_data()
    config = data.get('memory_config', {"num_pairs": 6, "num_players": 1})
    num_pairs = config['num_pairs']
    
    # 1. Photos disponibles pour ce tag
    available_photos = [p for p in data['photo'] if tag_name in p['tags']]
    
    if not available_photos:
        return "Pas de photos pour ce tag", 404

    # 2. Sélection des images (Option B: Boucle si pas assez)
    selected_images = []
    while len(selected_images) < num_pairs:
        # On ajoute toute la liste autant de fois que nécessaire
        selected_images.extend(available_photos)
    
    # On coupe au nombre exact de paires demandées
    selected_images = selected_images[:num_pairs]
    
    # 3. Création du deck (Paires)
    # On crée une liste d'objets pour le template
    deck = []
    for photo in selected_images:
        # On ajoute deux fois chaque image
        for i in range(2):
            deck.append({
                'id': photo['id'],       # Pour identifier la paire (match)
                'path': photo['path'],   # L'image à afficher
                'uuid': f"{photo['id']}_{i}_{random.randint(0,9999)}" # ID unique pour le DOM HTML
            })
            
    # 4. Mélange final
    random.shuffle(deck)
    
    return render_template('memory_game.html', 
                           cards=deck, 
                           tag_name=tag_name,
                           num_players=config['num_players'])

# --- NOUVELLES ROUTES ADMIN ---

@app.route('/admin')
def admin():
    return render_template('admin.html')

# 1. MODIFIER admin_process POUR ENVOYER LES MUSIQUES (Pour le choix dans le menu déroulant)
@app.route('/admin/process/<category>')
def admin_process(category):
    data = load_data()
    
    # On récupère la liste des musiques pour pouvoir les associer aux thèmes
    music_list = data.get('music', [])
    
    if category == 'story':
        available_tags = data.get('available_tags', {}).get('story', [])
        stories_list = sorted(data.get('story', []), key=lambda x: x['id'], reverse=True)
        # On récupère aussi les thèmes complets (avec images/musique) pour la gestion
        themes_list = data.get('story_themes', [])
        
        return render_template('admin_story.html', 
                               available_tags=available_tags, 
                               stories=stories_list,
                               themes=themes_list, # Pour le tableau de gestion
                               musics=music_list)  # Pour le selecteur de musique
    
    elif category == 'writing':
        available_tags = data.get('available_tags', {}).get('writing_words', [])
        words = data.get('writing_words', [])
        themes_list = data.get('writing_themes', [])
        
        return render_template('admin_writing.html', 
                               available_tags=available_tags, 
                               words=words,
                               themes=themes_list,
                               musics=music_list)
        
    elif category in ['music', 'video', 'photo']:
        available_tags = data.get('available_tags', {}).get(category, [])
        themes_list = data.get(f'{category}_themes', [])
        existing_files = data.get(category, [])
        existing_files.sort(key=lambda x: x.get('id', 0), reverse=True)

        # --- NOUVEAU : LECTURE DE L'INBOX ---
        inbox_folder = os.path.join('static', f'inbox_{category}')
        os.makedirs(inbox_folder, exist_ok=True) # Crée le dossier s'il n'existe pas
        
        # On liste les fichiers (en ignorant les fichiers cachés comme .DS_Store)
        inbox_files = [f for f in os.listdir(inbox_folder) if not f.startswith('.') and os.path.isfile(os.path.join(inbox_folder, f))]

        return render_template('admin_media.html', 
                               category=category,
                               available_tags=available_tags,
                               themes=themes_list,
                               musics=music_list,
                               files=existing_files,
                               inbox_files=inbox_files) # On envoie les fichiers de l'inbox
    
    return "Catégorie inconnue", 404

# --- ROUTE ADMIN : Affichage du Planning ---
@app.route('/admin/planning')
def admin_planning():
    data = load_data()
    
    # 1. Routines
    routine = sorted(data.get('planning_routine', []), key=lambda x: x.get('time', '00:00'))
    
    # 2. Hebdomadaire (Trié par jour 0=Lundi, puis heure)
    weekly = sorted(data.get('planning_weekly', []), key=lambda x: (int(x.get('day', 0)), x.get('time', '00:00')))
    
    # 3. Événements (Ponctuels et Annuels)
    events = sorted(data.get('planning_events', []), key=lambda x: x.get('date', '9999-99-99'))
    
    # 4. Vacances
    holidays = sorted(data.get('planning_holidays', []), key=lambda x: x.get('start_date', '9999-99-99'))
    
    return render_template('admin_planning.html', 
                           routine=routine, 
                           weekly=weekly, 
                           events=events, 
                           holidays=holidays)

# --- SAUVEGARDE ROUTINE (Avec Options Dynamiques & Audio) ---
@app.route('/admin/planning/routine/save', methods=['POST'])
def save_routine_item():
    data = load_data()
    items = data.get('planning_routine', [])
    
    item_id = request.form.get('id')
    title = request.form.get('title')
    time_val = request.form.get('time')
    question = request.form.get('question')
    
    target_folder = os.path.join('static', 'uploads', 'edt')
    os.makedirs(target_folder, exist_ok=True)

    # Gestion Image Principale
    image_filename = request.form.get('current_image')
    file = request.files.get('image_file')
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        file.save(os.path.join(target_folder, filename))
        image_filename = filename

    # Gestion Audio Principal
    audio_filename = request.form.get('current_audio')
    audio_file = request.files.get('audio_file')
    if audio_file and audio_file.filename != '':
        afilename = secure_filename(audio_file.filename)
        audio_file.save(os.path.join(target_folder, afilename))
        audio_filename = afilename

    # Gestion des Options Dynamiques (Images + Textes)
    options_list = []
    for i in range(1, 30): # On scanne jusqu'à 30 options possibles
        opt_text = request.form.get(f'option_text_{i}')
        if not opt_text: continue # Si l'option n'existe pas, on passe
        
        opt_img = request.form.get(f'option_current_img_{i}')
        opt_file = request.files.get(f'option_img_{i}')
        
        if opt_file and opt_file.filename != '':
            ofilename = secure_filename(opt_file.filename)
            opt_file.save(os.path.join(target_folder, ofilename))
            opt_img = ofilename
            
        options_list.append({"text": opt_text.strip(), "img": opt_img})

    if item_id:
        for item in items:
            if str(item['id']) == item_id:
                item.update({"title": title, "time": time_val, "img": image_filename, "audio": audio_filename, "question": question, "options": options_list})
                break
    else:
        new_id = max([r.get('id', 0) for r in items] or [0]) + 1
        items.append({"id": new_id, "title": title, "time": time_val, "img": image_filename, "audio": audio_filename, "question": question, "options": options_list})

    data['planning_routine'] = items
    save_data(data)
    return redirect(url_for('admin_planning'))

# --- SAUVEGARDE HEBDOMADAIRE ---
@app.route('/admin/planning/weekly/save', methods=['POST'])
def save_weekly_item():
    data = load_data()
    items = data.get('planning_weekly', [])
    
    item_id = request.form.get('id')
    title = request.form.get('title')
    day = int(request.form.get('day'))
    time_val = request.form.get('time')
    ignore_holidays = request.form.get('ignore_holidays') == 'on'
    
    target_folder = os.path.join('static', 'uploads', 'edt')
    os.makedirs(target_folder, exist_ok=True)

    image_filename = request.form.get('current_image')
    file = request.files.get('image_file')
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        file.save(os.path.join(target_folder, filename))
        image_filename = filename

    audio_filename = request.form.get('current_audio')
    audio_file = request.files.get('audio_file')
    if audio_file and audio_file.filename != '':
        afilename = secure_filename(audio_file.filename)
        audio_file.save(os.path.join(target_folder, afilename))
        audio_filename = afilename

    if item_id:
        for item in items:
            if str(item['id']) == item_id:
                item.update({"title": title, "day": day, "time": time_val, "img": image_filename, "audio": audio_filename, "ignore_holidays": ignore_holidays})
                break
    else:
        new_id = max([r.get('id', 0) for r in items] or [0]) + 1
        items.append({"id": new_id, "title": title, "day": day, "time": time_val, "img": image_filename, "audio": audio_filename, "ignore_holidays": ignore_holidays})

    data['planning_weekly'] = items
    save_data(data)
    return redirect(url_for('admin_planning'))

# --- SAUVEGARDE ÉVÉNEMENTS ---
@app.route('/admin/planning/event/save', methods=['POST'])
def save_event_item():
    data = load_data()
    items = data.get('planning_events', [])
    
    item_id = request.form.get('id')
    title = request.form.get('title')
    date_val = request.form.get('date')
    time_val = request.form.get('time')
    is_annual = request.form.get('is_annual') == 'on'
    
    target_folder = os.path.join('static', 'uploads', 'edt')
    os.makedirs(target_folder, exist_ok=True)

    image_filename = request.form.get('current_image')
    file = request.files.get('image_file')
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        file.save(os.path.join(target_folder, filename))
        image_filename = filename

    audio_filename = request.form.get('current_audio')
    audio_file = request.files.get('audio_file')
    if audio_file and audio_file.filename != '':
        afilename = secure_filename(audio_file.filename)
        audio_file.save(os.path.join(target_folder, afilename))
        audio_filename = afilename

    if item_id:
        for item in items:
            if str(item['id']) == item_id:
                item.update({"title": title, "date": date_val, "time": time_val, "img": image_filename, "audio": audio_filename, "is_annual": is_annual})
                break
    else:
        new_id = max([r.get('id', 0) for r in items] or [0]) + 1
        items.append({"id": new_id, "title": title, "date": date_val, "time": time_val, "img": image_filename, "audio": audio_filename, "is_annual": is_annual})

    data['planning_events'] = items
    save_data(data)
    return redirect(url_for('admin_planning'))

# --- SAUVEGARDE VACANCES ---
@app.route('/admin/planning/holiday/save', methods=['POST'])
def save_holiday_item():
    data = load_data()
    items = data.get('planning_holidays', [])
    
    item_id = request.form.get('id')
    name = request.form.get('name')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    if item_id:
        for item in items:
            if str(item['id']) == item_id:
                item.update({"name": name, "start_date": start_date, "end_date": end_date})
                break
    else:
        new_id = max([r.get('id', 0) for r in items] or [0]) + 1
        items.append({"id": new_id, "name": name, "start_date": start_date, "end_date": end_date})

    data['planning_holidays'] = items
    save_data(data)
    return redirect(url_for('admin_planning'))

# --- SUPPRESSION GÉNÉRIQUE ---
@app.route('/admin/planning/delete', methods=['POST'])
def delete_planning_item():
    data = load_data()
    category = request.form.get('category') # 'planning_routine', 'planning_weekly', etc.
    item_id = request.form.get('id')
    
    if category in data:
        data[category] = [i for i in data[category] if str(i.get('id')) != item_id]
        save_data(data)
        
    return redirect(url_for('admin_planning'))

# --- ROUTE ADMIN : Gestion de la ROUTINE (Ajout / Modif / Suppr) ---
def save_data(data):
    """
    Prend le dictionnaire Python 'data' et l'écrase dans le fichier database.json
    pour sauvegarder les changements définitivement.
    """
    with open('database.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    
@app.route('/api/create_writing_theme', methods=['POST'])
def api_create_writing_theme():
    try:
        data = load_data()
        
        # Récupération
        tag_name = request.form.get('tag_name').strip()
        image_file = request.files.get('tag_image')
        
        if not tag_name or not image_file:
            return jsonify({'success': False, 'error': 'Nom et image requis'}), 400

        # Sauvegarde Image
        os.makedirs(THEME_FOLDER, exist_ok=True)
        ext = image_file.filename.split('.')[-1]
        safe_name = secure_filename(tag_name)
        image_filename = f"writing_theme_{safe_name}.{ext}"
        image_file.save(os.path.join(THEME_FOLDER, image_filename))
        
        # Mise à jour DB (writing_themes)
        if 'writing_themes' not in data:
            data['writing_themes'] = []
            
        existing = next((t for t in data['writing_themes'] if t['name'] == tag_name), None)
        if existing:
            existing['img'] = image_filename
        else:
            data['writing_themes'].append({"name": tag_name, "img": image_filename})
            
        # Mise à jour DB (available_tags)
        if 'writing_words' not in data['available_tags']:
            data['available_tags']['writing_words'] = []
            
        if tag_name not in data['available_tags']['writing_words']:
            data['available_tags']['writing_words'].append(tag_name)
            data['available_tags']['writing_words'].sort()

        save_data(data)
        
        return jsonify({'success': True, 'tag': tag_name, 'img': image_filename})

    except Exception as e:
        print(f"ERREUR WRITING THEME: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scan/<category>')
def api_scan(category):
    files = media_manager.scan_inbox(category)
    return jsonify(files)

# 2. NOUVELLE API : RÉCUPÉRER LES DONNÉES D'UN MÉDIA (JSON)
@app.route('/api/get_media_data')
def api_get_media_data():
    try:
        data = load_data()
        category = request.args.get('category') # 'photo' ou 'video'
        tag_name = request.args.get('tag')
        index = request.args.get('index', 0, type=int)
        
        items_list = data.get(category, [])
        
        # Filtrer
        album_items = [i for i in items_list if tag_name in i['tags']]
        
        if not album_items or index < 0 or index >= len(album_items):
            return jsonify({'success': False, 'error': 'Index hors limites ou vide'})
            
        target_item = album_items[index]
        
        return jsonify({
            'success': True,
            'title': target_item['title'],
            'path': target_item['path'].replace('static/', ''), # Chemin relatif pour url_for static
            'index': index,
            'total': len(album_items)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/add_media', methods=['POST'])
def api_add_media():
    data = request.json
    category = data.get('category')
    filename = data.get('filename')
    tags = data.get('tags') # Ici on attend une liste ['rock', 'cool'] et non plus une string

    try:
        new_id = media_manager.add_media_file(category, filename, tags)
        return jsonify({'success': True, 'id': new_id})
    except Exception as e:
        print(f"Erreur API: {e}") # Debug dans la console
        return jsonify({'success': False, 'error': str(e)}), 400

# 2. API POUR MODIFIER LES TAGS D'UN FICHIER MÉDIA
@app.route('/api/update_file_tags', methods=['POST'])
def api_update_file_tags():
    try:
        data = request.json
        category = data.get('category')
        file_id = data.get('file_id')
        new_tags = data.get('tags') # Liste de tags

        db_data = load_data()
        files_list = db_data.get(category, [])

        # Trouver le fichier
        file_obj = next((f for f in files_list if str(f['id']) == str(file_id)), None)
        
        if file_obj:
            file_obj['tags'] = new_tags
            
            # Mise à jour des tags disponibles globaux (au cas où)
            current_cats = db_data['available_tags'].get(category, [])
            for t in new_tags:
                if t not in current_cats:
                    current_cats.append(t)
            current_cats.sort()
            db_data['available_tags'][category] = current_cats
            
            save_data(db_data)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Fichier introuvable'}), 404

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/bulk_update_file_tags', methods=['POST'])
def api_bulk_update_file_tags():
    try:
        data = request.json
        category = data.get('category')
        file_ids = data.get('file_ids', [])
        new_tags = data.get('tags', [])
        mode = data.get('mode', 'add') # 'add' (par défaut) ou 'replace'

        if not file_ids:
            return jsonify({'success': False, 'error': 'Aucun fichier sélectionné'}), 400

        db_data = load_data()
        files_list = db_data.get(category, [])
        target_ids = set(str(fid) for fid in file_ids)
        
        count = 0
        for f in files_list:
            if str(f['id']) in target_ids:
                current_tags = f.get('tags', [])
                
                if mode == 'replace':
                    # MODE REMPLACER : On écrase tout
                    f['tags'] = new_tags
                else:
                    # MODE AJOUTER : On fusionne (Anciens + Nouveaux, sans doublons)
                    # On utilise un set pour l'unicité, puis on repasse en liste
                    merged_tags = set(current_tags) | set(new_tags) # Opérateur Union
                    f['tags'] = sorted(list(merged_tags))
                
                count += 1
        
        # Mise à jour des tags disponibles globaux (au cas où on a créé des tags à la volée, 
        # même si ici on sélectionne depuis une liste existante)
        current_cats = db_data['available_tags'].get(category, [])
        for t in new_tags:
            if t not in current_cats:
                current_cats.append(t)
        current_cats.sort()
        db_data['available_tags'][category] = current_cats

        save_data(db_data)
        return jsonify({'success': True, 'count': count})

    except Exception as e:
        print(f"ERREUR BULK UPDATE: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
# --- 2. NOUVELLE API : ENREGISTRER DEPUIS L'INBOX ---
@app.route('/api/bulk_add_inbox', methods=['POST'])
def api_bulk_add_inbox():
    try:
        data = request.json
        category = data.get('category')
        filenames = data.get('filenames', [])
        tags = data.get('tags', [])

        db_data = load_data()
        
        src_dir = os.path.join('static', f'inbox_{category}')
        dest_dir_name = f"{category}s" if category != 'music' else 'music' # attention aux 's' selon tes dossiers
        dest_dir = os.path.join('static', dest_dir_name)
        os.makedirs(dest_dir, exist_ok=True)
        
        count = 0
        for original_filename in filenames:
            src_path = os.path.join(src_dir, original_filename)
            
            # --- LE BOUCLIER EST ICI ---
            # On nettoie le nom de fichier pour le web
            safe_filename = clean_filename(original_filename)
            dest_path = os.path.join(dest_dir, safe_filename)
            
            if os.path.exists(src_path):
                # 1. Déplacer ET renommer le fichier physique
                shutil.move(src_path, dest_path)
                
                # 2. Créer l'entrée JSON avec le nom propre
                new_id = 1
                if db_data.get(category):
                    new_id = max(f.get('id', 0) for f in db_data[category]) + 1
                    
                new_entry = {
                    "id": new_id,
                    "path": f"static/{dest_dir_name}/{safe_filename}", 
                    "tags": tags,
                    "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "title": safe_filename # On enregistre le nom propre !
                }
                
                if category not in db_data:
                    db_data[category] = []
                db_data[category].append(new_entry)
                count += 1
        
        # 3. Mise à jour des tags globaux
        current_cats = db_data['available_tags'].get(category, [])
        for t in tags:
            if t not in current_cats:
                current_cats.append(t)
        current_cats.sort()
        db_data['available_tags'][category] = current_cats
        
        save_data(db_data)
        return jsonify({'success': True, 'count': count})

    except Exception as e:
        print(f"ERREUR BULK INBOX: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/delete_media', methods=['POST'])
def api_delete_media():
    try:
        data = request.json
        category = data.get('category')
        file_id = data.get('file_id')

        db_data = load_data()
        items_list = db_data.get(category, [])
        
        # Trouver le fichier à supprimer
        item_to_delete = next((f for f in items_list if str(f['id']) == str(file_id)), None)

        if item_to_delete:
            # OPTIONNEL : Si tu veux aussi effacer le VRAI fichier du disque dur
            # file_path = item_to_delete.get('path')
            # if file_path and os.path.exists(file_path):
            #     os.remove(file_path)

            # Supprimer du JSON
            db_data[category] = [f for f in items_list if str(f['id']) != str(file_id)]
            save_data(db_data)
            
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Fichier introuvable'}), 404

    except Exception as e:
        print(f"ERREUR DELETE MEDIA: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# --- NOUVELLE API GÉNÉRIQUE : CRÉATION DE THÈME (POUR TOUT TYPE) ---
@app.route('/api/create_theme', methods=['POST'])
def api_create_theme():
    try:
        data = load_data()
        
        category = request.form.get('category')
        tag_name = request.form.get('tag_name').strip()
        music_file = request.form.get('music_file') # <-- AJOUT : On récupère la musique
        image_file = request.files.get('tag_image')
        
        if not category or not tag_name or not image_file:
            return jsonify({'success': False, 'error': 'Catégorie, Nom et Image requis'}), 400

        theme_key = f"{category}_themes"
        
        # Sauvegarde Image
        os.makedirs(THEME_FOLDER, exist_ok=True)
        ext = image_file.filename.split('.')[-1]
        safe_name = secure_filename(tag_name)
        image_filename = f"{category}_theme_{safe_name}.{ext}"
        image_file.save(os.path.join(THEME_FOLDER, image_filename))
        
        # Création de l'objet thème
        new_theme = {
            "name": tag_name,
            "img": image_filename
        }
        
        # AJOUT : Si une musique est choisie, on l'ajoute
        if music_file:
            new_theme["music"] = music_file

        # Mise à jour JSON
        if theme_key not in data:
            data[theme_key] = []
            
        # On vérifie si existe déjà pour écraser ou ajouter
        existing = next((t for t in data[theme_key] if t['name'] == tag_name), None)
        if existing:
            existing['img'] = image_filename
            if music_file: existing['music'] = music_file
        else:
            data[theme_key].append(new_theme)
            
        # Mise à jour tags disponibles
        if category not in data['available_tags']:
            data['available_tags'][category] = []
            
        if tag_name not in data['available_tags'][category]:
            data['available_tags'][category].append(tag_name)
            data['available_tags'][category].sort()

        save_data(data)
        
        return jsonify({'success': True, 'tag': tag_name})

    except Exception as e:
        print(f"ERREUR THEME {category}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
# --- FONCTION UTILITAIRE POUR RÉCUPÉRER LES THÈMES ---
def get_themes_for_category(data, category):
    """
    Récupère la liste des thèmes (Image + Nom).
    Si un tag existe dans les fichiers mais n'a pas de thème (image) défini,
    on crée un thème temporaire avec une image par défaut.
    """
    # 1. Thèmes configurés (avec images)
    configured_themes = data.get(f"{category}_themes", [])
    
    # 2. Tags réels utilisés dans les fichiers (pour ne rien oublier)
    # (On scanne les fichiers de la catégorie pour trouver tous les tags utilisés)
    used_tags = set()
    for item in data.get(category, []):
        for t in item.get('tags', []):
            used_tags.add(t)
            
    # 3. Fusion : On s'assure que tous les tags utilisés ont un objet thème
    final_themes = []
    
    # On ajoute d'abord ceux qui ont une belle image
    for theme in configured_themes:
        if theme['name'] in used_tags: # Optionnel : ne montrer que si utilisé ? Ou montrer tout ?
            final_themes.append(theme)
            if theme['name'] in used_tags:
                used_tags.remove(theme['name']) # Traité
        # Si on veut afficher les thèmes vides (créés mais sans fichiers), on laisse.
        # Ici on suppose qu'on affiche tout ce qui est configuré + le reste.
    
    # On ajoute les restants (ceux qui n'ont pas encore d'image configurée)
    for tag in used_tags:
        # On vérifie si le thème n'a pas déjà été ajouté (cas où le tag est dans themes mais pas matched par le remove)
        if not any(t['name'] == tag for t in final_themes):
            final_themes.append({'name': tag, 'img': 'default_theme.png'}) # Image grise par défaut
            
    # Tri alphabétique
    final_themes.sort(key=lambda x: x['name'])
    return final_themes

# --- NOUVELLE API CRÉATION HISTOIRE (MULTIPART/FILES) ---
# 2. MODIFIER L'API DE SAUVEGARDE (Gestion Mode Édition)
@app.route('/api/add_story_complex', methods=['POST'])
def api_add_story_complex():
    try:
        data = load_data()

        # Récupération de l'ID (s'il existe, c'est une modification)
        story_id = request.form.get('story_id')
        
        title = request.form.get('title')
        selected_tags = request.form.getlist('selected_tags')

        # Trouver l'ancienne histoire si on est en édition
        old_story = None
        if story_id:
            old_story = next((s for s in data['story'] if str(s['id']) == str(story_id)), None)

        # Gestion Cover
        cover_file = request.files.get('story_cover')
        cover_filename = "default_story.png"

        if cover_file and cover_file.filename != '':
            # Nouveau fichier uploadé
            ext = cover_file.filename.split('.')[-1]
            safe_title = secure_filename(title)
            filename = f"story_{safe_title}_cover_{random.randint(1000,9999)}.{ext}"
            cover_file.save(os.path.join(UPLOAD_FOLDER, filename))
            cover_filename = filename
        elif old_story:
            # Pas de nouveau fichier, on garde l'ancien
            cover_filename = old_story.get('cover', 'default_story.png')

        # Gestion Chapitres
        chapters = []
        index = 0
        while True:
            text_key = f'chapter_text_{index}'
            if text_key not in request.form:
                break
            
            chapter_text = request.form.get(text_key)
            
            # Gestion Audio Chapitre
            audio_file = request.files.get(f'chapter_audio_{index}')
            audio_filename = None
            
            if audio_file and audio_file.filename != '':
                # Nouveau fichier audio
                ext = audio_file.filename.split('.')[-1]
                safe_title = secure_filename(title)
                filename = f"{safe_title}_ch{index}_{random.randint(1000,9999)}.{ext}"
                audio_file.save(os.path.join(UPLOAD_FOLDER, filename))
                audio_filename = filename
            elif old_story and index < len(old_story.get('chapters', [])):
                # On garde l'ancien audio si le chapitre existait déjà
                audio_filename = old_story['chapters'][index].get('audio')

            chapters.append({
                'text': chapter_text,
                'audio': audio_filename
            })
            index += 1

        # Mise à jour des Tags Globaux
        current_story_tags = data['available_tags'].get('story', [])
        for t in selected_tags:
            if t not in current_story_tags:
                current_story_tags.append(t)
        data['available_tags']['story'] = sorted(current_story_tags)

        # Sauvegarde finale
        if old_story:
            # MISE À JOUR
            old_story['title'] = title
            old_story['cover'] = cover_filename
            old_story['chapters'] = chapters
            old_story['tags'] = selected_tags
            # On ne change pas la date de création ou l'ID
        else:
            # CRÉATION
            new_id = 1
            if data['story']:
                new_id = max(s['id'] for s in data['story']) + 1
            
            new_entry = {
                'id': new_id,
                'title': title,
                'cover': cover_filename,
                'chapters': chapters,
                'tags': selected_tags,
                'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            data['story'].append(new_entry)

        save_data(data)
        return jsonify({'success': True})

    except Exception as e:
        print(f"ERREUR CREATE STORY: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/update_theme', methods=['POST'])
def api_update_theme():
    try:
        data = load_data()
        
        category = request.form.get('category') # Maintenant gère 'story', 'writing', 'photo', 'video', 'music'
        old_name = request.form.get('old_name')
        new_name = request.form.get('new_name').strip()
        music_file = request.form.get('music_file')
        image_file = request.files.get('new_image')
        
        theme_key = f"{category}_themes"
        
        # 1. Gestion des clés spécifiques selon la catégorie
        if category == 'story':
            tags_key = 'story'
            item_key = 'story'
        elif category == 'writing':
            tags_key = 'writing_words'
            item_key = 'writing_words'
        else:
            # Pour photo, video, music
            tags_key = category
            item_key = category

        # 2. Trouver le thème à modifier
        themes = data.get(theme_key, [])
        theme_obj = next((t for t in themes if t['name'] == old_name), None)
        
        if not theme_obj:
            return jsonify({'success': False, 'error': 'Thème introuvable'}), 404

        # 3. Mise à jour de l'Image
        if image_file and image_file.filename != '':
            os.makedirs(THEME_FOLDER, exist_ok=True)
            ext = image_file.filename.split('.')[-1]
            safe_name = secure_filename(new_name)
            image_filename = f"{category}_theme_{safe_name}_{random.randint(100,999)}.{ext}"
            image_file.save(os.path.join(THEME_FOLDER, image_filename))
            theme_obj['img'] = image_filename

        # 4. Mise à jour de la Musique
        if music_file:
            theme_obj['music'] = music_file
        elif 'music' in theme_obj and not music_file: 
            del theme_obj['music']

        # 5. ASSURER LA PRÉSENCE DANS available_tags (même si on ne renomme pas)
        tag_list = data.get('available_tags', {}).get(tags_key, [])
        if new_name not in tag_list:
            tag_list.append(new_name)
            tag_list.sort()
            data['available_tags'][tags_key] = tag_list

        # 6. PROPAGATION GLOBALE DU CHANGEMENT DE NOM
        if new_name != old_name:
            if any(t['name'] == new_name for t in themes):
                return jsonify({'success': False, 'error': 'Ce nom de thème existe déjà !'}), 400
            
            theme_obj['name'] = new_name
            
            # A. Mise à jour de la liste 'available_tags' (déjà assurée ci-dessus, il s'agit juste de remplacer l'ancien)
            if old_name in tag_list:
                index = tag_list.index(old_name)
                tag_list[index] = new_name
                tag_list.sort()
                data['available_tags'][tags_key] = tag_list
                
            # B. Mise à jour de TOUTES les occurrences dans la base de données (Python CRUD)
            items = data.get(item_key, [])
            count_updated = 0
            for item in items:
                if 'tags' in item and old_name in item['tags']:
                    # On remplace l'ancien tag par le nouveau dans la liste
                    item['tags'] = [new_name if t == old_name else t for t in item['tags']]
                    count_updated += 1
            print(f"Renommé '{old_name}' -> '{new_name}' dans {count_updated} éléments de la catégorie {category}.")

        # 6. Sauvegarde définitive (Aucun JS, 100% logique Python sur le JSON comme demandé !)
        save_data(data)
        return jsonify({'success': True})

    except Exception as e:
        print(f"ERREUR UPDATE THEME: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# 3. API SUPPRESSION THÈME
@app.route('/api/delete_theme', methods=['POST'])
def api_delete_theme():
    try:
        data = load_data()
        category = request.json.get('category')
        tag_name = request.json.get('tag_name')
        
        theme_key = f"{category}_themes"
        tags_key = category if category == 'story' else 'writing_words'
        item_key = 'story' if category == 'story' else 'writing_words'

        # 1. Supprimer de la liste des thèmes (Objets)
        data[theme_key] = [t for t in data.get(theme_key, []) if t['name'] != tag_name]
        
        # 2. Supprimer de la liste available_tags
        if tag_name in data['available_tags'].get(tags_key, []):
            data['available_tags'][tags_key].remove(tag_name)
            
        # 3. NETTOYAGE : Enlever ce tag des histoires/mots qui le portaient
        items = data.get(item_key, [])
        for item in items:
            if 'tags' in item and tag_name in item['tags']:
                item['tags'].remove(tag_name)

        save_data(data)
        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
# 3. AJOUTER L'API DE SUPPRESSION D'HISTOIRE
@app.route('/api/delete_story', methods=['POST'])
def api_delete_story():
    try:
        story_id = request.json.get('id')
        data = load_data()
        
        # On filtre pour garder tout sauf cette histoire
        initial_len = len(data['story'])
        data['story'] = [s for s in data['story'] if str(s['id']) != str(story_id)]
        
        if len(data['story']) < initial_len:
            save_data(data)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Histoire introuvable'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/check_word', methods=['POST'])
def api_check_word():
    """Vérifie un mot soumis par la modale de lecture via AJAX"""
    data = request.json
    user_input = data.get('user_input', '').strip().upper()
    target_word = data.get('target_word', '').upper()

    # Logique de correction (Copie conforme de ton jeu)
    feedback = []
    is_correct = (user_input == target_word)
    max_len = max(len(target_word), len(user_input))
    
    for i in range(max_len):
        char_input = user_input[i] if i < len(user_input) else ""
        char_target = target_word[i] if i < len(target_word) else ""
        
        status = 'neutral'
        if char_input == char_target:
            status = 'correct'
        elif char_input != "" and char_target != "":
            status = 'wrong'
        elif char_input == "":
            status = 'missing'
        else:
            status = 'extra'

        feedback.append({
            'letter': char_input,
            'status': status
        })

    return jsonify({
        'success': is_correct,
        'feedback': feedback
    })
    
@app.route('/api/tags/<category>', methods=['GET'])
def api_get_tags(category):
    """Renvoie les tags disponibles pour cette catégorie"""
    tags = media_manager.get_tags(category)
    return jsonify(tags)

@app.route('/api/tags/create', methods=['POST'])
def api_create_tag():
    """Crée un nouveau tag global"""
    data = request.json
    category = data.get('category')
    new_tag = data.get('tag_name')
    
    if media_manager.create_tag(category, new_tag):
        return jsonify({'success': True, 'tags': media_manager.get_tags(category)})
    else:
        return jsonify({'success': False, 'message': 'Erreur ou tag existant'}), 400
    
# --- API POUR LE JEU D'ÉCRITURE ---

# 1. REMPLACER L'ANCIENNE ROUTE api_add_word PAR CELLE-CI
@app.route('/api/add_word', methods=['POST'])
def api_add_word():
    """Ajoute OU Modifie un mot"""
    data = request.json
    word_text = data.get('word').strip().upper() # On force en majuscule pour le jeu
    tags = data.get('tags')
    word_id = data.get('id') # S'il y a un ID, c'est une modif

    if not word_text:
        return jsonify({'success': False, 'error': 'Mot vide'}), 400

    try:
        db_data = load_data()
        words_list = db_data.get('writing_words', [])

        if word_id:
            # --- MODIFICATION ---
            word_obj = next((w for w in words_list if str(w['id']) == str(word_id)), None)
            if word_obj:
                word_obj['word'] = word_text
                word_obj['tags'] = tags
            else:
                return jsonify({'success': False, 'error': 'Mot introuvable'}), 404
        else:
            # --- CRÉATION ---
            # Vérifier si le mot existe déjà pour éviter les doublons (optionnel mais propre)
            if any(w['word'] == word_text for w in words_list):
                 return jsonify({'success': False, 'error': 'Ce mot existe déjà !'}), 400

            new_id = 1
            if words_list:
                new_id = max(w['id'] for w in words_list) + 1
            
            new_entry = {
                "id": new_id,
                "word": word_text,
                "tags": tags,
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            db_data['writing_words'].append(new_entry)

        save_data(db_data)
        return jsonify({'success': True})

    except Exception as e:
        print(f"❌ Erreur API Word: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
# 2. AJOUTER LA ROUTE DE SUPPRESSION
@app.route('/api/delete_word', methods=['POST'])
def api_delete_word():
    try:
        word_id = request.json.get('id')
        db_data = load_data()
        
        # On garde tout sauf le mot avec cet ID
        initial_len = len(db_data['writing_words'])
        db_data['writing_words'] = [w for w in db_data['writing_words'] if str(w['id']) != str(word_id)]
        
        if len(db_data['writing_words']) < initial_len:
            save_data(db_data)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Mot introuvable'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get_words', methods=['GET'])
def api_get_words():
    """Renvoie la liste de tous les mots au jeu"""
    try:
        words = media_manager.get_writing_words()
        return jsonify(words)
    except Exception as e:
        print(f"❌ Erreur récupération mots: {e}")
        return jsonify([]), 500
    
@app.route('/admin/memory')
def admin_memory():
    """Page de configuration du Memory (Admin seulement)"""
    data = load_data()
    config = data.get('memory_config', {"num_pairs": 6, "num_players": 1})
    return render_template('admin_memory.html', config=config)

@app.route('/admin/memory/save', methods=['POST'])
def save_memory_config():
    """Sauvegarde les préférences du Memory"""
    data = load_data()
    
    pairs = int(request.form.get('num_pairs'))
    players = int(request.form.get('num_players'))
    
    data['memory_config'] = {
        "num_pairs": pairs,
        "num_players": players
    }
    
    save_data(data)
    return redirect(url_for('admin_memory'))

# --- SECTION PUZZLE ---

PUZZLE_CACHE_FOLDER = 'static/cache/puzzle'

@app.route('/admin/puzzle')
def admin_puzzle():
    data = load_data()
    # Valeurs par défaut : 3x3 et mode "Click & Swap"
    config = data.get('puzzle_config', {"difficulty": 3, "mode": "swap"})
    return render_template('admin_puzzle.html', config=config)

@app.route('/admin/puzzle/save', methods=['POST'])
def save_puzzle_config():
    data = load_data()
    difficulty = int(request.form.get('difficulty'))
    mode = request.form.get('mode')
    
    data['puzzle_config'] = {
        "difficulty": difficulty,
        "mode": mode
    }
    save_data(data)
    return redirect(url_for('admin_puzzle'))

# --- DANS app.py ---

@app.route('/puzzle')
def puzzle_menu():
    """Menu choix image : n'affiche QUE les photos ayant le tag 'Puzzle'"""
    data = load_data()
    all_photos = data.get('photo', [])
    
    # On filtre les photos : on garde la photo seulement si le mot "puzzle" 
    # (en majuscule ou minuscule) se trouve dans ses tags.
    puzzle_photos = [
        p for p in all_photos 
        if any(tag.lower() == 'puzzle' for tag in p.get('tags', []))
    ]
    
    return render_template('puzzle_menu.html', photos=puzzle_photos)

@app.route('/puzzle/play/<int:photo_id>')
def puzzle_game(photo_id):
    data = load_data()
    
    # 1. Récupérer la config et la photo
    config = data.get('puzzle_config', {"difficulty": 3, "mode": "swap"})
    grid_size = config['difficulty'] # ex: 3 pour 3x3
    
    target_photo = next((p for p in data['photo'] if p['id'] == photo_id), None)
    if not target_photo: return "Photo introuvable", 404

    # 2. Préparer le dossier cache (Option A)
    # On vide le dossier cache pour ne pas mélanger avec l'ancien puzzle
    if os.path.exists(PUZZLE_CACHE_FOLDER):
        shutil.rmtree(PUZZLE_CACHE_FOLDER)
    os.makedirs(PUZZLE_CACHE_FOLDER)

    # 3. Traitement de l'image avec PIL
    # Chemin absolu de l'image source
    base_path = os.path.dirname(os.path.abspath(__file__))
    # On enlève le 'static/' du début s'il y est déjà pour construire le chemin absolu
    rel_path = target_photo['path']
    if rel_path.startswith('static/'):
        # os.path.join attend des chemins relatifs sans le premier slash parfois
        # Le plus simple est de construire le chemin complet
        image_path = os.path.join(base_path, rel_path)
    else:
        image_path = os.path.join(base_path, 'static', rel_path)

    try:
        img = Image.open(image_path)
    except FileNotFoundError:
        return f"Erreur: Impossible d'ouvrir l'image à {image_path}", 404

    # Convertit l'image en RGB pour supprimer la transparence (Alpha) qui fait planter le JPG
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        img = img.convert('RGB')

    # Même format modèle + grille : portrait / paysage / carré (max ~480px côté long)
    src_w, src_h = img.size
    max_side = 480
    if src_w >= src_h:
        # Paysage (ou carré)
        board_w = max_side
        board_h = max(grid_size * 40, int(round(max_side * src_h / src_w)))
    else:
        # Portrait
        board_h = max_side
        board_w = max(grid_size * 40, int(round(max_side * src_w / src_h)))

    # Dimensions multiples de la grille pour des pièces exactes
    board_w = max(grid_size, (board_w // grid_size) * grid_size)
    board_h = max(grid_size, (board_h // grid_size) * grid_size)
    target_size = (board_w, board_h)
    img = img.resize(target_size, Image.Resampling.LANCZOS)

    # Modèle = exactement la même image que la grille (pas l'original)
    model_filename = 'model.jpg'
    model_path = os.path.join(PUZZLE_CACHE_FOLDER, model_filename)
    img.save(model_path)
    model_src = f"cache/puzzle/{model_filename}"

    # 4. Découpage
    tile_w = board_w // grid_size
    tile_h = board_h // grid_size
    pieces = []

    for row in range(grid_size):
        for col in range(grid_size):
            left = col * tile_w
            top = row * tile_h
            tile = img.crop((left, top, left + tile_w, top + tile_h))
            filename = f"piece_{row}_{col}.jpg"
            tile.save(os.path.join(PUZZLE_CACHE_FOLDER, filename))
            pieces.append({
                'src': f"cache/puzzle/{filename}",
                'correct_pos': f"{row}-{col}",
                'id': f"tile-{row}-{col}"
            })

    # 5. Mélange
    random.shuffle(pieces)

    orientation = 'landscape' if board_w >= board_h else 'portrait'
    if board_w == board_h:
        orientation = 'square'

    return render_template('puzzle_game.html',
                           pieces=pieces,
                           grid_size=grid_size,
                           mode=config['mode'],
                           original_image=model_src,
                           board_w=board_w,
                           board_h=board_h,
                           tile_w=tile_w,
                           tile_h=tile_h,
                           orientation=orientation)

if __name__ == '__main__':
    app.run(debug=True, port=5000)