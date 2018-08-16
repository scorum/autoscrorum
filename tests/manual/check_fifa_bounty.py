import csv
import json
import logging
from collections import defaultdict
from copy import deepcopy

from sortedcontainers import SortedSet

from src.wallet import Wallet
from src.utils import to_date
from graphenebase.amount import Amount

# CHAIN_ID = "d3c1f19a4947c296446583f988c43fd1a83818fabaf3454a0020198cb361ebd2"  # testnet
CHAIN_ID = "db4007d45f04c1403a7e66a5c66b5b1cdfc2dde8b5335d1d2f116d592ca3dbb1"  # mainnet


def get_chain_capital(address):
    with Wallet(CHAIN_ID, address) as wallet:
        return wallet.get_chain_capital()


def get_dynamic_global_properties(address):
    with Wallet(CHAIN_ID, address) as wallet:
        return wallet.get_dynamic_global_properties()


def get_fifa_pool(address):
    fifa_pool = Amount(get_chain_capital(address)["content_reward_fifa_world_cup_2018_bounty_fund_sp_balance"])
    logging.info("Fifa pool: '%s'" % str(fifa_pool))
    return fifa_pool


def get_total_net_rhsres(posts_to_be_rewarded, all_posts):
    total_net_rshares = 0
    for name in posts_to_be_rewarded:
        net_rshares = int(all_posts[name]["net_rshares"])
        if net_rshares > 0:
            total_net_rshares += net_rshares
    logging.info("Total net_rshares: %d", total_net_rshares)
    return total_net_rshares


def list_all_accounts(address):
    with Wallet(CHAIN_ID, address) as wallet:
        return wallet.list_all_accounts()


def get_accounts(names, address):
    with Wallet(CHAIN_ID, address) as wallet:
        accounts = wallet.get_accounts(names)
        logging.info("Total number of accounts; %d" % len(accounts))
        return {a["name"]: a for a in accounts}


def get_posts(address):
    with Wallet(CHAIN_ID, address) as wallet:
        posts = {"%s:%s" % (p["author"], p["permlink"]): p for p in wallet.get_posts_and_comments()}
        logging.info("Total number of posts and comments: %d", len(posts))
        return posts


def get_operations_in_block(address, num):
    with Wallet(CHAIN_ID, address) as w:
        operations = w.get_ops_in_block(num, 2)
        save_to_file("all_operations.json", operations)
        return operations


def get_fifa_operations(operations, cashout_posts):
    fifa_ops = []
    additional_ops = []
    for num, data in operations:
        op = data["op"][0]
        if op != "comment_reward":
            continue
        addr = "%s:%s" % (data["op"][1]["author"], data["op"][1]["permlink"])
        if addr in cashout_posts:
            cashout_posts.remove(addr)
            additional_ops.append([num, data])
        else:
            fifa_ops.append([num, data])
    save_to_file("fifa_operations.json", fifa_ops)
    if cashout_posts:
        logging.critical(cashout_posts)
    if additional_ops:
        save_to_file("additional_operations.json", additional_ops)
        fund_sum = Amount("0 SP")
        author_sum = Amount("0 SP")
        for num, data in additional_ops:
            fund_sum += Amount(data["op"][1]["fund_reward"])
            author_sum += Amount(data["op"][1]["author_reward"])
        logging.info("Additional rewards: fund '%s', author '%s' ", str(fund_sum), str(author_sum))
    return fifa_ops, additional_ops


def calc_accounts_actual_rewards(accounts, operations):
    for _, acc in accounts.items():
        acc["actual_reward"] = Amount("0 SP")
    op_num = 0
    op_sum = Amount("0 SP")
    missed_accs = set()
    for num, data in operations:
        name = data["op"][1]["author"]
        if name not in accounts:
            missed_accs.add(name)
            continue
        accounts[name]["actual_reward"] += Amount(data["op"][1]["author_reward"])
        op_sum += Amount(data["op"][1]["author_reward"])
        op_num += 1
    if missed_accs:
        logging.error("Unexpected '%d' author_reward operations for accs: %s", missed_accs)
    logging.info("Total number of author_reward operations: %d, reward sum: '%s'", op_num, str(op_sum))


