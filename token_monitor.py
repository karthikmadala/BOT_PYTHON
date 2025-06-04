import requests
import time
import asyncio
import logging
import certifi
import ssl
import json
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError, RetryAfter
from web3 import Web3
from web3.exceptions import Web3Exception
import os
from typing import Dict, List, Optional, Tuple
import aiohttp
from dataclasses import dataclass
from functools import lru_cache

# Configuration class
@dataclass
class Config:
    BSCSCAN_API_KEY: str = "6IYJ7I59ZUJQDYE8S44UT8MXB48DFP69VK"
    TELEGRAM_BOT_TOKEN: str = "8131473302:AAFxLJ4RPa52SOU2zVMxkPHKjQ0V8mqpTFc"
    TELEGRAM_CHANNEL_ID: str = "-1002609179898"
    ICO_ADDRESS: str = "0x4408cd3a88C813E34C23bdd1FB57d75df9227003"
    TOKEN_ADDRESS: str = "0xf9847c631ADED64430Ece222798994b88bC8aeDA"
    IMAGE_PATH: str = "./stoneform_telegram_img.png"
    FALLBACK_IMAGE_URL: str = "https://stoneform.io/assets/images/icon/logo.png"
    STONEFORM_WEBSITE: str = "https://stoneform.io/"
    STONEFORM_WHITEPAPER: str = "https://stoneform.io/public/pdf/WHITEPAPER.pdf"
    CACHE_FILE: str = "token_monitor_cache.json"
    LOG_FILE: str = "token_monitor.log"
    BSC_NODE_URL: str = "https://bsc-dataseed.binance.org/"
    POLLING_INTERVAL: int = 30
    REQUEST_TIMEOUT: int = 10
    MAX_RETRIES: int = 3
    FALLBACK_PRICE: float = 0.02
    FALLBACK_SUPPLY: float = 100000000000
    FALLBACK_NAME: str = "Stoneform"
    FALLBACK_SYMBOL: str = "STOF"
    FALLBACK_DECIMALS: int = 18

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Web3 and Telegram bot
w3 = Web3(Web3.HTTPProvider(Config.BSC_NODE_URL))
bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)

