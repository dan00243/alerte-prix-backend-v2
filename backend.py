from flask import Flask, request, jsonify
import json
import os
import requests
from bs4 import BeautifulSoup
import re
import schedule
import threading
import time
import smtplib
from email.message import EmailMessage

app = Flask(__name__)
FICHIER_ALERTES = "alertes.json"

# Charger les alertes
def charger_alertes():
    if os.path.exists(FICHIER_ALERTES):
        with open(FICHIER_ALERTES, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# Sauvegarder les alertes
def sauvegarder_alertes():
    with open(FICHIER_ALERTES, "w", encoding="utf-8") as f:
        json.dump(alertes, f, indent=2, ensure_ascii=False)

# Initialiser les alertes
alertes = charger_alertes()

@app.route('/')
def home():
    return "Serveur d'Alerte de Prix - En ligne ✅"

@app.route('/ajouter_alerte', methods=['POST'])
def ajouter_alerte():
    data = request.json
    lien = data.get('lien')
    prix = data.get('prix')

    if not lien or prix is None:
        return jsonify({'message': 'Données manquantes'}), 400

    alerte = {'lien': lien, 'prix': prix}
    alertes.append(alerte)
    sauvegarder_alertes()
    return jsonify({'message': 'Alerte ajoutée', 'alerte': alerte}), 201

@app.route('/alertes', methods=['GET'])
def lister_alertes():
    return jsonify(alertes)

def obtenir_prix_actuel(lien):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        response = requests.get(lien, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        texte = soup.get_text()
        prix_match = re.search(r"(\d{1,5}[.,]\d{2})", texte)
        if prix_match:
            return float(prix_match.group(1).replace(',', '.'))
        return None
    except Exception as e:
        print(f"Erreur scraping : {e}")
        return None

@app.route('/verifier', methods=['GET'])
def verifier_alertes():
    alertes_trouvees = []
    for alerte in alertes:
        lien = alerte['lien']
        prix_cible = alerte['prix']
        prix_actuel = obtenir_prix_actuel(lien)
        if prix_actuel is not None and prix_actuel <= prix_cible:
            alertes_trouvees.append({
                'lien': lien,
                'prix_actuel': prix_actuel,
                'prix_cible': prix_cible
            })
    return jsonify(alertes_trouvees)

# Envoi email (désactivé ici par défaut)
def envoyer_email(destinataire, sujet, message):
    EMAIL = "ton_email@gmail.com"
    MDP = "mot_de_passe_application"
    try:
        msg = EmailMessage()
        msg.set_content(message)
        msg['Subject'] = sujet
        msg['From'] = EMAIL
        msg['To'] = destinataire

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL, MDP)
            smtp.send_message(msg)

        print("✅ Email envoyé !")
    except Exception as e:
        print(f"❌ Erreur email : {e}")

def verification_automatique():
    print("🕒 Vérification automatique...")
    with app.app_context():
        resultats = verifier_alertes().get_json()

    if resultats:
        print("⚠️ Alertes déclenchées :")
        for a in resultats:
            print(f"- {a['lien']} ➝ {a['prix_actuel']} € ≤ {a['prix_cible']} €")
            # envoyer_email(...)  # à activer si besoin
    else:
        print("✅ Aucune alerte déclenchée.")

def lancer_scheduler():
    schedule.every(10).minutes.do(verification_automatique)
    while True:
        schedule.run_pending()
        time.sleep(60)

# Lancer le scheduler en arrière-plan
t = threading.Thread(target=lancer_scheduler)
t.daemon = True
t.start()

# ✅ Lancement pour Render avec port dynamique
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Render définit PORT=10000
    app.run(host='0.0.0.0', port=port)
