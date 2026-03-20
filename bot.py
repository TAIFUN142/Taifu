import os
import sqlite3
import random
import time
import traceback
import requests
import pandas as pd
import yfinance as yf
import telebot

from datetime import datetime
from telebot import types

print("=" * 60)
print("🤖 БОТ С СИГНАЛАМИ BINARY OPTIONS + РЕФЕРАЛЬНАЯ СИСТЕМА")
print("=" * 60)

# ========== НАСТРОЙКИ ==========
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

POCKET_REFERRAL_LINK = "https://pocket-friends.co/r/cvez0moyv8"
ADMIN_ID = 8385943123
# ===============================

bot = telebot.TeleBot(TOKEN)

# ========== НАСТРОЙКИ АКТИВОВ ==========
CRYPTO_ASSETS = [
    "BTC/USD", "ETH/USD", "BNB/USD", "SOL/USD", "XRP/USD",
    "ADA/USD", "DOGE/USD", "DOT/USD", "MATIC/USD", "SHIB/USD",
    "AVAX/USD", "LINK/USD", "LTC/USD", "TRX/USD", "UNI/USD",
    "ATOM/USD", "ETC/USD", "XLM/USD", "FIL/USD", "ALGO/USD",
    "VET/USD", "MANA/USD", "SAND/USD", "THETA/USD", "XTZ/USD",
    "EOS/USD", "AAVE/USD", "CAKE/USD", "KLAY/USD", "NEAR/USD",
    "QNT/USD", "CHZ/USD", "FLOW/USD", "GALA/USD", "AXS/USD",
    "APE/USD", "GRT/USD", "CRV/USD", "SNX/USD", "COMP/USD"
]

FOREX_ASSETS = [
    "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD",
    "USD/CAD", "NZD/USD", "EUR/GBP", "GBP/JPY",
    "USD/CHF", "EUR/JPY", "EUR/CHF", "GBP/CHF",
    "AUD/JPY", "CAD/JPY", "NZD/JPY", "EUR/AUD",
    "EUR/CAD", "GBP/AUD", "GBP/CAD", "AUD/CAD",
    "AUD/NZD", "USD/SGD", "USD/HKD", "USD/CNH",
    "USD/MXN", "USD/ZAR", "USD/TRY", "USD/INR"
]

COMMODITIES_ASSETS = [
    "XAU/USD", "XAG/USD", "XPT/USD", "XPD/USD",
    "OIL/USD", "NATURAL GAS", "COPPER", "ALUMINUM",
    "WHEAT", "CORN", "SOYBEAN", "SUGAR",
    "COFFEE", "COCOA", "COTTON", "LUMBER"
]

INDICES_ASSETS = [
    "S&P 500", "NASDAQ", "DOW JONES", "DAX 30",
    "FTSE 100", "NIKKEI 225", "CAC 40", "HSI",
    "ASX 200", "IBEX 35", "SMI", "TSX",
    "STOXX 50", "RUSSELL 2000", "SHANGHAI COMP"
]

OTC_ASSETS = [
    "BTC/OTC", "ETH/OTC", "BNB/OTC", "SOL/OTC", "XRP/OTC",
    "ADA/OTC", "DOGE/OTC", "DOT/OTC", "MATIC/OTC", "SHIB/OTC",
    "AVAX/OTC", "LINK/OTC", "LTC/OTC", "TRX/OTC", "UNI/OTC",
    "ATOM/OTC", "XLM/OTC", "FIL/OTC", "ALGO/OTC", "VET/OTC",
    "EOS/OTC", "AAVE/OTC", "XTZ/OTC", "MANA/OTC", "SAND/OTC",
    "GALA/OTC", "APE/OTC", "AXS/OTC", "THETA/OTC", "NEAR/OTC",
    "QNT/OTC", "CHZ/OTC", "FLOW/OTC", "GRT/OTC", "CRV/OTC",
    "SNX/OTC", "COMP/OTC", "CAKE/OTC", "KLAY/OTC", "ETC/OTC"
]

ALL_ASSETS = CRYPTO_ASSETS + FOREX_ASSETS + COMMODITIES_ASSETS + INDICES_ASSETS + OTC_ASSETS
TIMEFRAMES = ["1 мин", "5 мин", "15 мин", "30 мин", "1 час", "4 часа", "1 день"]


