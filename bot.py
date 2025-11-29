#!/usr/bin/env python3
import asyncio
import aiohttp
import time
from typing import List
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MIN_SPREAD_PCT = 2.5
POLL_INTERVAL = 10

@dataclass
class MarketPrice:
    platform: str
    event_id: str
    event_name: str
    outcome: str
    bid: float
    ask: float
    timestamp: float
    
    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2 if self.bid and self.ask else 0.5

class PolymarketCollector:
    def __init__(self):
        self.api_url = "https://clob.polymarket.com"
    
    async def fetch_markets(self) -> List[MarketPrice]:
        prices = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/markets", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        markets = data.get("markets", [])[:50]
                        for market in markets:
                            market_id = market.get("condition_id", "")
                            title = market.get("question", "")
                            if not market_id or not title: continue
                            try:
                                async with session.get(f"{self.api_url}/orderbooks/{market_id}", timeout=aiohttp.ClientTimeout(total=5)) as ob_resp:
                                    if ob_resp.status == 200:
                                        ob = await ob_resp.json()
                                        bids = ob.get("bids", [])
                                        asks = ob.get("asks", [])
                                        if bids and asks:
                                            prices.append(MarketPrice(
                                                platform="Polymarket",
                                                event_id=market_id,
                                                event_name=title,
                                                outcome="YES",
                                                bid=float(bids[0][0]),
                                                ask=float(asks[0][0]),
                                                timestamp=time.time()
                                            ))
                            except: pass
        except Exception as e:
            logger.error(f"Polymarket error: {e}")
        logger.info(f"Polymarket: {len(prices)} prices")
        return prices

class OPINIONCollector:
    def __init__(self):
        self.base_url = "https://app.opinion.trade"
        self.driver = None
    
    def _init_driver(self):
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            logger.info("Chrome driver initialized")
            return True
        except Exception as e:
            logger.error(f"Chrome error: {e}")
            return False
    
    def _fetch_selenium(self) -> List[MarketPrice]:
        prices = []
        if not self.driver and not self._init_driver():
            return prices
        try:
            logger.info("Loading OPINION...")
            self.driver.get(f"{self.base_url}/macro")
            WebDriverWait(self.driver, 15).until(EC.presence_of_all_elements_located((By.TAG_NAME, "tr")))
            rows = self.driver.find_elements(By.TAG_NAME, "tr")
            logger.info(f"Found {len(rows)} rows")
            for row in rows[1:51]:
                try:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) < 5: continue
                    event_name = cols[2].text.strip()
                    if not event_name: continue
                    price_elements = row.find_elements(By.XPATH, ".//*[contains(text(), '%')]")
                    if len(price_elements) >= 1:
                        try:
                            price_text = price_elements[0].text.strip()
                            price_value = float(price_text.replace('%', '').replace(',', '.'))
                            if 0 < price_value < 100:
                                mid_price = price_value / 100.0
                                prices.append(MarketPrice(
                                    platform="OPINION",
                                    event_id=event_name,
                                    event_name=event_name,
                                    outcome="YES",
                                    bid=mid_price * 0.99,
                                    ask=mid_price * 1.01,
                                    timestamp=time.time()
                                ))
                        except: pass
                except: continue
            logger.info(f"OPINION: {len(prices)} prices")
        except Exception as e:
            logger.error(f"OPINION error: {e}")
        return prices
    
    async def fetch_markets(self) -> List[MarketPrice]:
        loop = asyncio.get_event_loop()
        prices = await loop.run_in_executor(None, self._fetch_selenium)
        return prices
    
    def close(self):
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Chrome closed")
            except: pass

class ArbitrageEngine:
    def __init__(self, min_spread: float = 2.5):
        self.min_spread = min_spread
        self.fee_pct = 1.0
    
    def normalize_event_name(self, name: str) -> str:
        return " ".join(name.lower().split())[:100]
    
    def process_prices(self, prices: List[MarketPrice]):
        opportunities = []
        grouped = defaultdict(list)
        for price in prices:
            key = f"{self.normalize_event_name(price.event_name)}|{price.outcome}"
            grouped[key].append(price)
        
        for event_key, event_prices in grouped.items():
            if len(event_prices) < 2: continue
            platforms = {p.platform: p for p in event_prices}
            if len(platforms) < 2: continue
            
            platform_list = list(platforms.items())
            for i in range(len(platform_list)):
                for j in range(i + 1, len(platform_list)):
                    p1_name, p1 = platform_list[i]
                    p2_name, p2 = platform_list[j]
                    price1 = p1.mid
                    price2 = p2.mid
                    if price1 > price2:
                        price1, price2 = price2, price1
                        p1_name, p2_name = p2_name, p1_name
                    spread = ((price2 - price1) / price1) * 100
                    net_spread = spread - (2 * self.fee_pct)
                    if net_spread >= self.min_spread:
                        event_name, outcome = event_key.split("|")
                        opportunities.append({
                            'event': event_name,
                            'buy_platform': p1_name,
                            'buy_price': price1,
                            'sell_platform': p2_name,
                            'sell_price': price2,
                            'net_spread': net_spread
                        })
        return opportunities

async def main():
    print("\n" + "="*60)
    print("🚀 ARBITRAGE BOT - Polymarket vs OPINION")
    print("="*60 + "\n")
    
    polymarket = PolymarketCollector()
    opinion = OPINIONCollector()
    engine = ArbitrageEngine(min_spread=MIN_SPREAD_PCT)
    
    iteration = 0
    found_total = 0
    
    try:
        while True:
            try:
                iteration += 1
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"\n[Scan #{iteration}] {timestamp}")
                
                all_prices = []
                pm_prices = await polymarket.fetch_markets()
                all_prices.extend(pm_prices)
                op_prices = await opinion.fetch_markets()
                all_prices.extend(op_prices)
                
                print(f"Total prices: {len(all_prices)} (PM: {len(pm_prices)}, OPINION: {len(op_prices)})")
                
                opportunities = engine.process_prices(all_prices)
                
                if opportunities:
                    found_total += len(opportunities)
                    print(f"\n✅ FOUND {len(opportunities)} OPPORTUNITIES!\n")
                    for idx, opp in enumerate(opportunities, 1):
                        print(f"  {idx}. {opp['event']}")
                        print(f"     BUY  {opp['buy_platform']:12} @ {opp['buy_price']:.6f}")
                        print(f"     SELL {opp['sell_platform']:12} @ {opp['sell_price']:.6f}")
                        print(f"     SPREAD: {opp['net_spread']:.3f}%\n")
                else:
                    print("No opportunities found")
                
                print(f"Total found: {found_total}")
                await asyncio.sleep(POLL_INTERVAL)
            except Exception as e:
                logger.error(f"Error: {e}")
                await asyncio.sleep(10)
    finally:
        opinion.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped")
        exit(0)
