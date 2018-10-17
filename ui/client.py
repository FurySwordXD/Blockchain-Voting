from flask import Flask, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

ip = 'localhost'
ip = input('Enter IP of a node: ')
port = 5001
port = int(input('Enter port of a node: '))

@app.route("/")
def index():
    return render_template("client.html",ipaddress=ip,port=port)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5010)