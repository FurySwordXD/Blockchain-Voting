import random
import hashlib, json 
import requests
from urllib.parse import urlparse
from textwrap import dedent
from uuid import uuid4
from flask import Flask , jsonify , request, render_template
from time import time
from flask_cors import CORS

class Blockchain():
    def __init__(self):
        self.chain = []
        self.current_transactions= []
        self.nodes = set()
        #genesis block
        self.new_block(previous_hash=1, proof=100)

    def new_block(self, proof , previous_hash=None):
        block ={
            'index': len(self.chain) + 1 ,
            'timestamp' : time(), 
            'transactions': self.current_transactions,
            'proof' : proof, 
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }
        self.current_transactions=[]
        self.chain.append(block)
        return block

    def new_transaction(self, voter_aid, party):
        self.current_transactions.append(
            {
                'voter_aid': voter_aid,
                'party': party,
            }
        )
        return self.last_block['index']+1

    @staticmethod
    def hash(block):
        block_string = json.dumps(block , sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1] 
    def proof_of_work(self , last_proof):
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof+=1
        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:5]== '00000'

    def register_node(self , address, flag):
        parsed_url = urlparse(address)
        if flag == 1:
            self.trigger_flood_nodes(address)
            for node in self.nodes:
                node = "http://" + node
                requests.post(url=f'http://{parsed_url.netloc}/nodes/register', json={
                    'nodes': [node],
                    'flag': 0
                })
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self , chain):
        last_block = chain[0]
        for current_index in range(1 , len(chain)):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print('\n----------\n')
            if block['previous_hash']!=self.hash(last_block):
                return False
            if not self.valid_proof(last_block['proof'] , block['proof']):
                return False
            last_block = block
        else:
            return True

    def resolve_conflicts(self):
        neighbours = self.nodes
        new_chain = None
        max_length = len(self.chain)
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')
            if response.status_code ==200:
                length = response.json()['length']
                chain = response.json()['chain']
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain
        if new_chain:
            self.chain = new_chain
            return True
        return False

    def triggered_flood_chain(self):
        for node in self.nodes:
            requests.get(f'http://{node}/nodes/resolve')

    def trigger_flood_nodes(self,address):
        print('flooding now ')
        for node in self.nodes:
            requests.post(url=f'http://{node}/nodes/register', json={
                'nodes': [address] ,
                'flag': 0
            })

    def tally_votes(self):
        votes = {}
        for block in self.chain:
            for i in block['transactions']:
                if i['party'] not in votes:
                    print('no there ' , i)
                    votes[i['party']]=1
                else :
                    votes[i['party']]+=1
        return jsonify(votes)
            
    def verify_vote(self, voter_aid):
        for block in self.chain:
            for i in block['transactions'] :
                print(i)
                if i['voter_aid']==str(voter_aid):
                    return { 'message' : i['party'] }
        else:
            return {'message' : "No vote found"}
    
    def redundancy(self,voter_aid):
        for block in self.chain:
            for i in block['transactions']:
                if i['voter_aid'] == str(voter_aid):
                    return True
        else:
            return False


# Flask API code here

app = Flask(__name__)
node_identifier = str(uuid4()).replace('-', '')

CORS(app)
blockchain = Blockchain()

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/mine', methods= ['GET'])
def mine():
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message' : "New Block Forged",
        'index': block['index'] , 
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    blockchain.triggered_flood_chain()
    return jsonify(response) , 200


@app.route('/transactions', methods=['GET'])
def full_transactions():
    return jsonify({
        'transactions': blockchain.current_transactions
    })

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    required = ['voter_aid', 'party']
    party_response = requests.get(f"http://localhost:5000/party/{values['party']}").json()
    aid_response = requests.get(f"http://localhost:5000/aids/{values['voter_aid']}").json()
    if not all(k in values for k in required):
        return 'missing values' , 400
    if not party_response['valid'] or not aid_response['valid']:
        return 'invalid aadhar id or party', 400
    if blockchain.redundancy(values['voter_aid']):
        return jsonify({'message': 'You have already voted.'})

    index = blockchain.new_transaction(values['voter_aid'] , values['party'])
    response = {'message' : f'Transaction will be added to Block {index} '}
    return jsonify(response) , 201

@app.route('/chain' , methods=['GET'])
def full_chain():
    response={
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

@app.route('/nodes', methods=['GET'])
def full_nodes():
    return jsonify({
        'nodes': list(blockchain.nodes)
    })

@app.route('/nodes/register', methods= ['POST'])
def register_nodes():
    values = request.get_json()
    nodes = values.get('nodes')
    flag = values.get('flag')
    print(flag)
    if nodes is None:
        return 'Error: Please supply a valid list of nodes' , 400
    for node in nodes:
        blockchain.register_node(node, flag)
    response = {
        'message' : 'new nodes have been added', 
        'total_nodes': list(blockchain.nodes)
    }
    blockchain.resolve_conflicts()
    return jsonify(response) , 201

@app.route('/tally', methods=['GET'])
def tally_votes():
    return blockchain.tally_votes()

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain,
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain,
        }
    return jsonify(response), 200

@app.route('/verify/<int:aid>', methods = ['GET'])
def verify_vote(aid):
    print(blockchain.verify_vote(aid))
    return jsonify(blockchain.verify_vote(aid))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=random.randint(5001,5009), debug=True)