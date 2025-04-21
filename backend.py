from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import requests
from bs4 import BeautifulSoup
import re
import schedule
import time
import threading
import smtplib
from email.message import EmailMessage

app = Flask(__name__)
CORS(app)  # 🔓 Autorise les requêtes depuis Flutter Web

FICHIER_ALERTES = "alertes.json"

# Charger les alertes existantes
def charger_alertes():
    if os.path.exists(FICHIER_ALERTES):
        with open(FICHIER_ALERTES, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# Sauvegarder les alertes dans le fichier
def sauvegarder_alertes():
    with open(FICHIER_ALERTES, "w", encoding="utf-8") as f:
        json.dump(alertes, f, indent=2, ensure_ascii=False)

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
    return jsonify({'message': 'Alerte ajoutée avec succès', 'alerte': alerte}), 201

@app.route('/alertes', methods=['GET'])
def lister_alertes():
    return jsonify(alertes)

# Scraper le prix actuel
def obtenir_prix_actuel(lien):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
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

# 💌 Envoi d’e-mail
def envoyer_email(destinataire, sujet, message):
    EMAIL = "dan.berekia@gmail.com"
    MOT_DE_PASSE = "fwtssbyckzziubvq"  # mot de passe d'application

    try:
        msg = EmailMessage()
        msg.set_content(message)
        msg['Subject'] = sujet
        msg['From'] = EMAIL
        msg['To'] = destinataire

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL, MOT_DE_PASSE)
            smtp.send_message(msg)

        print("✅ Email envoyé avec succès !")
    except Exception as e:
        print(f"❌ Erreur en envoyant l'email : {e}")

# Vérification automatique
def verification_automatique():
    print("🕒 Vérification automatique...")
    with app.app_context():
        resultats = verifier_alertes().get_json()

    if resultats:
        print("⚠️ Alertes déclenchées :")
        for a in resultats:
            print(f" - {a['lien']} ➝ {a['prix_actuel']} € ≤ {a['prix_cible']} €")
            envoyer_email(
                destinataire="dan.berekia@gmail.com",
                sujet="🔔 Alerte de prix atteinte !",
                message=f"Produit : {a['lien']}\nPrix actuel : {a['prix_actuel']} €\nPrix cible : {a['prix_cible']} €"
            )
    else:
        print("✅ Aucune alerte à déclencher.")

# Scheduler
def lancer_scheduler():
    schedule.every(1).minutes.do(verification_automatique)
    while True:
        schedule.run_pending()
        time.sleep(60)

# ▶️ Démarrage
if __name__ == '__main__':
    t = threading.Thread(target=lancer_scheduler)
    t.daemon = True
    t.start()
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=True)
