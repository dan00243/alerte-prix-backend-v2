from flask import Flask, request, jsonify
from flask_cors import CORS
import json, os, requests, re, threading, smtplib, schedule, time
from bs4 import BeautifulSoup
from email.message import EmailMessage
import uuid

app = Flask(__name__)
CORS(app)

FICHIER_ALERTES = "alertes.json"
EMAIL = "dan.berekia@gmail.com"
MOT_DE_PASSE = "fwtssbyckzziubvq"

def charger_alertes():
    if os.path.exists(FICHIER_ALERTES):
        with open(FICHIER_ALERTES, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def sauvegarder_alertes():
    with open(FICHIER_ALERTES, "w", encoding="utf-8") as f:
        json.dump(alertes, f, indent=2, ensure_ascii=False)

alertes = charger_alertes()

@app.route('/')
def accueil():
    return "🚀 Serveur Alerte de Prix en ligne !"

@app.route('/add_alert', methods=['POST'])
def add_alert():
    data = request.json
    alert = {
        "id": str(uuid.uuid4()),
        "name": data.get("name"),
        "url": data.get("url"),
        "target_price": data.get("target_price")
    }
    with open(FICHIER_ALERTES, "r", encoding="utf-8") as f:
        alerts = json.load(f)
    alerts.append(alert)
    with open(FICHIER_ALERTES, "w", encoding="utf-8") as f:
        json.dump(alerts, f, indent=4)
    return jsonify({"message": "Alerte ajoutée"}), 200

@app.route('/get_alerts', methods=['GET'])
def get_alerts():
    try:
        with open(FICHIER_ALERTES, "r", encoding="utf-8") as f:
            alerts = json.load(f)
        return jsonify(alerts)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/delete_alert', methods=['POST'])
def delete_alert():
    data = request.json
    alert_id = data.get("id")
    try:
        with open(FICHIER_ALERTES, "r", encoding="utf-8") as f:
            alerts = json.load(f)
        alerts = [a for a in alerts if a.get("id") != alert_id]
        with open(FICHIER_ALERTES, "w", encoding="utf-8") as f:
            json.dump(alerts, f, indent=4)
        return jsonify({"message": "Alerte supprimée"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def obtenir_prix_actuel(lien):
    try:
        headers = { "User-Agent": "Mozilla/5.0" }
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

@app.route('/verifier', methods=['GET'])
def verifier_alertes():
    alertes_trouvees = []
    for alerte in alertes:
        lien = alerte.get("url") or alerte.get("lien")
        prix_cible = alerte.get("target_price") or alerte.get("prix")
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

def envoyer_email(destinataire, lien, prix_actuel, prix_cible):
    try:
        msg = EmailMessage()
        msg['Subject'] = "🔔 Alerte de prix atteinte !"
        msg['From'] = EMAIL
        msg['To'] = destinataire
        contenu_html = f"""
        <html><body>
        <h2>🔔 Alerte de prix atteinte !</h2>
        <p>Produit : <a href="{lien}">{lien}</a></p>
        <p>Prix actuel : <strong>{prix_actuel} €</strong></p>
        <p>Prix souhaité : <strong>{prix_cible} €</strong></p>
        </body></html>
        """
        msg.set_content("Votre alerte a été déclenchée.")
        msg.add_alternative(contenu_html, subtype='html')
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL, MOT_DE_PASSE)
            smtp.send_message(msg)
        print("✅ Email envoyé !")
    except Exception as e:
        print(f"❌ Erreur email : {e}")

def lancer_scheduler():
    schedule.every(1).minutes.do(lambda: verifier_alertes())
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    t = threading.Thread(target=lancer_scheduler)
    t.daemon = True
    t.start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
