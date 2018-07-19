from autoscorum.wallet import Wallet
import json
import logging

from graphenebase.amount import Amount

from multiprocessing import Pool
from functools import partial


BLOG_START = 2297977
FIRST_POST = 2325074
FIFA_BLOCK_NUM = 3303003

# reward operations
O_AUTHOR_REWARD = "author_reward"
O_BENEFACTOR_REWARD = "comment_benefactor_reward"
O_COMMENT_REWARD = "comment_reward"
O_CURATION_REWARD = "curation_reward"
OPS = [O_AUTHOR_REWARD, O_BENEFACTOR_REWARD, O_CURATION_REWARD, O_COMMENT_REWARD]
OPS_REWARDS = {
    O_AUTHOR_REWARD: "reward",
    O_CURATION_REWARD: "reward",
    O_COMMENT_REWARD: "commenting_reward",
    O_BENEFACTOR_REWARD: "reward"
}
OPS_ACCS = {
    O_AUTHOR_REWARD: "author",
    O_CURATION_REWARD: "comment_author",
    O_COMMENT_REWARD: "author",
    O_BENEFACTOR_REWARD: "author"
}

# CHAIN_ID = "d3c1f19a4947c296446583f988c43fd1a83818fabaf3454a0020198cb361ebd2"
# DR_BEFORE = "rpc1-testnet-v2.scorum.com:8001"
CHAIN_ID = "db4007d45f04c1403a7e66a5c66b5b1cdfc2dde8b5335d1d2f116d592ca3dbb1"
# ADDR_BEFORE = "localhost:11092"
# ADDR_BEFORE = "rpc1-mainnet-weu-v2.scorum.com:8001"
# ADDR_AFTER = ADDR_BEFORE

ADDR_BEFORE = "192.168.100.10:8093"
ADDR_AFTER = "192.168.100.10:8091"


def get_fifa_pool(chain_id, address):
    with Wallet(chain_id, address) as wallet:
        return Amount(wallet.get_chain_capital()["content_reward_fifa_world_cup_2018_bounty_fund_sp_balance"])


def list_accounts(chain_id, address):
    with Wallet(chain_id, address) as wallet:
        limit = 100
        names = []
        last = ""
        while True:
            accs = wallet.list_accounts(limit, last)
            last = accs[-1]
            names += accs
            if len(accs) < limit:
                break
        logging.info("Total accs; %d" % len(names))
        return names


def get_accounts(names, chain_id, address):
    with Wallet(chain_id, address) as wallet:
        return [{"name": a["name"], "scorumpower": a["scorumpower"]} for a in wallet.get_accounts(names)]


def get_account_net_rshares(account, chain_id, address):
    with Wallet(chain_id, address) as wallet:
        start_permlink = None
        last_permlink = None
        author_posts = []
        limit = 100
        acc_net_shares = 0
        while True:
            discussions = wallet.get_discussions_by(
                "author", **{"start_author": account["name"], "limit": limit, "start_permlink": start_permlink}
            )
            author_posts += discussions
            acc_net_shares += sum([int(d["net_rshares"]) for d in discussions if int(d["net_rshares"]) > 0])
            if len(discussions) < limit or (start_permlink and start_permlink == last_permlink):
                break
            last_permlink = start_permlink
            start_permlink = discussions[-1]["permlink"]
        logging.debug(
            "Author: %s, posts and comments: %d, net_rshares: %d." %
            (account["name"], len(author_posts), acc_net_shares)
        )
        account.update({"net_rshares": acc_net_shares})
        return account, author_posts


def get_fifa_rewards(accounts, chain_id, adddress):
    for name in accounts:
        rewards = {r: Amount("0 SP") for r in OPS}
        accounts[name].update({"rewards": rewards})
    fund_sum = Amount("0 SP")
    with Wallet(chain_id, adddress) as w:
        for num, data in w.get_ops_in_block(FIFA_BLOCK_NUM):
            operation = data["op"][0]
            if operation in OPS:
                name = data["op"][1][OPS_ACCS[operation]]
                if name not in accounts:
                    continue
                reward = data["op"][1][OPS_REWARDS[operation]]
                logging.debug(name, operation, reward)
                accounts[name]["rewards"][operation] += Amount(reward)
            if operation == O_COMMENT_REWARD:
                fund_sum += Amount(data["op"][1]["fund_reward"])
    logging.info("Fund reward sum: %s", str(fund_sum))
    return accounts, fund_sum


def get_accounts_history(account, chain_id, address):
    with Wallet(chain_id, address) as wallet:
        limit = 100
        start_from = -1
        rewards = {r: Amount("0 SP") for r in OPS}
        while True:
            records = wallet.get_account_history(account["name"], start_from, limit)
            for num, data in records:
                operation = data["op"][0]
                if operation in OPS:
                    rewards[operation] += Amount(data["op"][1][OPS_REWARDS[operation]])
            start_from = min([num for num, _ in records] or [0])
            if len(records) < limit or len(records) < 100 or not start_from:  # or records[0][1]["block"] < FIRST_POST:
                break
            if start_from < limit:
                limit = start_from
        rewards.update({"sum": sum(rewards.values(), Amount("0 SP"))})
        if rewards["sum"].amount > 0:
            logging.info(
                "Name: %s, rewards: author %s, comment %s, curator %s, benefactor %s, sum %s",
                account["name"], str(rewards[O_AUTHOR_REWARD]), str(rewards[O_COMMENT_REWARD]),
                str(rewards[O_CURATION_REWARD]), str(rewards[O_BENEFACTOR_REWARD]), str(rewards["sum"])
            )

        account.update({"rewards": rewards})
        return account