def calc_posts_actual_rewards(posts, operations):
    for _, post in posts.items():
        post.update({"actual_reward": Amount("0 SP"), "commenting_reward": Amount("0 SP")})
    op_num = 0
    fund_sum = Amount("0 SP")
    commenting_sum = Amount("0 SP")
    missed_posts = set()
    for num, data in operations:
        author = data["op"][1]["author"]
        permlink = data["op"][1]["permlink"]
        address = "%s:%s" % (author, permlink)
        if address not in posts:
            missed_posts.add(address)
            continue
        posts[address]["actual_reward"] += Amount(data["op"][1]["fund_reward"])
        fund_sum += Amount(data["op"][1]["fund_reward"])
        posts[address]["commenting_reward"] += Amount(data["op"][1]["commenting_reward"])
        commenting_sum += Amount(data["op"][1]["commenting_reward"])
        op_num += 1
    if missed_posts:
        logging.error("Unexpected '%d' comment_reward operation for posts: %s", len(missed_posts), missed_posts)
    logging.info(
        "Total number of comment_reward operations: %d, fund_reward sum: '%s', commenting_reward sum: '%s'",
        op_num, str(fund_sum), str(commenting_sum)
    )


def load_from_file(path):
    with open(path, "r") as f:
        return json.loads(f.read())


def save_to_file(path, data):
    with open(path, "w") as f:
        f.write(json.dumps(data))


def comparison_str(expected: Amount, actual: Amount):
    delta = expected - actual
    percent = "%.2f%%" % round((actual.amount / expected.amount) * 100, 9) if expected.amount else "inf%"
    return "actual '%s', expected '%s', delta '%s', percent '%s'" % (str(actual), str(expected), str(delta), percent)


def percentage(dividend, divisor, precision=5):
    return "%.{}f%%".format(precision) % (100 * dividend / divisor) if divisor else "inf%"


def _add_parent_posts(base_posts, all_posts):
    # sort base ports by depth (from children to parents)
    base_posts = SortedSet(base_posts, key=lambda k: int(all_posts[k]["depth"]) * -1)
    # add all missing parents
    i = 0
    while True:
        address = base_posts[i]
        parent_author = all_posts[address]["parent_author"]
        if not parent_author:
            break
        parent_permlink = all_posts[address]["parent_permlink"]
        base_posts.add(value="%s:%s" % (parent_author, parent_permlink))
        i += 1
    # check that order is correct
    for i in range(1, len(base_posts)):
        curr = base_posts[i]
        prev = base_posts[i - 1]
        assert all_posts[curr]["depth"] <= all_posts[prev]["depth"], "Order of comments to reward is not correct."
    return base_posts


def find_posts_to_be_rewarded(posts):
    posts_to_be_rewarded = [
        address for address, post in posts.items()
        if int(post["net_rshares"]) > 0
        and to_date(post["cashout_time"]) < to_date("2018-08-08T12:00:00")
    ]

    posts_to_be_rewarded = _add_parent_posts(posts_to_be_rewarded, posts)
    logging.info("Expected amount of posts and comments to be rewarded: %d", len(posts_to_be_rewarded))
    return posts_to_be_rewarded


def find_cashout_posts(posts):
    # for these posts expected other rewards in addition to fifa
    cashout_posts = [
        addr for addr, post in posts.items()
        if to_date("1970-01-01T00:00:00") < to_date(post["cashout_time"]) < to_date("2018-08-08T12:00:00")
        and int(post["net_rshares"]) > 0
    ]
    cashout_posts = _add_parent_posts(cashout_posts, posts)
    logging.info("Amount of cashout posts: %d", len(cashout_posts))
    return cashout_posts


