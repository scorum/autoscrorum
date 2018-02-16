from graphenebase import operations
from graphenebase.account import PublicKey
from autoscorum.node import chain_params


def transfer_operation(_from, to, amount, memo):
    return operations.Transfer(
        **{"from": _from,
           "to": to,
           "amount": '{:.{prec}f} {asset}'.format(
               float(amount),
               prec=chain_params["scorum_prec"],
               asset=chain_params["scorum_symbol"]
           ),
           "memo": memo
           })


def transfer_to_vesting_operation(_from, to, amount):
    return operations.TransferToVesting(
        **{'from': _from,
           'to': to,
           'amount': '{:.{prec}f} {asset}'.format(
               float(amount),
               prec=chain_params["scorum_prec"],
               asset=chain_params["scorum_symbol"]
           )
           })


def account_create_operation(creator: str,
                             fee: float,
                             name: str,
                             owner: str,
                             active: str,
                             posting: str,
                             memo,
                             json_meta,
                             additional_owner_accounts,
                             additional_active_accounts,
                             additional_posting_accounts,
                             additional_owner_keys,
                             additional_active_keys,
                             additional_posting_keys):
    creation_fee = '{:.{prec}f} {asset}'.format(
                   float(fee if fee else 0.000000750),
                   prec=chain_params["scorum_prec"],
                   asset=chain_params["scorum_symbol"])

    owner_pubkey = PublicKey(owner)
    active_pubkey = PublicKey(active if active else owner)
    posting_pubkey = PublicKey(posting if posting else owner)
    memo_pubkey = PublicKey(memo)

    owner_key_authority = [[str(owner_pubkey), 1]]
    active_key_authority = [[str(active_pubkey), 1]]
    posting_key_authority = [[str(posting_pubkey), 1]]
    owner_accounts_authority = []
    active_accounts_authority = []
    posting_accounts_authority = []

    for k in additional_owner_keys:
        owner_key_authority.append([k, 1])
    for k in additional_active_keys:
        active_key_authority.append([k, 1])
    for k in additional_posting_keys:
        posting_key_authority.append([k, 1])

    for k in additional_owner_accounts:
        owner_accounts_authority.append([k, 1])
    for k in additional_active_accounts:
        active_accounts_authority.append([k, 1])
    for k in additional_posting_accounts:
        posting_accounts_authority.append([k, 1])
    return operations.AccountCreate(
        **{'fee': creation_fee,
           'creator': creator,
           'new_account_name': name,
           'owner': {'account_auths': owner_accounts_authority,
                     'key_auths': owner_key_authority,
                     'weight_threshold': 1},
           'active': {'account_auths': active_accounts_authority,
                      'key_auths': active_key_authority,
                      'weight_threshold': 1},
           'posting': {'account_auths': posting_accounts_authority,
                       'key_auths': posting_key_authority,
                       'weight_threshold': 1},
           'memo_key': str(memo_pubkey),
           'json_metadata': json_meta}
    )


def account_witness_vote_operation(account, witness, approve):
    return operations.AccountWitnessVote(
        **{'account': account,
           'witness': witness,
           'approve': approve}
    )