def load_from_file(path):
    with open(path, "r") as f:
        return json.loads(f.read())


def save_to_file(path, data):
    with open(path, "w") as f:
        f.write(json.dumps(data))


def percentage(a: int, b: int):
    return "%.2f%%" % round((a / b) * 100, 9)


def make_checks(accounts_before, accounts_after, fifa_pool, accs_to_reward, total_net_rshares):
    differences = []

    sum_reward = Amount("0 SP")
    sum_balance_diff = Amount("0 SP")

    for name in accounts_before.keys():
        sp_before = Amount(accounts_before[name]["scorumpower"])
        if not accounts_after.get(name):
            continue
        sp_after = Amount(accounts_after[name]["scorumpower"])
        balance_diff = sp_after - sp_before
        balance_percent = percentage(balance_diff.amount, fifa_pool.amount)
        rshares_percent = percentage(accounts_before[name]["net_rshares"], total_net_rshares)
        sum_balance_diff += balance_diff
        reward = accounts_after[name]["rewards"][O_AUTHOR_REWARD]
        reward_percent = percentage(reward.amount, fifa_pool.amount)
        sum_reward += reward

        if name not in accs_to_reward and balance_diff > Amount("1.000000000 SP"):
            logging.warning(
                "Balance of account without reward has changed too much: '%s', before '%s', after '%s'",
                name, str(sp_before), str(sp_after)
            )
        if name not in accs_to_reward and reward.amount != 0:
            logging.error("Unexpected reward for '%s', amount '%s'", name, str(reward))

        if name in accs_to_reward and not balance_diff.amount:
            logging.warning(
                "Account has not received reward: '%s', expected +'%s'",
                name, str(reward)
            )
        if name in accs_to_reward and (
                balance_diff - reward > Amount("1.000000000 SP") or reward - balance_diff > Amount("1.000000000 SP")
        ):
            logging.warning(
                "Balance change differs too much from reward: '%s', '%s'",
                str(balance_diff), str(reward)
            )

        differences.append(
            {
                "account": name,
                "sp_before": str(sp_before), "sp_after": str(sp_after),
                "balance_diff": str(balance_diff), "balance_percent": balance_percent,
                "reward": str(reward), "reward_percent": reward_percent,
                "rshares_percent": rshares_percent
            }
        )
        logging.debug(
            "%s: balance %s, rewards %s, rshares %s" % (name, balance_percent, reward_percent, rshares_percent)
        )

    if sum_reward != fifa_pool:
        logging.error(
            "Sum of rewards is not equal to fifa pool! Sum is '%s', expected '%s'",
            str(sum_reward), str(fifa_pool)
        )

    if sum_balance_diff != fifa_pool:
        logging.warning(
            "Sum of differences of accounts balances is not equal to fifa pool. Sum is '%s', expected '%s'",
            str(sum_reward), str(fifa_pool)
        )

    save_to_file("differences.json", differences)
    return differences


def main():
    logging.basicConfig(
        level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S",
        format="%(asctime)s.%(msecs)03d (%(name)s) %(levelname)s - %(message)s" 
    )
    names = list_accounts(CHAIN_ID, ADDR_BEFORE)
    logging.info("Collecting data before payment.")
    accounts_before = get_accounts(names, CHAIN_ID, ADDR_BEFORE)
    p = Pool(processes=20)
    accounts_posts = p.map(partial(get_account_net_rshares, chain_id=CHAIN_ID, address=ADDR_BEFORE), accounts_before)
    p.close()

    accounts_before = []
    posts_before = []
    for acc, posts in accounts_posts:
        accounts_before.append(acc)
        posts_before += posts

    logging.info("Total posts and comments: %d", len(posts_before))
    save_to_file("posts_before.json", posts_before)

    total_net_rshares = sum([a["net_rshares"] for a in accounts_before])
    logging.info("Total net_rshares: %d", total_net_rshares)

    accs_to_reward = [a["name"] for a in accounts_before if a["net_rshares"] > 0]
    logging.info("%d acounts to reward: %s", len(accs_to_reward), accs_to_reward)

    accounts_before = {a["name"]: a for a in accounts_before}
    save_to_file("accounts_before.json", accounts_before)

    fifa_pool_before = get_fifa_pool(CHAIN_ID, ADDR_BEFORE)
    logging.info("Fifa pool before: %s" % fifa_pool_before)

    logging.info("Collecting data after payment.")
    accounts_after = {a["name"]: a for a in get_accounts(names, CHAIN_ID, ADDR_AFTER)}
    accounts_after, fund_sum = get_fifa_rewards(accounts_after, CHAIN_ID, ADDR_AFTER)
    save_to_file("accounts_after.json", accounts_after)

    if fund_sum != fifa_pool_before:
        logging.error(
            "Sum of fund rewards do not equal with fifa pool: '%s', expected '%s'" %
            (str(fund_sum), str(fifa_pool_before))
        )

    fifa_pool_after = get_fifa_pool(CHAIN_ID, ADDR_AFTER)
    logging.info("Fifa pool after: %s" % fifa_pool_after)

    if fifa_pool_after.amount < 0:
        logging.error("Fifa pool after payment is negative: %s", str(fifa_pool_after))

    diffs = make_checks(accounts_before, accounts_after, fifa_pool_before, accs_to_reward, total_net_rshares)
    logging.info("Sum of rshare percents: %.2f%%", sum([float(d["rshares_percent"].split('%')[0]) for d in diffs]))
    save_to_file("sorted_net_rshares_percents.json", sorted({d["rshares_percent"]: d["account"] for d in diffs}))


if __name__ == "__main__":
    main()