# ========== БАЗА ДАННЫХ ==========
def get_db_connection():
    conn = sqlite3.connect("pocket_bot.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            username TEXT,
            first_name TEXT,
            join_date TEXT,
            pocket_id TEXT,
            is_verified INTEGER DEFAULT 0,
            referrer_id INTEGER DEFAULT 0,
            balance REAL DEFAULT 0,
            signals_count INTEGER DEFAULT 0,
            last_signal_date TEXT,
            preferred_assets TEXT DEFAULT '',
            trading_experience TEXT DEFAULT '',
            risk_level TEXT DEFAULT 'medium',
            preferred_timeframe TEXT DEFAULT ''
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER,
            registration_date TEXT,
            FOREIGN KEY (referrer_id) REFERENCES users(telegram_id),
            FOREIGN KEY (referred_id) REFERENCES users(telegram_id)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            signal_date TEXT,
            asset TEXT,
            direction TEXT,
            timeframe TEXT,
            confidence INTEGER,
            result TEXT DEFAULT 'PENDING',
            FOREIGN KEY (user_id) REFERENCES users(telegram_id)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS verification_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            pocket_id TEXT,
            request_date TEXT,
            status TEXT DEFAULT 'PENDING',
            verification_date TEXT,
            admin_id INTEGER
        )
        """)

        conn.commit()
        print("✅ База данных инициализирована")
        update_database_structure(conn)

    except Exception as e:
        print(f"⚠️ Ошибка при инициализации БД: {e}")
    finally:
        cursor.close()
        conn.close()


def update_database_structure(conn):
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users)")
    existing_columns = [column[1] for column in cursor.fetchall()]

    required_columns = [
        ("preferred_assets", "TEXT DEFAULT ''"),
        ("trading_experience", "TEXT DEFAULT ''"),
        ("risk_level", "TEXT DEFAULT 'medium'"),
        ("preferred_timeframe", "TEXT DEFAULT ''")
    ]

    for column_name, column_type in required_columns:
        if column_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
                print(f"✅ Колонка {column_name} добавлена")
            except Exception as e:
                print(f"⚠️ Ошибка при добавлении колонки {column_name}: {e}")

    conn.commit()
    cursor.close()


init_db()


def execute_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if commit:
            conn.commit()

        if fetchone:
            result = cursor.fetchone()
        elif fetchall:
            result = cursor.fetchall()
        else:
            result = None

        return result
    except Exception as e:
        print(f"Ошибка выполнения запроса: {e}")
        print(f"Запрос: {query}")
        print(f"Параметры: {params}")
        return None
    finally:
        cursor.close()
        conn.close()


def get_user(telegram_id):
    return execute_query(
        "SELECT * FROM users WHERE telegram_id = ?",
        (telegram_id,),
        fetchone=True
    )


def add_user(telegram_id, username, first_name, join_date):
    return execute_query(
        """INSERT OR IGNORE INTO users (telegram_id, username, first_name, join_date)
           VALUES (?, ?, ?, ?)""",
        (telegram_id, username, first_name, join_date),
        commit=True
    )


def ensure_owner_access():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET is_verified = 1 WHERE telegram_id = ?", (ADMIN_ID,))
        cursor.execute("DELETE FROM verification_requests WHERE user_id = ?", (ADMIN_ID,))
        conn.commit()
        print("👑 Доступ владельца гарантирован")
    except Exception as e:
        print(f"⚠️ Ошибка при обеспечении доступа владельца: {e}")
    finally:
        cursor.close()
        conn.close()


ensure_owner_access()


# ========== АНАЛИЗАТОР ==========
class MarketAnalyzer:
    def __init__(self):
        self.binance_timeframes = {
            "1 мин": "1m",
            "5 мин": "5m",
            "15 мин": "15m",
            "30 мин": "30m",
            "1 час": "1h",
            "4 часа": "4h",
            "1 день": "1d"
        }

        self.yahoo_timeframes = {
            "1 мин": ("1d", "1m"),
            "5 мин": ("5d", "5m"),
            "15 мин": ("5d", "15m"),
            "30 мин": ("10d", "30m"),
            "1 час": ("1mo", "60m"),
            "4 часа": ("3mo", "1h"),
            "1 день": ("6mo", "1d")
        }

        self.yahoo_map = {
            "EUR/USD": "EURUSD=X",
            "GBP/USD": "GBPUSD=X",
            "USD/JPY": "JPY=X",
            "AUD/USD": "AUDUSD=X",
            "USD/CAD": "CAD=X",
            "NZD/USD": "NZDUSD=X",
            "EUR/GBP": "EURGBP=X",
            "GBP/JPY": "GBPJPY=X",
            "USD/CHF": "CHF=X",
            "EUR/JPY": "EURJPY=X",
            "EUR/CHF": "EURCHF=X",
            "GBP/CHF": "GBPCHF=X",
            "AUD/JPY": "AUDJPY=X",
            "CAD/JPY": "CADJPY=X",
            "NZD/JPY": "NZDJPY=X",
            "EUR/AUD": "EURAUD=X",
            "EUR/CAD": "EURCAD=X",
            "GBP/AUD": "GBPAUD=X",
            "GBP/CAD": "GBPCAD=X",
            "AUD/CAD": "AUDCAD=X",
            "AUD/NZD": "AUDNZD=X",
            "USD/SGD": "SGD=X",
            "USD/HKD": "HKD=X",
            "USD/CNH": "CNH=X",
            "USD/MXN": "MXN=X",
            "USD/ZAR": "ZAR=X",
            "USD/TRY": "TRY=X",
            "USD/INR": "INR=X",

            "XAU/USD": "GC=F",
            "XAG/USD": "SI=F",
            "XPT/USD": "PL=F",
            "XPD/USD": "PA=F",
            "OIL/USD": "CL=F",
            "NATURAL GAS": "NG=F",
            "COPPER": "HG=F",
            "ALUMINUM": "ALI=F",
            "WHEAT": "ZW=F",
            "CORN": "ZC=F",
            "SOYBEAN": "ZS=F",
            "SUGAR": "SB=F",
            "COFFEE": "KC=F",
            "COCOA": "CC=F",
            "COTTON": "CT=F",
            "LUMBER": "LBR=F",

            "S&P 500": "^GSPC",
            "NASDAQ": "^IXIC",
            "DOW JONES": "^DJI",
            "DAX 30": "^GDAXI",
            "FTSE 100": "^FTSE",
            "NIKKEI 225": "^N225",
            "CAC 40": "^FCHI",
            "HSI": "^HSI",
            "ASX 200": "^AXJO",
            "IBEX 35": "^IBEX",
            "SMI": "^SSMI",
            "TSX": "^GSPTSE",
            "STOXX 50": "^STOXX50E",
            "RUSSELL 2000": "^RUT",
            "SHANGHAI COMP": "000001.SS"
        }

        self.supported_crypto = {
            "BTC/USD": "BTCUSDT",
            "ETH/USD": "ETHUSDT",
            "BNB/USD": "BNBUSDT",
            "SOL/USD": "SOLUSDT",
            "XRP/USD": "XRPUSDT",
            "ADA/USD": "ADAUSDT",
            "DOGE/USD": "DOGEUSDT",
            "DOT/USD": "DOTUSDT",
            "MATIC/USD": "POLUSDT",
            "SHIB/USD": "SHIBUSDT",
            "AVAX/USD": "AVAXUSDT",
            "LINK/USD": "LINKUSDT",
            "LTC/USD": "LTCUSDT",
            "TRX/USD": "TRXUSDT",
            "UNI/USD": "UNIUSDT",
            "ATOM/USD": "ATOMUSDT",
            "ETC/USD": "ETCUSDT",
            "XLM/USD": "XLMUSDT",
            "FIL/USD": "FILUSDT",
            "ALGO/USD": "ALGOUSDT",
            "VET/USD": "VETUSDT",
            "MANA/USD": "MANAUSDT",
            "SAND/USD": "SANDUSDT",
            "THETA/USD": "THETAUSDT",
            "XTZ/USD": "XTZUSDT",
            "EOS/USD": "EOSUSDT",
            "AAVE/USD": "AAVEUSDT",
            "CAKE/USD": "CAKEUSDT",
            "KLAY/USD": "KLAYUSDT",
            "NEAR/USD": "NEARUSDT",
            "QNT/USD": "QNTUSDT",
            "CHZ/USD": "CHZUSDT",
            "FLOW/USD": "FLOWUSDT",
            "GALA/USD": "GALAUSDT",
            "AXS/USD": "AXSUSDT",
            "APE/USD": "APEUSDT",
            "GRT/USD": "GRTUSDT",
            "CRV/USD": "CRVUSDT",
            "SNX/USD": "SNXUSDT",
            "COMP/USD": "COMPUSDT"
        }

    def _ema(self, series, period):
        return series.ewm(span=period, adjust=False).mean()

    def _rsi(self, close, period=14):
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / avg_loss.replace(0, 1e-10)
        return 100 - (100 / (1 + rs))

    def _macd(self, close):
        ema12 = self._ema(close, 12)
        ema26 = self._ema(close, 26)
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        hist = macd - signal
        return macd, signal, hist

    def _atr(self, df, period=14):
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def _detect_asset_type(self, asset):
        if "/OTC" in asset:
            return "otc"
        if asset in self.supported_crypto:
            return "crypto"
        if asset in FOREX_ASSETS:
            return "forex"
        if asset in COMMODITIES_ASSETS:
            return "commodity"
        if asset in INDICES_ASSETS:
            return "index"
        return "unknown"

    def _fetch_binance_ohlcv(self, symbol, timeframe):
        interval = self.binance_timeframes.get(timeframe, "5m")
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": symbol, "interval": interval, "limit": 250}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        df = pd.DataFrame(data, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "qav", "num_trades", "tbbav", "tbqav", "ignore"
        ])
        df = df[["open", "high", "low", "close", "volume"]].astype(float)
        return df.dropna()

    def _fetch_yahoo_ohlcv(self, ticker, timeframe):
        period, interval = self.yahoo_timeframes.get(timeframe, ("5d", "5m"))

        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            multi_level_index=False
        )

        if df is None or df.empty:
            raise ValueError(f"Нет данных по тикеру {ticker}")

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        df = df.loc[:, ~df.columns.duplicated()].copy()

        if "Adj Close" in df.columns:
            df = df.drop(columns=["Adj Close"])

        rename_map = {
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume"
        }

        df = df.rename(columns=rename_map)
        df = df.loc[:, ~df.columns.duplicated()].copy()

        required = ["open", "high", "low", "close", "volume"]
        missing = [col for col in required if col not in df.columns]

        if missing:
            raise ValueError(f"В данных {ticker} нет колонок: {missing}")

        df = df[required].copy()
        df = df.dropna()

        if df.empty:
            raise ValueError(f"Пустые данные по тикеру {ticker}")

        return df

    def _fetch_ohlcv(self, asset, timeframe):
        asset_type = self._detect_asset_type(asset)

        if asset_type == "otc":
            proxy_asset = asset.replace("/OTC", "/USD")
            proxy_type = self._detect_asset_type(proxy_asset)

            if proxy_type == "crypto":
                symbol = self.supported_crypto.get(proxy_asset)
                if not symbol:
                    raise ValueError(f"Нет proxy-маппинга для OTC актива {asset}")
                return self._fetch_binance_ohlcv(symbol, timeframe), proxy_asset

            ticker = self.yahoo_map.get(proxy_asset)
            if ticker:
                return self._fetch_yahoo_ohlcv(ticker, timeframe), proxy_asset

            raise ValueError(f"Нет proxy-маппинга для OTC актива {asset}")

        if asset_type == "crypto":
            symbol = self.supported_crypto.get(asset)
            if not symbol:
                raise ValueError(f"Нет маппинга для крипто-актива {asset}")
            return self._fetch_binance_ohlcv(symbol, timeframe), asset

        ticker = self.yahoo_map.get(asset)
        if not ticker:
            raise ValueError(f"Нет тикера для актива {asset}")

        return self._fetch_yahoo_ohlcv(ticker, timeframe), asset

    def analyze_market(self, asset=None, timeframe=None):
        if not asset:
            asset = random.choice(ALL_ASSETS)

        if not timeframe:
            timeframe = random.choice(TIMEFRAMES)

        asset_type = self._detect_asset_type(asset)

        try:
            df, source_asset = self._fetch_ohlcv(asset, timeframe)
        except Exception as e:
            return {
                "asset": asset,
                "direction": "WAIT",
                "confidence": 0,
                "timeframe": timeframe,
                "risk": "⚪ НЕТ ДАННЫХ",
                "risk_level": "unknown",
                "pattern": "no_data",
                "asset_type": asset_type,
                "price_action": str(e),
                "indicators": "Недостаточно рыночных данных",
                "volatility": "Неизвестно",
                "volume": "Неизвестно",
                "unavailable": True,
                "source_asset": asset,
                "is_otc_proxy": False
            }

        if len(df) < 60:
            return {
                "asset": asset,
                "direction": "WAIT",
                "confidence": 0,
                "timeframe": timeframe,
                "risk": "⚪ НЕТ ДАННЫХ",
                "risk_level": "unknown",
                "pattern": "insufficient_history",
                "asset_type": asset_type,
                "price_action": "Недостаточно истории для анализа",
                "indicators": "Недостаточно данных",
                "volatility": "Неизвестно",
                "volume": "Неизвестно",
                "unavailable": True,
                "source_asset": source_asset,
                "is_otc_proxy": asset.endswith("/OTC")
            }

        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        ema9 = self._ema(close, 9)
        ema21 = self._ema(close, 21)
        ema50 = self._ema(close, 50)
        rsi = self._rsi(close, 14)
        _, _, macd_hist = self._macd(close)
        atr = self._atr(df, 14)

        last_close = close.iloc[-1]
        last_ema9 = ema9.iloc[-1]
        last_ema21 = ema21.iloc[-1]
        last_ema50 = ema50.iloc[-1]
        last_rsi = rsi.iloc[-1]
        last_macd_hist = macd_hist.iloc[-1]
        last_atr = atr.iloc[-1]

        recent_high = high.tail(20).max()
        recent_low = low.tail(20).min()
        avg_volume = volume.tail(20).mean()
        last_volume = volume.iloc[-1]

        score = 0
        reasons = []

        if last_close > last_ema9 > last_ema21 > last_ema50:
            score += 3
            reasons.append("сильный восходящий тренд по EMA")
        elif last_close < last_ema9 < last_ema21 < last_ema50:
            score -= 3
            reasons.append("сильный нисходящий тренд по EMA")
        elif last_close > last_ema21:
            score += 1
            reasons.append("цена выше EMA21")
        else:
            score -= 1
            reasons.append("цена ниже EMA21")

        if last_rsi < 30:
            score += 2
            reasons.append("RSI в перепроданности")
        elif last_rsi > 70:
            score -= 2
            reasons.append("RSI в перекупленности")
        elif last_rsi > 55:
            score += 1
            reasons.append("RSI подтверждает бычий импульс")
        elif last_rsi < 45:
            score -= 1
            reasons.append("RSI подтверждает медвежий импульс")

        if last_macd_hist > 0:
            score += 1
            reasons.append("MACD histogram выше нуля")
        else:
            score -= 1
            reasons.append("MACD histogram ниже нуля")

        if last_close >= recent_high * 0.998:
            score += 1
            reasons.append("цена у локального пробоя вверх")
        elif last_close <= recent_low * 1.002:
            score -= 1
            reasons.append("цена у локального пробоя вниз")

        if last_volume > avg_volume * 1.2:
            if score > 0:
                score += 1
                reasons.append("рост объема поддерживает движение вверх")
            elif score < 0:
                score -= 1
                reasons.append("рост объема поддерживает движение вниз")

        atr_pct = (last_atr / last_close) * 100 if last_close else 0
        if atr_pct > 2:
            volatility_text = "Высокая"
        elif atr_pct > 0.8:
            volatility_text = "Средняя"
        else:
            volatility_text = "Низкая"

        if last_volume > avg_volume * 1.3:
            volume_text = "Высокий"
        elif last_volume > avg_volume * 0.8:
            volume_text = "Средний"
        else:
            volume_text = "Низкий"

        if score >= 2:
            direction = "BUY"
            pattern = "bullish"
        elif score <= -2:
            direction = "SELL"
            pattern = "bearish"
        else:
            direction = "BUY" if score >= 0 else "SELL"
            pattern = "weak"

        confidence = min(92, max(51, 55 + abs(score) * 6))

        if confidence >= 84:
            risk = "🟢 НИЗКИЙ"
            risk_level = "low"
        elif confidence >= 70:
            risk = "🟡 СРЕДНИЙ"
            risk_level = "medium"
        else:
            risk = "🔴 ВЫСОКИЙ"
            risk_level = "high"

        indicators_text = (
            f"RSI: {last_rsi:.1f} | "
            f"EMA9/21/50: {last_ema9:.4f}/{last_ema21:.4f}/{last_ema50:.4f} | "
            f"MACD hist: {last_macd_hist:.5f} | "
            f"ATR: {last_atr:.5f}"
        )

        return {
            "asset": asset,
            "direction": direction,
            "confidence": int(confidence),
            "timeframe": timeframe,
            "risk": risk,
            "risk_level": risk_level,
            "pattern": pattern,
            "asset_type": asset_type,
            "price_action": "; ".join(reasons[:3]) if reasons else "нейтральная структура",
            "indicators": indicators_text,
            "volatility": volatility_text,
            "volume": volume_text,
            "unavailable": False,
            "is_otc_proxy": asset.endswith("/OTC"),
            "source_asset": source_asset
        }


neural_net = MarketAnalyzer()


# ========== ДОСТУП ==========
def check_user_access(user_id, username, first_name):
    if user_id == ADMIN_ID:
        execute_query(
            "UPDATE users SET is_verified = 1 WHERE telegram_id = ?",
            (user_id,),
            commit=True
        )
        execute_query(
            "DELETE FROM verification_requests WHERE user_id = ?",
            (user_id,),
            commit=True
        )
        execute_query(
            """INSERT OR IGNORE INTO users
               (telegram_id, username, first_name, join_date, is_verified)
               VALUES (?, ?, ?, ?, 1)""",
            (user_id, username, first_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            commit=True
        )
        return True, "owner"

    user_data = get_user(user_id)
    if not user_data:
        return False, "not_registered"

    user_dict = dict(user_data)
    if user_dict.get("is_verified", 0) == 1:
        return True, "verified"

    return False, "not_verified"


# ========== МЕНЮ ==========
def create_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("📈 Случайный сигнал")
    btn2 = types.KeyboardButton("🎯 Сигнал по активу")
    btn3 = types.KeyboardButton("⚙️ Настройки")
    btn4 = types.KeyboardButton("📊 Моя статистика")
    btn5 = types.KeyboardButton("👥 Рефералы")
    btn6 = types.KeyboardButton("ℹ️ Помощь")
    btn7 = types.KeyboardButton("🔐 Регистрация")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7)
    return markup


def create_settings_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("⏱️ Выбрать время")
    btn2 = types.KeyboardButton("🔙 Назад")
    markup.add(btn1, btn2)
    return markup


def create_assets_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_crypto = types.InlineKeyboardButton("💰 Криптовалюты (40+)", callback_data="category_crypto")
    btn_forex = types.InlineKeyboardButton("💱 Форекс (28+)", callback_data="category_forex")
    btn_commodities = types.InlineKeyboardButton("🛢️ Сырье (16+)", callback_data="category_commodities")
    btn_indices = types.InlineKeyboardButton("📊 Индексы (15+)", callback_data="category_indices")
    btn_otc = types.InlineKeyboardButton("📊 Крипто OTC (40+)", callback_data="category_otc")
    markup.add(btn_crypto, btn_forex)
    markup.add(btn_commodities, btn_indices)
    markup.add(btn_otc)
    return markup


def create_timeframe_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)

    for i in range(0, len(TIMEFRAMES), 2):
        if i + 1 < len(TIMEFRAMES):
            btn1 = types.InlineKeyboardButton(TIMEFRAMES[i], callback_data=f"timeframe_{TIMEFRAMES[i]}")
            btn2 = types.InlineKeyboardButton(TIMEFRAMES[i + 1], callback_data=f"timeframe_{TIMEFRAMES[i + 1]}")
            markup.add(btn1, btn2)
        else:
            btn = types.InlineKeyboardButton(TIMEFRAMES[i], callback_data=f"timeframe_{TIMEFRAMES[i]}")
            markup.add(btn)

    btn_random = types.InlineKeyboardButton("🎲 Случайное время", callback_data="timeframe_random")
    btn_cancel = types.InlineKeyboardButton("❌ Отмена", callback_data="timeframe_cancel")
    markup.add(btn_random, btn_cancel)
    return markup


def create_crypto_menu(page=1):
    markup = types.InlineKeyboardMarkup(row_width=2)
    items_per_page = 20
    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, len(CRYPTO_ASSETS))

    for i in range(start_idx, end_idx, 2):
        if i + 1 < end_idx:
            btn1 = types.InlineKeyboardButton(CRYPTO_ASSETS[i], callback_data=f"asset_{CRYPTO_ASSETS[i]}")
            btn2 = types.InlineKeyboardButton(CRYPTO_ASSETS[i + 1], callback_data=f"asset_{CRYPTO_ASSETS[i + 1]}")
            markup.add(btn1, btn2)
        else:
            btn = types.InlineKeyboardButton(CRYPTO_ASSETS[i], callback_data=f"asset_{CRYPTO_ASSETS[i]}")
            markup.add(btn)

    navigation_buttons = []

    if page > 1:
        navigation_buttons.append(types.InlineKeyboardButton("◀️ Назад", callback_data=f"crypto_page_{page - 1}"))
    if end_idx < len(CRYPTO_ASSETS):
        navigation_buttons.append(types.InlineKeyboardButton("Вперед ▶️", callback_data=f"crypto_page_{page + 1}"))

    if navigation_buttons:
        markup.add(*navigation_buttons)

    markup.add(types.InlineKeyboardButton("🔙 Назад к категориям", callback_data="back_to_categories"))
    return markup


def create_forex_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)

    for i in range(0, len(FOREX_ASSETS), 2):
        if i + 1 < len(FOREX_ASSETS):
            btn1 = types.InlineKeyboardButton(FOREX_ASSETS[i], callback_data=f"asset_{FOREX_ASSETS[i]}")
            btn2 = types.InlineKeyboardButton(FOREX_ASSETS[i + 1], callback_data=f"asset_{FOREX_ASSETS[i + 1]}")
            markup.add(btn1, btn2)
        else:
            btn = types.InlineKeyboardButton(FOREX_ASSETS[i], callback_data=f"asset_{FOREX_ASSETS[i]}")
            markup.add(btn)

    markup.add(types.InlineKeyboardButton("🔙 Назад к категориям", callback_data="back_to_categories"))
    return markup


def create_commodities_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)

    for i in range(0, len(COMMODITIES_ASSETS), 2):
        if i + 1 < len(COMMODITIES_ASSETS):
            btn1 = types.InlineKeyboardButton(COMMODITIES_ASSETS[i], callback_data=f"asset_{COMMODITIES_ASSETS[i]}")
            btn2 = types.InlineKeyboardButton(COMMODITIES_ASSETS[i + 1], callback_data=f"asset_{COMMODITIES_ASSETS[i + 1]}")
            markup.add(btn1, btn2)
        else:
            btn = types.InlineKeyboardButton(COMMODITIES_ASSETS[i], callback_data=f"asset_{COMMODITIES_ASSETS[i]}")
            markup.add(btn)

    markup.add(types.InlineKeyboardButton("🔙 Назад к категориям", callback_data="back_to_categories"))
    return markup


def create_indices_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)

    for i in range(0, len(INDICES_ASSETS), 2):
        if i + 1 < len(INDICES_ASSETS):
            btn1 = types.InlineKeyboardButton(INDICES_ASSETS[i], callback_data=f"asset_{INDICES_ASSETS[i]}")
            btn2 = types.InlineKeyboardButton(INDICES_ASSETS[i + 1], callback_data=f"asset_{INDICES_ASSETS[i + 1]}")
            markup.add(btn1, btn2)
        else:
            btn = types.InlineKeyboardButton(INDICES_ASSETS[i], callback_data=f"asset_{INDICES_ASSETS[i]}")
            markup.add(btn)

    markup.add(types.InlineKeyboardButton("🔙 Назад к категориям", callback_data="back_to_categories"))
    return markup


def create_otc_menu(page=1):
    markup = types.InlineKeyboardMarkup(row_width=2)
    items_per_page = 20
    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, len(OTC_ASSETS))

    for i in range(start_idx, end_idx, 2):
        if i + 1 < end_idx:
            btn1 = types.InlineKeyboardButton(OTC_ASSETS[i], callback_data=f"asset_{OTC_ASSETS[i]}")
            btn2 = types.InlineKeyboardButton(OTC_ASSETS[i + 1], callback_data=f"asset_{OTC_ASSETS[i + 1]}")
            markup.add(btn1, btn2)
        else:
            btn = types.InlineKeyboardButton(OTC_ASSETS[i], callback_data=f"asset_{OTC_ASSETS[i]}")
            markup.add(btn)

    navigation_buttons = []

    if page > 1:
        navigation_buttons.append(types.InlineKeyboardButton("◀️ Назад", callback_data=f"otc_page_{page - 1}"))
    if end_idx < len(OTC_ASSETS):
        navigation_buttons.append(types.InlineKeyboardButton("Вперед ▶️", callback_data=f"otc_page_{page + 1}"))

    if navigation_buttons:
        markup.add(*navigation_buttons)

    markup.add(types.InlineKeyboardButton("🔙 Назад к категориям", callback_data="back_to_categories"))
    return markup


# ========== СИГНАЛЫ ==========
def format_signal_message(signal_data, selected_asset=None, asset_source="🎲 Случайный актив"):
    if signal_data["direction"] == "BUY":
        direction_emoji = "📈"
        action = "ПОКУПКА (CALL)"
        color = "🟢"
    elif signal_data["direction"] == "SELL":
        direction_emoji = "📉"
        action = "ПРОДАЖА (PUT)"
        color = "🔴"
    else:
        direction_emoji = "⏸"
        action = "ОЖИДАНИЕ"
        color = "⚪"

    asset_type_emoji = {
        "crypto": "💰",
        "forex": "💱",
        "commodity": "🛢️",
        "index": "📊",
        "otc": "📊"
    }.get(signal_data["asset_type"], "📊")

    selected_line = f"🎯 **Выбранный актив:** {selected_asset}\n" if selected_asset else ""

    proxy_note = ""
    if signal_data.get("is_otc_proxy"):
        proxy_note = f"📌 **OTC proxy-анализ:** расчёт выполнен по {signal_data.get('source_asset', signal_data['asset'])}\n"

    return f"""
{direction_emoji} **СИГНАЛ ПО РЫНКУ** {direction_emoji}

