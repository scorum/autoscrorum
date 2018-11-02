import pytest

from automation.wallet import Wallet
from tests.common import DEFAULT_WITNESS, validate_response


@pytest.mark.parametrize('delay', [60])
def test_devcommittee_change_resolve_delay(wallet: Wallet, delay):
    default_delay = wallet.get_config()['SCORUM_BETTING_RESOLVE_DELAY_SEC']
    assert default_delay != delay, "Default resolve_delay value has changed. Test case should be updated."
    validate_response(wallet.development_committee_change_betting_resolve_delay(
        DEFAULT_WITNESS, delay
    ), wallet.development_committee_change_betting_resolve_delay.__name__)
    proposals = wallet.list_proposals()
    assert len(proposals) == 1
    validate_response(wallet.proposal_vote(DEFAULT_WITNESS, proposals[0]["id"]), wallet.proposal_vote.__name__)
    props = wallet.get_betting_properties()
    assert props['resolve_delay_sec'] == delay and props["resolve_delay_sec"] != default_delay