def calc_expected_rewards(posts_to_be_rewarded, posts, accounts, fifa_pool):
    total_net_rshares = get_total_net_rhsres(posts_to_be_rewarded, posts)
    total_posting_rewards = sum([Amount(a["posting_rewards_sp"]) for a in accounts.values()], Amount("0 SP"))
    params = {"is_reward_expected": False, "expected_reward": Amount("0 SP"), "comment_reward": Amount("0 SP")}
    for account in accounts.values():
        account.update(deepcopy(params))
        exp_posting_reward = Amount("0 SP")
        acc_posting_rewards = Amount(account["posting_rewards_sp"])
        exp_posting_reward["amount"] = int(fifa_pool.amount * acc_posting_rewards.amount / total_posting_rewards.amount)
        account.update({"expected_posting_reward": exp_posting_reward})
    for post in posts.values():
        post.update(deepcopy(params))
    authors_to_be_rewarded = set()
    for addr in posts_to_be_rewarded:
        posts[addr]["is_reward_expected"] = True
        post_reward = Amount("0 SP")
        net_rshares = int(posts[addr]["net_rshares"])
        if net_rshares > 0:
            post_reward["amount"] = int(fifa_pool.amount * net_rshares / total_net_rshares)
            posts[addr]["expected_reward"] = post_reward
        author = posts[addr]["author"]
        authors_to_be_rewarded.add(author)
        comment_reward = posts[addr].get("comment_reward", Amount("0 SP"))
        author_reward = (post_reward + comment_reward) / 2
        accounts[author]["expected_reward"] += author_reward
        accounts[author]["is_reward_expected"] = True

        parent_author = posts[addr]["parent_author"]
        if parent_author:
            parent_permlink = posts[addr]["parent_permlink"]
            parent_addr = "%s:%s" % (parent_author, parent_permlink)
            posts[parent_addr]["comment_reward"] += author_reward
        else:
            # e.g. it is post (root), so whole reward receive author
            accounts[author]["expected_reward"] += author_reward

    logging.info("Expected amount of accounts to be rewarded: %d", len(authors_to_be_rewarded))


def check_comments_expected_reward_sum_equal_to_fifa_pull_size(posts, fifa_pool):
    fund_sum = Amount("0 SP")
    for post in posts.values():
        fund_sum += post["expected_reward"]
    msg = "Sum of expected fund rewards for posts is not equal to fifa pool: %s" % \
          comparison_str(fifa_pool, fund_sum)
    # assert Amount("-0.005 SP") <= fund_sum - fifa_pool <= Amount("0.005 SP"), msg
    if Amount("-0.000005 SP") <= fund_sum - fifa_pool <= Amount("0.000005 SP"):
        return
    logging.error(msg)


def check_comments_actual_reward_sum_equal_to_fifa_pull_size(posts, fifa_pool):
    fund_sum = Amount("0 SP")
    for post in posts.values():
        fund_sum += post["actual_reward"]
    msg = "Sum of actual fund rewards is not equal to fifa pool: %s" % \
          comparison_str(fifa_pool, fund_sum)
    # assert Amount("-0.005 SP") <= fund_sum - fifa_pool <= Amount("0.005 SP"), msg
    if Amount("-0.000005 SP") <= fund_sum - fifa_pool <= Amount("0.000005 SP"):
        return
    logging.error(msg)


def check_accounts_expected_reward_sum_equal_to_fifa_pool_size(accounts, fifa_pool):
    reward_sum = Amount("0 SP")
    for name in accounts.keys():
        reward_sum += accounts[name]["expected_reward"] + accounts[name]["comment_reward"]
    msg = "Sum of expected rewards for all accounts is not equal to fifa pool: %s" % \
          comparison_str(fifa_pool, reward_sum)
    # assert reward_sum == fifa_pool, msg
    if reward_sum == fifa_pool:
        logging.info("check_accounts_expected_reward_sum_equal_to_fifa_pool_size - OK")
        return
    logging.error(msg)