{asset_source}
{selected_line}{asset_type_emoji} **ТИП АКТИВА:** {signal_data['asset_type'].upper()}
{color} **АКТИВ:** {signal_data['asset']}
{proxy_note}🎯 **ДЕЙСТВИЕ:** {action}
⏱ **ЭКСПИРАЦИЯ:** {signal_data['timeframe']}
📊 **УВЕРЕННОСТЬ:** {signal_data['confidence']}%
⚠️ **РИСК:** {signal_data['risk']}

🧠 **АНАЛИЗ:**
• Структура: {signal_data['pattern'].upper()}
• Цена: {signal_data['price_action']}
• Индикаторы: {signal_data['indicators']}
• Волатильность: {signal_data['volatility']}
• Объем: {signal_data['volume']}
• Основано на EMA / RSI / MACD / ATR / объеме

📈 **АНАЛИТИЧЕСКИЙ ВЫВОД:**
1. Направление рассчитано по теханализу
2. Таймфрейм анализа: {signal_data['timeframe']}
3. Слабые сигналы лучше пропускать
4. Не используйте крупный риск на одну сделку

🕐 **СИГНАЛ АКТУАЛЕН:** 1-3 минуты
📅 **ВРЕМЯ:** {datetime.now().strftime("%H:%M %d.%m.%Y")}
"""


def store_signal(user_id, signal_data):
    execute_query(
        """INSERT INTO signals (user_id, signal_date, asset, direction, timeframe, confidence)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            signal_data["asset"],
            signal_data["direction"],
            signal_data["timeframe"],
            signal_data["confidence"]
        ),
        commit=True
    )

    execute_query(
        "UPDATE users SET signals_count = signals_count + 1, last_signal_date = ? WHERE telegram_id = ?",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id),
        commit=True
    )