# ABIs
TOKEN_ABI = [
    {
        "inputs":[{"internalType":"address","name":"initialOwner","type":"address"}],"stateMutability":"nonpayable","type":"constructor"},
        {"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"allowance","type":"uint256"},{"internalType":"uint256","name":"needed","type":"uint256"}],"name":"ERC20InsufficientAllowance","type":"error"},
        {"inputs":[{"internalType":"address","name":"sender","type":"address"},{"internalType":"uint256","name":"balance","type":"uint256"},{"internalType":"uint256","name":"needed","type":"uint256"}],"name":"ERC20InsufficientBalance","type":"error"},
        {"inputs":[{"internalType":"address","name":"approver","type":"address"}],"name":"ERC20InvalidApprover","type":"error"},
        {"inputs":[{"internalType":"address","name":"receiver","type":"address"}],"name":"ERC20InvalidReceiver","type":"error"},
        {"inputs":[{"internalType":"address","name":"sender","type":"address"}],"name":"ERC20InvalidSender","type":"error"},
        {"inputs":[{"internalType":"address","name":"spender","type":"address"}],"name":"ERC20InvalidSpender","type":"error"},
        {"inputs":[{"internalType":"address","name":"owner","type":"address"}],"name":"OwnableInvalidOwner","type":"error"},
        {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"OwnableUnauthorizedAccount","type":"error"},
        {"inputs":[],"name":"INITIAL_SUPPLY","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
        {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"burn","outputs":[],"stateMutability":"nonpayable","type":"function"},
        {"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"mint","outputs":[],"stateMutability":"nonpayable","type":"function"},
        {"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},
        {"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
        {"inputs":[],"name":"renounceOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},
        {"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},
        {"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
        {"inputs":[{"internalType":"address","name":"from","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
        {"inputs":[{"internalType":"address","name":"newOwner","type":"address"}],"name":"transferOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"}
]

ICO_ABI = [
    {
        "inputs":[],"name":"tokenAmountPerUSD","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"
    },
    {
        "inputs":[],"name":"tokenAddress","outputs":[{"internalType":"contract IERC20","name":"","type":"address"}],"stateMutability":"view","type":"function"
    },
    {
        "inputs":[
            {"internalType":"address","name":"recipient","type":"address"},
            {"internalType":"uint256","name":"paymentType","type":"uint256"},
            {"internalType":"uint256","name":"tokenAmount","type":"uint256"},
            {
                "components":[
                    {"internalType":"uint8","name":"v","type":"uint8"},
                    {"internalType":"bytes32","name":"r","type":"bytes32"},
                    {"internalType":"bytes32","name":"s","type":"bytes32"},
                    {"internalType":"uint256","name":"nonce","type":"uint256"}
                ],
                "internalType":"struct StoneForm_ICO.Sign","name":"sign","type":"tuple"
            }
        ],
        "name":"buyToken","outputs":[],"stateMutability":"payable","type":"function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "amount", "type": "uint256"}
        ],
        "name": "TokenBuyed",
        "type": "event"
    }
]

class Cache:
    def __init__(self):
        self.cache_file = Config.CACHE_FILE
        self.known_addresses = set()
        self.processed_tx_hashes = set()
        self.load_cache()

    def load_cache(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    self.known_addresses = set(data.get('known_addresses', []))
                    self.processed_tx_hashes = set(data.get('processed_tx_hashes', []))
                logger.info(f"Cache loaded: {len(self.known_addresses)} addresses, {len(self.processed_tx_hashes)} processed txs")
        except Exception as e:
            logger.error(f"Error loading cache: {e}")

    def save_cache(self):
        try:
            with open(self.cache_file, 'w') as f:
                json.dump({
                    'known_addresses': list(self.known_addresses),
                    'processed_tx_hashes': list(self.processed_tx_hashes)
                }, f)
            logger.info("Cache saved successfully")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")

@lru_cache(maxsize=1)
def get_token_info() -> Tuple[str, str, float, int]:
    try:
        contract = w3.eth.contract(address=Config.TOKEN_ADDRESS, abi=TOKEN_ABI)
        symbol = contract.functions.symbol().call()
        name = contract.functions.name().call()
        initial_supply = contract.functions.INITIAL_SUPPLY().call()
        decimals = contract.functions.decimals().call()
        initial_supply = initial_supply / 10**decimals
        logger.info(f"Token Info - Name: {name}, Symbol: {symbol}, Initial Supply: {initial_supply:,.0f}, Decimals: {decimals}")
        return name, symbol, initial_supply, decimals
    except Web3Exception as e:
        logger.error(f"Error fetching token info for {Config.TOKEN_ADDRESS}: {e}", exc_info=True)
        return Config.FALLBACK_NAME, Config.FALLBACK_SYMBOL, Config.FALLBACK_SUPPLY, Config.FALLBACK_DECIMALS

async def fetch_with_retry(url: str, session: aiohttp.ClientSession, retries: int = Config.MAX_RETRIES) -> Optional[Dict]:
    for attempt in range(retries):
        try:
            async with session.get(url, timeout=Config.REQUEST_TIMEOUT) as response:
                response.raise_for_status()
                data = await response.json()
                logger.debug(f"Fetched data from {url}: {data.get('status')}")
                return data
        except aiohttp.ClientError as e:
            logger.error(f"Request failed (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
    return None

async def get_token_transactions(session: aiohttp.ClientSession) -> List[Dict]:
    url = f"https://api.bscscan.com/api?module=account&action=txlist&address={Config.ICO_ADDRESS}&sort=desc&apikey={Config.BSCSCAN_API_KEY}"
    data = await fetch_with_retry(url, session)
    transactions = []
    if data and data.get("status") == "1" and data.get("result"):
        logger.info(f"Found {len(data['result'])} transactions for ICO_ADDRESS {Config.ICO_ADDRESS}")
        transactions = data["result"]
    else:
        logger.warning(f"No transactions found: {data.get('message', 'Unknown error') if data else 'Request failed'}")
    return transactions

async def get_token_buyed_events(tx_hash: str, decimals: int) -> Tuple[Optional[float], Optional[str]]:
    try:
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        contract = w3.eth.contract(address=Config.ICO_ADDRESS, abi=ICO_ABI)
        logs = contract.events.TokenBuyed().process_receipt(receipt)
        for log in logs:
            if log['address'].lower() == Config.ICO_ADDRESS.lower():
                amount = log['args']['amount'] / 10**decimals
                to_address = log['args']['to']
                logger.info(f"Found TokenBuyed event in tx {tx_hash}: {amount:,.2f} tokens to {to_address}")
                return amount, to_address
        logger.debug(f"No TokenBuyed event found in tx {tx_hash}")
        return None, None
    except Web3Exception as e:
        logger.error(f"Error fetching TokenBuyed event for tx {tx_hash}: {e}")
        return None, None

@lru_cache(maxsize=1)
def tokenpriceperusd() -> float:
    try:
        contract = w3.eth.contract(address=Config.ICO_ADDRESS, abi=ICO_ABI)
        token_amount_per_usd = contract.functions.tokenAmountPerUSD().call()
        contract_token_address = contract.functions.tokenAddress().call()
        if contract_token_address.lower() != Config.TOKEN_ADDRESS.lower():
            logger.warning(f"ICO contract token address mismatch: {contract_token_address} vs {Config.TOKEN_ADDRESS}")
            return Config.FALLBACK_PRICE
        token_contract = w3.eth.contract(address=Config.TOKEN_ADDRESS, abi=TOKEN_ABI)
        decimals = token_contract.functions.decimals().call()
        if token_amount_per_usd == 0:
            logger.warning("tokenAmountPerUSD is 0")
            return Config.FALLBACK_PRICE
        price_usd = 1 / (token_amount_per_usd / 10**decimals)
        logger.info(f"Token Price: {price_usd:.6f} USD")
        return price_usd
    except Web3Exception as e:
        logger.error(f"Error fetching price for {Config.ICO_ADDRESS}: {e}", exc_info=True)
        return Config.FALLBACK_PRICE

def is_new_holder(to_address: str, cache: Cache) -> bool:
    if not to_address:
        logger.warning("Empty to_address, assuming new holder")
        return True
    logger.debug(f"Checking if {to_address} is a new holder. Known addresses: {len(cache.known_addresses)}")
    if to_address.lower() in [addr.lower() for addr in cache.known_addresses]:
        logger.info(f"Address {to_address} already in cache, marking as existing holder")
        return False
    cache.known_addresses.add(to_address)
    cache.save_cache()
    logger.info(f"Added new holder {to_address} to cache")
    return True

async def send_to_telegram(
    transaction: Dict,
    amount: float,
    to_address: str,
    initial_supply: float,
    price: float,
    name: str,
    symbol: str,
    decimals: int,
    volume_24h: float,
    cache: Cache
):
    amount_usd = amount * price
    holders_count = len(cache.known_addresses)
    new_holder = is_new_holder(to_address, cache)
    
    message = (
        f"<b>🚀 {name} ({symbol}) Token Purchase 🚀</b>\n\n"
        f"<b>New Token Buy Alert 📢</b>\n"
        f"📍 Amount: {amount:,.2f} {symbol}\n"
        f"💰 USD Value: ${amount_usd:,.2f}\n"
        f"📈 Price: ${price:.6f}\n"
        f"💸 Initial Supply: {initial_supply:,.0f} {symbol}\n"
        f"👥 Holders: {holders_count:,}\n"
        f"ℹ️ Status: {'New Holder!' if new_holder else 'Existing Holder'}\n"
        f"⏰ Time: {datetime.fromtimestamp(int(transaction.get('timeStamp', 0))).strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
        f"<a href='https://bscscan.com/tx/{transaction['hash']}'>View on BscScan</a>\n\n"
        f"<a href='{Config.STONEFORM_WEBSITE}'>Website</a> | "
        f"<a href='{Config.STONEFORM_WHITEPAPER}'>Whitepaper</a>"
    )

    logger.info(f"Sending Telegram message for tx {transaction['hash']} (length: {len(message)}):\n{message}")

    async with aiohttp.ClientSession() as session:
        for attempt in range(Config.MAX_RETRIES):
            try:
                if os.path.exists(Config.IMAGE_PATH):
                    with open(Config.IMAGE_PATH, "rb") as photo:
                        await bot.send_photo(
                            chat_id=Config.TELEGRAM_CHANNEL_ID,
                            photo=photo,
                            caption=message,
                            parse_mode="HTML"
                        )
                    logger.info("Message sent with local image")
                else:
                    await bot.send_photo(
                        chat_id=Config.TELEGRAM_CHANNEL_ID,
                        photo=Config.FALLBACK_IMAGE_URL,
                        caption=message,
                        parse_mode="HTML"
                    )
                    logger.info("Message sent with fallback image")
                return
            except RetryAfter as e:
                logger.warning(f"Rate limit hit, retrying after {e.retry_after} seconds")
                await asyncio.sleep(e.retry_after)
            except TelegramError as e:
                logger.error(f"Telegram error (attempt {attempt + 1}/{Config.MAX_RETRIES}): {e}")
                if attempt < Config.MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"Unexpected error sending to Telegram: {e}")
                break

        try:
            await bot.send_message(
                chat_id=Config.TELEGRAM_CHANNEL_ID,
                text=message,
                parse_mode="HTML"
            )
            logger.info("Text-only message sent")
        except TelegramError as e:
            logger.error(f"Failed to send text-only message: {e}")

async def calculate_24h_volume(transactions: List[Dict], decimals: int = Config.FALLBACK_DECIMALS) -> float:
    now = int(time.time())
    one_day_ago = now - 24 * 3600
    volume = 0.0
    for tx in transactions:
        if int(tx.get("timeStamp", 0)) >= one_day_ago:
            amount, _ = await get_token_buyed_events(tx["hash"], decimals)
            if amount is not None:
                volume += amount
    logger.info(f"Calculated 24h volume: {volume:,.2f}")
    return volume

async def main():
    logger.info("Starting token monitoring service...")
    
    if not w3.is_connected():
        logger.error("Failed to connect to BSC node")
        exit(1)

    cache = Cache()
    logger.info(f"Cache initialized: {len(cache.processed_tx_hashes)} processed txs, {len(cache.known_addresses)} known addresses")
    name, symbol, initial_supply, decimals = get_token_info()
    logger.info(f"Token info fetched: name={name}, symbol={symbol}, initial_supply={initial_supply}, decimals={decimals}")
    volume_24h = 0

    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=ssl.create_default_context(cafile=certifi.where()))
    ) as session:
        while True:
            try:
                logger.debug("Starting main loop iteration")
                transactions = await get_token_transactions(session)
                price = tokenpriceperusd()
                logger.info(f"Price fetched: {price}")
                volume_24h = await calculate_24h_volume(transactions, decimals)

                if transactions:
                    logger.info(f"Processing {len(transactions)} transactions")
                    for tx in transactions[:5]:
                        if tx["hash"] in cache.processed_tx_hashes:
                            logger.debug(f"Skipping already processed tx: {tx['hash']}")
                            continue
                        amount, to_address = await get_token_buyed_events(tx["hash"], decimals)
                        if amount is not None and to_address is not None:
                            logger.info(f"New TokenBuyed event detected: {tx['hash']}")
                            await send_to_telegram(
                                tx, amount, to_address, initial_supply, price,
                                name, symbol, decimals, volume_24h, cache
                            )
                            cache.processed_tx_hashes.add(tx["hash"])
                            cache.save_cache()
                        else:
                            logger.debug(f"No valid TokenBuyed event in tx: {tx['hash']}")
                else:
                    logger.info("No transactions found in this iteration")

                await asyncio.sleep(Config.POLLING_INTERVAL)

            except Exception as e:
                logger.error(f"Main loop error: {e}", exc_info=True)
                await asyncio.sleep(Config.POLLING_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