def check_accounts_actual_reward_sum_equal_to_fifa_pool_size(accounts, fifa_pool):
    reward_sum = Amount("0 SP")
    for name in accounts.keys():
        reward_sum += accounts[name]["actual_reward"]
    msg = "Sum of actual rewards for all accounts is not equal to fifa pool: %s" % \
          comparison_str(fifa_pool, reward_sum)
    # assert reward_sum == fifa_pool, msg
    if reward_sum == fifa_pool:
        logging.info("check_accounts_actual_reward_sum_equal_to_fifa_pool_size - OK")
        return
    logging.error(msg)


def check_accounts_sp_gain_equal_to_fifa_pool_size(accounts_before, accounts_after, fifa_pool):
    total_gain = Amount("0 SP")
    for name in accounts_before.keys():
        sp_before = Amount(accounts_before[name]["scorumpower"])
        sp_after = Amount(accounts_after[name]["scorumpower"])
        total_gain += sp_after - sp_before
    msg = "Amount of sp balance gain is not equal to fifa pool: %s" % \
          comparison_str(fifa_pool, total_gain)
    # assert total_gain == fifa_pool, msg
    if total_gain == fifa_pool:
        logging.info("check_sum_of_authors_sp_balance_gain_equal_to_fifa_pool_size - OK")
        return
    logging.error(msg)


def check_fifa_pool_after_distribution_equal_zero(fifa_pool):
    msg = "Fifa pool after payment is not equal to zero: %s" % str(fifa_pool)
    # assert fifa_pool == Amount("0 SP"), msg
    if fifa_pool == Amount("0 SP"):
        logging.info("check_fifa_pool_after_distribution_equal_zero - OK")
        return
    logging.error(msg)


def check_accounts_scr_balance_has_not_changed(accounts_before, accounts_after):
    errors = 0
    for name in accounts_before.keys():
        scr_before = Amount(accounts_before[name]["balance"])
        scr_after = Amount(accounts_after[name]["balance"])
        msg = "Amount of SCR balance has changed for '%s'" % name
        # assert scr_after - scr_before == Amount("0 SCR"), msg
        if scr_after - scr_before == Amount("0 SCR"):
            continue
        logging.error(msg)
        errors += 1
    if not errors:
        logging.info("check_accounts_scr_balance_has_not_changed - OK")


def check_balances_of_expected_accounts_increased(accounts_before, accounts_after):
    errors = 0
    for name in accounts_before.keys():
        gain = Amount(accounts_after[name]["scorumpower"]) - Amount(accounts_before[name]["scorumpower"])
        is_reward_expected = accounts_before[name]["is_reward_expected"]
        if is_reward_expected:
            msg = "Balance of '%s' account has not changed (gain expected)." % name
            # assert gain > Amount("0 SP"), msg
            if gain > Amount("0 SP"):
                continue
            logging.error(msg)
            errors += 1
    if not errors:
        logging.info("check_balances_of_expected_accounts_increased - OK")


def check_balances_of_expected_accounts_not_increased(accounts_before, accounts_after):
    errors = 0
    for name in accounts_before.keys():
        gain = Amount(accounts_after[name]["scorumpower"]) - Amount(accounts_before[name]["scorumpower"])
        is_reward_expected = accounts_before[name]["is_reward_expected"]
        if not is_reward_expected:
            msg = "Balance of '%s' unexpectedly has changed on '%s'." % (name, str(gain))
            # assert Amount("0 SP") <= gain < Amount("1.000000000 SP"), msg
            if Amount("0 SP") <= gain < Amount("1.000000000 SP"):
                continue
            logging.error(msg)
            errors += 1
    if not errors:
        logging.info("check_balances_of_expected_accounts_not_increased - OK")