def generate_signal(message, asset=None, random_asset=False, timeframe=None):
    try:
        user = message.from_user
        access, status = check_user_access(user.id, user.username, user.first_name)

        if not access:
            if status == "not_registered":
                bot.send_message(
                    message.chat.id,
                    "❌ Вы не зарегистрированы. Нажмите '🔐 Регистрация'",
                    reply_markup=create_main_menu()
                )
                return

            verification = execute_query(
                "SELECT status FROM verification_requests WHERE user_id = ? ORDER BY request_date DESC LIMIT 1",
                (user.id,),
                fetchone=True
            )

            status_msg = ""
            if verification:
                ver_status = dict(verification).get("status", "PENDING")
                if ver_status == "PENDING":
                    status_msg = "⏳ Ваша заявка на проверке у администратора"
                elif ver_status == "REJECTED":
                    status_msg = "❌ Ваша заявка отклонена администратором"
                elif ver_status == "APPROVED":
                    status_msg = "✅ Ваша заявка одобрена (используйте /fix для активации)"

            bot.send_message(
                message.chat.id,
                f"🔒 **ДОСТУП ЗАКРЫТ!**\n\n{status_msg}\n\n📌 Для получения сигналов необходимо подтверждение аккаунта администратором.",
                parse_mode="Markdown",
                reply_markup=create_main_menu()
            )
            return

        user_data = get_user(user.id)
        if not user_data:
            bot.send_message(
                message.chat.id,
                "❌ Ошибка доступа. Попробуйте снова.",
                reply_markup=create_main_menu()
            )
            return

        user_dict = dict(user_data)
        if not timeframe:
            preferred_timeframe = user_dict.get("preferred_timeframe", "")
            if preferred_timeframe:
                timeframe = preferred_timeframe

        bot.send_message(message.chat.id, "🧠 Анализирую рынок по свечам...")
        time.sleep(1)

        if asset:
            signal_data = neural_net.analyze_market(asset, timeframe)
            asset_source = "🎯 По вашему выбору"
        elif random_asset:
            signal_data = neural_net.analyze_market(None, timeframe)
            asset_source = "🎲 Случайный актив"
        else:
            signal_data = neural_net.analyze_market(None, timeframe)
            asset_source = "🎲 Случайный актив"

        if signal_data.get("unavailable"):
            bot.send_message(
                message.chat.id,
                f"⚠️ По активу **{signal_data['asset']}** сейчас нельзя построить сигнал.\n\n"
                f"Причина: {signal_data['price_action']}\n\n"
                f"Попробуйте другой актив
