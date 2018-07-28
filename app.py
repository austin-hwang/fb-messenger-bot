import os
import sys
import json
import random
from datetime import datetime
import schedule
import apiai

import requests
from flask import Flask, request

CLIENT_ACCESS_TOKEN = "e6a80cb21ef64a4e8bec7a6b050c2ebd"
ai = apiai.ApiAI(CLIENT_ACCESS_TOKEN)

app = Flask(__name__)

def select_compliment():
    with open('./compliments.txt') as text:
        return random.choice(text.readlines()).strip()

@app.route('/', methods=['GET'])
def verify():
    # when the endpoint is registered as a webhook, it must echo back
    # the 'hub.challenge' value it receives in the query arguments
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200


@app.route('/', methods=['POST'])
def webhook():

    # endpoint for processing incoming messaging events

    data = request.get_json()
    log(data)  # you may not want to log every incoming message in production, but it's good for testing

    if data["object"] == "page":

        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:

                if messaging_event.get("message"):  # someone sent us a message

                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    message_text = messaging_event["message"]["text"]  # the message's text

                    # prepare API.ai request
                    req = ai.text_request()
                    req.lang = 'en'  # optional, default value equal 'en'
                    req.query = message_text

                    # get response from API.ai
                    api_response = req.getresponse()
                    responsestr = api_response.read().decode('utf-8')
                    response_obj = json.loads(responsestr)
                    if 'result' in response_obj:
                        response = response_obj["result"]["fulfillment"]["speech"]
                        send_message(sender_id, response)
                    
                    # profile = requests.get("https://graph.facebook.com/v2.6/" + sender_id + "?access_token=" + os.environ["PAGE_ACCESS_TOKEN"])
                    if message_text.lower() == 'subscribe':
                        with open('./db.txt', 'ra') as database:
                            users = database.readlines()
                            if not any(sender_id in u.strip() for u in users):
                                database.write(sender_id + '\n')
                    elif message_text.lower() == 'unsubscribe':
                        with open('./db.txt', 'ra') as database:
                            users = database.readlines()
                            if any(sender_id in u.strip() for u in users):
                                index = users.index(sender_id)
                                del users[index]
                                for id in users:
                                    database.write(sender_id + '\n')
                    elif 'compliment' in message_text.lower():
                        send_message(sender_id, select_compliment())

                if messaging_event.get("delivery"):  # delivery confirmation
                    pass

                if messaging_event.get("optin"):  # optin confirmation
                    pass

                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    pass

    return "ok", 200


def send_message(recipient_id, message_text):

    log("sending message to {recipient}: {text}".format(recipient=recipient_id, text=message_text))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        print r.text
        log(r.status_code)
        # log(r.text)
    if r.status_code == 200:
        print "This is working correctly"

def log(msg, *args, **kwargs):  # simple wrapper for logging to stdout on heroku
    try:
        if type(msg) is dict:
            msg = json.dumps(msg)
        else:
            msg = unicode(msg).format(*args, **kwargs)
        print u"{}: {}".format(datetime.now(), msg)
    except UnicodeEncodeError:
        pass  # squash logging errors in case of non-ascii text
    sys.stdout.flush()

if __name__ == '__main__':
    app.run(debug=True)