def check_accounts_fund_reward_distribution(accounts_before, accounts_after):
    errors = 0
    for name in accounts_before.keys():
        expected = accounts_before[name]["expected_reward"]
        actual = accounts_after[name]["actual_reward"]
        msg = "Account actual and expected rewards are not equal: %s, name '%s'" % \
              (comparison_str(expected, actual), name)
        # assert Amount("-0.000005 SP") <= actual - expected <= Amount("0.000005 SP"), msg
        if Amount("-0.000005 SP") <= actual - expected <= Amount("0.000005 SP"):
            continue
        logging.error(msg)
        errors += 1
    if not errors:
        logging.info("check_accounts_fund_reward_distribution - OK")


def check_posts_fund_reward_distribution(posts_before, posts_after):
    errors = 0
    for address in posts_before.keys():
        expected = posts_before[address]["expected_reward"]
        actual = posts_after[address]["actual_reward"]
        msg = "Post actual and expected rewards are not equal: %s, author_permlink '%s'" % \
              (comparison_str(expected, actual), address)
        if Amount("-0.000005 SP") <= actual - expected <= Amount("0.000005 SP"):
            continue
        logging.error(msg)
        errors += 1
    if not errors:
        logging.info("check_posts_fund_reward_distribution - OK")


def check_expected_posts_received_reward(posts_before, posts_after):
    posts_to_reward = set(address for address in posts_before if posts_before[address]["is_reward_expected"])
    rewarded_posts = set(
        address for address in posts_after
        if posts_after[address]["actual_reward"] > Amount("0 SP")
        or posts_after[address]["commenting_reward"] > Amount("0 SP")
    )
    missing = posts_to_reward.difference(rewarded_posts)
    if missing:
        logging.error("Missing comment_reward_operations for %d posts: %s", len(missing), missing)
    unexpected = rewarded_posts.difference(posts_to_reward)
    if unexpected:
        logging.error("Unexpected comment_reward_operations for %d posts: %s", len(unexpected), unexpected)
    if not missing and not unexpected:
        logging.info("check_expected_posts_received_reward - OK")


def check_expected_accounts_received_reward(accounts_before, accounts_after):
    accs_to_reward = set(name for name in accounts_before if accounts_before[name]["is_reward_expected"])
    rewarded_authors = set(name for name in accounts_after if accounts_after[name]["actual_reward"] > Amount("0 SP"))
    missing = accs_to_reward.difference(rewarded_authors)
    if missing:
        logging.error("Missing author_reward_operations for %d accounts: %s", len(missing), missing)
    unexpected = rewarded_authors.difference(accs_to_reward)
    if unexpected:
        logging.error("Unexpected author_reward_operations for %d accounts: %s", len(unexpected), unexpected)
    if not missing and not unexpected:
        logging.info("check_expected_accounts_received_reward - OK")


def write_posts_stats(posts, fifa_pool):
    with open("fifa_posts_result.csv", "w") as csvfile:
        authors_payouts = defaultdict(Amount)
        writer = csv.writer(csvfile, delimiter=";")
        writer.writerow([
            "author", "actual_reward_by_net_rshares_distribution", "fifa_percent", "post_author_payout",
            "payout_percent", "net_rshares", "permlink"
        ])
        for addr, post in posts.items():
            reward = post["expected_reward"]
            if reward > Amount("0 SP"):
                fifa_percent = percentage(reward.amount, fifa_pool.amount)
                author, permlink = addr.split(":")
                author_payout = Amount(post["author_payout_sp_value"])
                payout_percent = percentage(reward.amount, author_payout.amount)
                writer.writerow([
                    author, str(reward), fifa_percent, str(author_payout), payout_percent,
                    int(post["net_rshares"]), permlink
                ])
                authors_payouts[author] += author_payout
        return authors_payouts


