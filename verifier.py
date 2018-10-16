from flask import Flask,jsonify
from json import load
from flask_cors import CORS

with open('valid_aids_file.json', 'r') as aids_file:
    valid_aids = load(aids_file)
with open('valid_parties.json', 'r') as parties_file:
    valid_parties= load(parties_file)

app = Flask(__name__)
CORS(app)

@app.route('/aids/<int:aid>', methods= ['GET'])
def verify_aadhar(aid):
    return jsonify(
        {
            'valid': aid in valid_aids['aids'],   
        }
    )

@app.route('/party/<party>', methods= ['GET'])
def verify_party(party):
    return jsonify(
        {
            'valid': party in valid_parties['parties'],   
        }
    )

if __name__ == '__main__':
    app.run(debug=True)