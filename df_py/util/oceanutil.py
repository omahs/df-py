import hashlib
import json
import os
from collections import namedtuple
from typing import Any, Dict, List, Tuple

from enforce_typing import enforce_types
from web3.exceptions import ExtraDataLengthError
from web3.logs import DISCARD
from web3.main import Web3

from df_py.util import networkutil
from df_py.util.base18 import to_wei
from df_py.util.constants import CONTRACTS, ZERO_ADDRESS
from df_py.util.contract_base import ContractBase
from df_py.util.http_provider import get_web3_connection_provider


@enforce_types
def _contracts(key: str):
    """Returns the contract object at the currently connected network"""
    # TODO: actual chainId
    # chainID = brownie.network.chain.id
    chainID = 8996
    if chainID not in CONTRACTS:
        address_file = networkutil.chain_id_to_address_file(chainID)
        record_deployed_contracts(address_file)

    return CONTRACTS[chainID][key]


@enforce_types
def record_dev_deployed_contracts():
    # TODO: uncomment and adapt
    # assert brownie.network.is_connected()
    # assert brownie.network.chain.id == networkutil.DEV_CHAINID
    address_file = networkutil.chain_id_to_address_file(networkutil.DEV_CHAINID)
    record_deployed_contracts(address_file)


@enforce_types
def record_deployed_contracts(address_file: str):
    """Records deployed Ocean contracts at currently connected network"""
    # TODO: uncomment and adapt
    # assert brownie.network.is_connected()
    # TODO: actual chainId
    # chainID = brownie.network.chain.id
    chainID = 8996

    if chainID in CONTRACTS:  # already filled
        return

    network_name = networkutil.chain_id_to_network(chainID)
    with open(address_file, "r") as json_file:
        json_dict = json.load(json_file)
        if network_name not in json_dict:
            raise ValueError(
                f"Can't find {network_name} in {address_file}. Barge problems?"
            )
        a = json_dict[network_name]  # dict of contract_name: address

    C = {}

    web3 = get_web3(get_rpc_url(network_name))

    C["Ocean"] = ContractBase(web3, "Simpletoken", a["Ocean"])
    C["ERC721Template"] = ContractBase(web3, "ERC721Template", a["ERC721Template"]["1"])
    C["ERC20Template"] = ContractBase(web3, "ERC20Template", a["ERC20Template"]["1"])
    C["Router"] = ContractBase(web3, "FactoryRouter", a["Router"])
    C["Staking"] = ContractBase(web3, "SideStaking", a["Staking"])
    C["ERC721Factory"] = ContractBase(web3, "ERC721Factory", a["ERC721Factory"])
    C["FixedPrice"] = ContractBase(web3, "FixedRateExchange", a["FixedPrice"])

    if "veOCEAN" in a:
        C["veOCEAN"] = ContractBase(web3, "veOcean", a["veOCEAN"])

    if "veAllocate" in a:
        C["veAllocate"] = ContractBase(web3, "veAllocate", a["veAllocate"])

    if "veFeeDistributor" in a:
        C["veFeeDistributor"] = ContractBase(
            web3, "FeeDistributor", a["veFeeDistributor"]
        )

    if "veDelegation" in a:
        C["veDelegation"] = ContractBase(web3, "veDelegation", a["veDelegation"])

    if "VestingWalletV0" in a:
        C["VestingWalletV0"] = ContractBase(
            web3, "VestingWalletV0", a["VestingWalletV0"]
        )
    elif chainID == networkutil.DEV_CHAINID:
        web3.eth.default_account = web3.eth.accounts[0]
        C["VestingWalletV0"] = ContractBase(
            web3, "test/VestingWallet", constructor_args=[]
        )
        pass

    CONTRACTS[chainID] = C


def OCEAN_token():
    return _contracts("Ocean")


def OCEAN_address() -> str:
    return OCEAN_token().address.lower()


def ERC721Template():
    return _contracts("ERC721Template")


def ERC20Template():
    return _contracts("ERC20Template")


def FactoryRouter():
    return _contracts("Router")


def Staking():
    return _contracts("Staking")


def ERC721Factory():
    return _contracts("ERC721Factory")


def veOCEAN():
    return _contracts("veOCEAN")


def veAllocate():
    return _contracts("veAllocate")


def veDelegation():
    return _contracts("veDelegation")


def FixedPrice():
    return _contracts("FixedPrice")


def FeeDistributor():
    return _contracts("veFeeDistributor")


def VestingWalletV0():
    return _contracts("VestingWalletV0")


# ===========================================================================
# Creating Ocean objects: data NFT, datatoken, FRE contract