def write_accounts_stats(accounts, authors_payouts, fifa_pool):
    with open("fifa_accounts_result.csv", "w") as csvfile:
        writer = csv.writer(csvfile, delimiter=";")
        writer.writerow([
            "name", "actual_reward_by_net_rshares_distribution", "fifa_percent", "author_posts_payouts",
            "payout_percent",
            "balance_before_fifa", "gain_percent", "potential_reward_by_sp_distribution", "exp_posting_percent"
        ])
        for name, acc in accounts.items():
            reward = acc["expected_reward"]
            if reward > Amount("0 SP"):
                fifa_percent = percentage(reward.amount, fifa_pool.amount)
                author_payout = authors_payouts[name]
                payout_percent = percentage(reward.amount, author_payout.amount)
                balance = Amount(acc["scorumpower"])
                gain_percent = percentage(reward.amount, balance.amount)
                exp_posting_reward = acc["expected_posting_reward"]
                exp_posting_percent = percentage(exp_posting_reward.amount, fifa_pool.amount)
                writer.writerow([
                    name, str(reward), fifa_percent, str(author_payout), payout_percent, str(balance), gain_percent,
                    exp_posting_reward, exp_posting_percent
                ])


def main(addr_before, addr_after, fifa_block):
    names = list_all_accounts(addr_before)
    accounts_before = get_accounts(names, addr_before)
    posts_before = get_posts(addr_before)
    posts_to_be_rewarded = find_posts_to_be_rewarded(posts_before)
    cashout_posts = find_cashout_posts(posts_before)
    fifa_pool_before = get_fifa_pool(addr_before)
    calc_expected_rewards(posts_to_be_rewarded, posts_before, accounts_before, fifa_pool_before)
    save_to_file("posts_before.json", posts_before)
    save_to_file("accounts_before.json", accounts_before)

    logging.info("Collecting data after fifa payment.")
    ops = get_operations_in_block(addr_after, fifa_block)
    fifa_operations, additional_ops = get_fifa_operations(ops, cashout_posts)
    accounts_after = get_accounts(names, addr_after)
    calc_accounts_actual_rewards(accounts_after, fifa_operations)
    save_to_file("accounts_after.json", accounts_after)
    posts_after = get_posts(addr_after)
    calc_posts_actual_rewards(posts_after, fifa_operations)
    save_to_file("posts_after.json", posts_after)
    fifa_pool_after = get_fifa_pool(addr_after)

    check_fifa_pool_after_distribution_equal_zero(fifa_pool_after)

    check_expected_posts_received_reward(posts_before, posts_after)
    check_comments_expected_reward_sum_equal_to_fifa_pull_size(posts_before, fifa_pool_before)
    check_comments_actual_reward_sum_equal_to_fifa_pull_size(posts_after, fifa_pool_before)
    check_posts_fund_reward_distribution(posts_before, posts_after)

    check_expected_accounts_received_reward(accounts_before, accounts_after)
    check_accounts_expected_reward_sum_equal_to_fifa_pool_size(accounts_before, fifa_pool_before)
    check_accounts_actual_reward_sum_equal_to_fifa_pool_size(accounts_after, fifa_pool_before)
    check_accounts_fund_reward_distribution(accounts_before, accounts_after)
    check_accounts_sp_gain_equal_to_fifa_pool_size(accounts_before, accounts_after, fifa_pool_before)
    check_accounts_scr_balance_has_not_changed(accounts_before, accounts_after)
    check_balances_of_expected_accounts_increased(accounts_before, accounts_after)
    check_balances_of_expected_accounts_not_increased(accounts_before, accounts_after)

    payouts = write_posts_stats(posts_before, fifa_pool_before)
    write_accounts_stats(accounts_before, payouts, fifa_pool_before)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S",
        format="%(asctime)s.%(msecs)03d (%(name)s) %(levelname)s - %(message)s"
    )

    logging.info("Collecting data before fifa payment.")
    main(addr_before="localhost:8091", addr_after="localhost:8093", fifa_block=3902818)
