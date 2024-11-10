from flask import Flask, render_template, request, jsonify
from algosdk import mnemonic, account, transaction
from algosdk.v2client import algod
import time
import random

app = Flask(__name__)


def create_algod_client():
    algod_address = "https://testnet-api.algonode.cloud"
    algod_token = ""
    algod_client = algod.AlgodClient(algod_token, algod_address)
    return algod_client


hardcoded_accounts = [
    {
        "mnemonic": "history tuna elbow response glass ribbon sing leisure discover fold warrior arrow hurt grid gravity garden lizard impulse tired divorce bulk flower skill able joke",
        "address": "4MMK35CO2ISYD4TPY5ZRUWNDUJ3MXCIM6AVGNNEBZWD2VCZM4E4JVX2CF4"
    },
    {
        "mnemonic": "know option trigger viable cart install lawn indicate lemon steel job heart alley prosper stamp left above wool shrimp punch ginger walnut angry abstract bright",
        "address": "YRQFF5PSX2HS6PZ75TWAISFST2XROUVYUQRPK5ZXU7SNN7QWGTBPFJXSSQ"
    },
    {
        "mnemonic": "prepare news spider fuel require harbor december inside melody drum daring bitter mad twin rail scissors clog oven grit above unknown garden unknown abstract arctic",
        "address": "VI7NU5WFYUPOKPSC3RGY7OZNWK3YHSZF4D5Y3S2XBCLJG5UY6Y4K3D2PU4"
    },
    {
        "mnemonic": "february hat menu fee birth grab rich name hood solid eyebrow narrow figure sniff race midnight apart enforce electric exhaust ecology coyote spatial above garbage",
        "address": "VKAWCU7XS2WG7KU5N2XAR5UU5SQGJUGIBMUQ25KYW6K4WMCRQQAUPGA3VU"
    },
    {
        "mnemonic": "river great eyebrow true disagree obtain credit time tackle unknown stadium wall hood cabbage liquid dilemma reward dish hurt opinion rain simple picture absorb today",
        "address": "BMSL2ZRZJ2DXNSVKDZITFRUFNOO24BIQHV2DDVI7SM3UW5B5RQH3KQZ7NI"
    }
]

hardcoded_stokvel_account = {
    "address": "4GK46635MKFBCOPAY2BFC5MDOVRDLQ6YFJ2VAI5GOPWSBNHIMDGCP3E6XY"
}

hardcoded_stokvel_group = {
    "name": "Community Stokvel",
    "members": [account["address"] for account in hardcoded_accounts],
    "contributions": {account["address"]: 0.0 for account in hardcoded_accounts}
}

algod_client = create_algod_client()


def get_private_key(address):
    for account in hardcoded_accounts:
        if account["address"] == address:
            return mnemonic.to_private_key(account["mnemonic"])
    return None


def wait_for_confirmation(client, txid, timeout=10):
    start_time = time.time()
    while True:
        try:
            status = client.pending_transaction_info(txid)
            if status.get("confirmed-round") and status["confirmed-round"] > 0:
                return status
        except Exception as e:
            if time.time() - start_time > timeout:
                raise Exception("Transaction confirmation timeout")
        time.sleep(1)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    accounts = [account['address'] for account in hardcoded_accounts]
    accounts.append(hardcoded_stokvel_account["address"])
    return jsonify(accounts)


@app.route('/api/contribute', methods=['POST'])
def contribute():
    data = request.json
    address = data['address']
    amount = int(float(data['amount']) * 1000000)  # Convert to microAlgos
    private_key = get_private_key(address)

    if not private_key:
        return jsonify({"error": "Invalid address"}), 400

    try:
        params = algod_client.suggested_params()
        txn = transaction.PaymentTxn(address, params, hardcoded_stokvel_account["address"], amount)
        signed_txn = txn.sign(private_key)
        tx_id = algod_client.send_transaction(signed_txn)
        wait_for_confirmation(algod_client, tx_id)

        hardcoded_stokvel_group["contributions"][address] += amount / 1000000

        return jsonify({"message": "Contribution successful"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/transfer', methods=['POST'])
def transfer():
    data = request.json
    from_address = data['fromAddress']
    to_address = data['toAddress']
    amount = int(float(data['amount']) * 1000000)  # Convert to microAlgos
    private_key = get_private_key(from_address)

    if not private_key:
        return jsonify({"error": "Invalid from address"}), 400

    try:
        params = algod_client.suggested_params()
        txn = transaction.PaymentTxn(from_address, params, to_address, amount)
        signed_txn = txn.sign(private_key)
        tx_id = algod_client.send_transaction(signed_txn)
        wait_for_confirmation(algod_client, tx_id)
        return jsonify({"message": "Transfer successful"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/simulate', methods=['POST'])
def simulate_cycle():
    try:
        for month in range(1, 6):
            print(f"\n--- Month {month} ---")

            for member in hardcoded_stokvel_group["members"]:
                contribute_amount = 1000000  # 1 Algo in microAlgos
                private_key = get_private_key(member)
                params = algod_client.suggested_params()
                txn = transaction.PaymentTxn(member, params, hardcoded_stokvel_account["address"], contribute_amount)
                signed_txn = txn.sign(private_key)
                tx_id = algod_client.send_transaction(signed_txn)
                wait_for_confirmation(algod_client, tx_id)
                hardcoded_stokvel_group["contributions"][member] += 1  # 1 Algo

            selected_member = hardcoded_stokvel_group["members"][month - 1]
            payout_amount = int(0.60 * 1000000 * 5)  # 60% of total deposits in microAlgos

            params = algod_client.suggested_params()
            txn = transaction.PaymentTxn(hardcoded_stokvel_account["address"], params, selected_member, payout_amount)
            private_key = get_private_key(hardcoded_stokvel_group["members"][0])
            signed_txn = txn.sign(private_key)
            tx_id = algod_client.send_transaction(signed_txn)
            wait_for_confirmation(algod_client, tx_id)

            print(f"Payout of {payout_amount / 1000000} Algos to {selected_member} completed.")

        return jsonify({"message": "Simulation completed successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/account_details', methods=['GET'])
def get_account_details():
    address = request.args.get('address')
    if address == 'stokvel':
        address = hardcoded_stokvel_account["address"]

    try:
        account_info = algod_client.account_info(address)
        balance = account_info['amount'] / 1000000  # Convert microAlgos to Algos

        transactions = []
        try:
            txn_params = {
                "address": address,
                "limit": 10,
                "txtype": "pay"
            }
            txn_response = algod_client.search_transactions(**txn_params)
            for txn in txn_response['transactions']:
                txn_type = "Receive" if txn['payment-transaction']['receiver'] == address else "Send"
                amount = txn['payment-transaction']['amount'] / 1000000
                date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(txn['round-time']))
                transactions.append({
                    "type": txn_type,
                    "amount": amount,
                    "date": date
                })
        except Exception as txn_error:
            print(f"Error fetching transactions: {txn_error}")

        return jsonify({
            "balance": balance,
            "transactions": transactions
        })
    except Exception as e:
        print(f"Error in get_account_details: {e}")
        return jsonify({"error": str(e), "balance": 0, "transactions": []}), 400


if __name__ == '__main__':
    app.run(debug=True)