@enforce_types
def create_data_nft_with_fre(web3, from_account, token):
    data_NFT = create_data_nft(web3, "1", "1", from_account)
    DT = create_datatoken_from_data_nft(web3, "1", "1", data_NFT, from_account)

    exchangeId = create_FRE_from_datatoken(DT, token, 10.0, from_account)
    return (data_NFT, DT, exchangeId)


@enforce_types
def create_data_nft(web3: Web3, name: str, symbol: str, from_account):
    erc721_factory = ERC721Factory()
    template_index = 1
    additional_metadata_updater = ZERO_ADDRESS
    additional_erc20_deployer = FactoryRouter().address
    transferable = True
    owner = from_account.address
    token_uri = "https://mystorage.com/mytoken.png"

    tx = erc721_factory.deployERC721Contract(
        name,
        symbol,
        template_index,
        additional_metadata_updater,
        additional_erc20_deployer,
        token_uri,
        transferable,
        owner,
        {"from": from_account},
    )

    event = erc721_factory.contract.events.NFTCreated().process_receipt(
        tx, errors=DISCARD
    )[0]
    data_NFT_address = event.args.newTokenAddress
    data_NFT = ContractBase(web3, "ERC721Template", data_NFT_address)
    return data_NFT


def get_data_nft(web3: Web3, data_nft_address):
    return ContractBase(web3, "ERC721Template", data_nft_address)


def get_data_field(data_nft, field_label: str) -> str:
    field_label_hash = Web3.keccak(text=field_label)  # to keccak256 hash
    field_value_hex = data_nft.getData(field_label_hash)
    field_value = field_value_hex.decode("ascii")

    return field_value


@enforce_types
def create_datatoken_from_data_nft(
    web3: Web3, dt_name: str, dt_symbol: str, data_nft, from_account
):
    erc20_template_index = 1
    strings = [
        dt_name,
        dt_symbol,
    ]
    addresses = [
        from_account.address,  # minter
        from_account.address,  # fee mgr
        from_account.address,  # pub mkt
        ZERO_ADDRESS,  # pub mkt fee token addr
    ]
    uints = [
        to_wei(100000.0),  # cap. Note contract will hardcod this to max_int
        to_wei(0.0),  # pub mkt fee amt
    ]
    _bytes: List[Any] = []

    tx = data_nft.createERC20(
        erc20_template_index, strings, addresses, uints, _bytes, {"from": from_account}
    )

    event = data_nft.contract.events.TokenCreated().process_receipt(tx, errors=DISCARD)[
        0
    ]
    DT_address = event.args.newTokenAddress
    DT = ContractBase(web3, "ERC20Template", DT_address)

    return DT


@enforce_types
def create_FRE_from_datatoken(
    datatoken, base_token, amount: float, from_account, rate=1.0
) -> str:
    """Create new fixed-rate exchange. Returns its exchange_id (str)"""
    datatoken.approve(FixedPrice().address, to_wei(amount), {"from": from_account})

    addresses = [
        base_token.address,  # baseToken
        from_account.address,  # owner
        from_account.address,  # marketFeeCollector address
        ZERO_ADDRESS,  # allowed swapper
    ]

    uints = [
        base_token.decimals(),  # baseTokenDecimals
        datatoken.decimals(),  # datatokenDecimals
        to_wei(rate),  # fixedRate : exchange rate of base_TOKEN to datatoken
        0,  # marketFee
        1,  # withMint
    ]

    # In https://github.com/oceanprotocol/contracts:
    # templates/ERC20Template.sol::createFixedRate()
    # -> pools/FactoryRouter.sol::deployFixedRate()
    # -> pools/fixedRate/FixedRateExchange.sol::createWithDecimals(
    #      datatoken: address, addresses: list, uints: list)
    # Creates an Exchange struct (defined at FixedRateExchange.sol)
    tx = datatoken.createFixedRate(
        FixedPrice().address, addresses, uints, {"from": from_account}
    )

    event = datatoken.contract.events.NewFixedRate().process_receipt(
        tx, errors=DISCARD
    )[0]
    exchange_id: str = event.args.exchangeId

    return exchange_id


# =============================================================================
# veOCEAN routines


@enforce_types
def set_allocation(amount: int, nft_addr: str, chain_id: int, from_account):
    veAllocate().setAllocation(amount, nft_addr, chain_id, {"from": from_account})


@enforce_types
def ve_delegate(
    from_account, to_account, percentage: float, token_id: int, expiry: int = 0
):
    if expiry == 0:
        expiry = veOCEAN().locked__end(from_account)
    veDelegation().create_boost(
        from_account,
        to_account,
        int(percentage * 10000),
        0,
        expiry,
        token_id,
        {"from": from_account},
    )


# =============================================================================
# fee stuff needed for consume


