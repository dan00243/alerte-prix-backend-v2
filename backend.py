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
CORS(app)  # ✅ Pour autoriser les requêtes depuis Flutter Web

FICHIER_ALERTES = "alertes.json"
EMAIL = "dan.berekia@gmail.com"
MOT_DE_PASSE = "fwtssbyckzziubvq"  # ❗ Ton mot de passe d'application Gmail

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

# ✅ Initialisation
alertes = charger_alertes()

@app.route('/')
def accueil():
    return "🚀 Serveur Alerte de Prix en ligne !"

@app.route('/ajouter_alerte', methods=['POST'])
def ajouter_alerte():
    data = request.json
    lien = data.get('lien')
    prix = data.get('prix')
    if not lien or prix is None:
        return jsonify({'message': '❌ Données manquantes'}), 400

    alerte = {'lien': lien, 'prix': prix}
    alertes.append(alerte)
    sauvegarder_alertes()
    return jsonify({'message': '✅ Alerte ajoutée avec succès', 'alerte': alerte}), 201

@app.route('/alertes', methods=['GET'])
def voir_alertes():
    return jsonify(alertes), 200

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
            return float(prix_match.group(1).replace(",", "."))
        return None
    except Exception as e:
        print(f"❌ Erreur scraping : {e}")
        return None

def envoyer_email(destinataire, lien, prix_actuel, prix_cible):
    try:
        msg = EmailMessage()
        msg['Subject'] = "🔔 Alerte de prix atteinte !"
        msg['From'] = EMAIL
        msg['To'] = destinataire

        contenu_html = f"""
        <html>
            <body style="font-family: Arial; line-height: 1.6;">
                <h2 style="color: #2e6c80;">🔔 Alerte de prix atteinte !</h2>
                <p><strong>Produit :</strong> <a href="{lien}" target="_blank">{lien}</a></p>
                <p><strong>Prix actuel :</strong> <span style="color:green;">{prix_actuel} €</span></p>
                <p><strong>Prix souhaité :</strong> <span style="color:red;">{prix_cible} €</span></p>
                <p>🎯 C'est le moment d'acheter !</p>
            </body>
        </html>
        """
        msg.set_content("Votre alerte a été déclenchée.")
        msg.add_alternative(contenu_html, subtype='html')

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL, MOT_DE_PASSE)
            smtp.send_message(msg)

        print("✅ Email HTML envoyé !")
    except Exception as e:
        print(f"❌ Erreur en envoyant l'email : {e}")

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
            envoyer_email(
                destinataire=EMAIL,
                lien=lien,
                prix_actuel=prix_actuel,
                prix_cible=prix_cible
            )
    return jsonify(alertes_trouvees), 200

# 🔁 Scheduler toutes les minutes
def lancer_scheduler():
    schedule.every(1).minutes.do(lambda: verifier_alertes())
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    t = threading.Thread(target=lancer_scheduler)
    t.daemon = True
    t.start()
    port = int(os.environ.get('PORT', 5000))  # ✅ Port dynamique pour Render
    app.run(host='0.0.0.0', port=port)