# follow order in ocean.py/ocean_lib/structures/abi_tuples.py::ConsumeFees
@enforce_types
def get_zero_consume_mkt_fee_tuple() -> Tuple:
    d = {
        "consumeMarketFeeAddress": ZERO_ADDRESS,
        "consumeMarketFeeToken": ZERO_ADDRESS,
        "consumeMarketFeeAmount": 0,
    }

    consume_mkt_fee = (
        d["consumeMarketFeeAddress"],
        d["consumeMarketFeeToken"],
        d["consumeMarketFeeAmount"],
    )
    return consume_mkt_fee


# follow order in ocean.py/ocean_lib/structures/abi_tuples.py::ProviderFees
@enforce_types
def get_zero_provider_fee_tuple(pub_account) -> Tuple:
    d = get_zero_provider_fee_dict(pub_account)

    provider_fee = (
        d["providerFeeAddress"],
        d["providerFeeToken"],
        d["providerFeeAmount"],
        d["v"],
        d["r"],
        d["s"],
        d["validUntil"],
        d["providerData"],
    )

    return provider_fee


# from ocean.py/tests/resources/helper_functions.py
@enforce_types
def get_zero_provider_fee_dict(provider_account) -> Dict[str, Any]:
    web3 = brownie.web3
    provider_fee_amount = 0
    compute_env = None
    provider_data = json.dumps({"environment": compute_env}, separators=(",", ":"))
    provider_fee_address = provider_account.address
    provider_fee_token = ZERO_ADDRESS
    valid_until = 0

    message = web3.solidityKeccak(
        ["bytes", "address", "address", "uint256", "uint256"],
        [
            web3.toHex(web3.toBytes(text=provider_data)),
            provider_fee_address,
            provider_fee_token,
            provider_fee_amount,
            valid_until,
        ],
    )
    signed = web3.eth.sign(provider_fee_address, data=message)
    signature = split_signature(signed)

    provider_fee = {
        "providerFeeAddress": provider_fee_address,
        "providerFeeToken": provider_fee_token,
        "providerFeeAmount": provider_fee_amount,
        "providerData": web3.toHex(web3.toBytes(text=provider_data)),
        # make it compatible with last openzepellin
        # https://github.com/OpenZeppelin/openzeppelin-contracts/pull/1622
        "v": signature.v,
        "r": signature.r,
        "s": signature.s,
        "validUntil": 0,
    }

    return provider_fee


# from ocean.py/ocean_lib/web3_internal/utils.py
Signature = namedtuple("Signature", ("v", "r", "s"))


# from ocean.py/ocean_lib/web3_internal/utils.py
@enforce_types
def split_signature(signature: Any) -> Signature:
    """
    :param signature: signed message hash, hex str
    """
    web3 = brownie.web3
    assert len(signature) == 65, (
        f"invalid signature, " f"expecting bytes of length 65, got {len(signature)}"
    )
    v = web3.toInt(signature[-1])
    r = to_32byte_hex(int.from_bytes(signature[:32], "big"))
    s = to_32byte_hex(int.from_bytes(signature[32:64], "big"))
    if v != 27 and v != 28:
        v = 27 + v % 2

    return Signature(v, r, s)


# from ocean.py/ocean_lib/web3_internal/utils.py
@enforce_types
def to_32byte_hex(val: int) -> str:
    """

    :param val:
    :return:
    """
    web3 = brownie.web3
    return web3.toHex(web3.toBytes(val).rjust(32, b"\0"))


@enforce_types
def calc_did(nft_addr: str, chainID: int) -> str:
    nft_addr2 = Web3.to_checksum_address(nft_addr)

    # adapted from ocean.py/ocean_lib/ocean/ocean_assets.py
    did = f"did:op:{create_checksum(nft_addr2 + str(chainID))}"
    return did


# from ocean.py/ocean_lib/utils/utilities.py
@enforce_types
def create_checksum(text: str) -> str:
    """
    :return: str
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@enforce_types
def get_web3(network_url: str) -> Web3:
    provider = get_web3_connection_provider(network_url)
    web3 = Web3(provider)

    try:
        web3.eth.get_block("latest")
    except ExtraDataLengthError:
        from web3.middleware import geth_poa_middleware

        web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    web3.strict_bytes_type_checking = False
    return web3


def get_rpc_url(network_name: str) -> str:
    """Return the RPC URL for a given network."""
    base_url = None

    if os.getenv(f"{network_name.upper()}_RPC_URL"):
        base_url = os.getenv(f"{network_name.upper()}_RPC_URL")

    if os.getenv("WEB3_INFURA_PROJECT_ID") and base_url:
        base_url = f"{base_url}{os.getenv('WEB3_INFURA_PROJECT_ID')}"

    if base_url:
        return base_url

    raise ValueError(f"Need to set {network_name.upper()}_RPC_URL env variable.")
