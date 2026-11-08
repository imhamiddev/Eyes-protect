"""Offline city list for the sunrise/sunset schedule: (key, English, Persian, lat, lon)."""
from __future__ import annotations

from typing import NamedTuple


class City(NamedTuple):
    key: str
    en: str
    fa: str
    lat: float
    lon: float


CITIES: tuple[City, ...] = (
    City("tehran", "Tehran", "تهران", 35.6892, 51.3890),
    City("mashhad", "Mashhad", "مشهد", 36.2605, 59.6168),
    City("isfahan", "Isfahan", "اصفهان", 32.6546, 51.6680),
    City("shiraz", "Shiraz", "شیراز", 29.5918, 52.5837),
    City("tabriz", "Tabriz", "تبریز", 38.0962, 46.2738),
    City("karaj", "Karaj", "کرج", 35.8400, 50.9391),
    City("ahvaz", "Ahvaz", "اهواز", 31.3183, 48.6706),
    City("qom", "Qom", "قم", 34.6416, 50.8746),
    City("kermanshah", "Kermanshah", "کرمانشاه", 34.3277, 47.0778),
    City("rasht", "Rasht", "رشت", 37.2808, 49.5832),
    City("urmia", "Urmia", "ارومیه", 37.5527, 45.0761),
    City("yazd", "Yazd", "یزد", 31.8974, 54.3569),
    City("kerman", "Kerman", "کرمان", 30.2839, 57.0834),
    City("zahedan", "Zahedan", "زاهدان", 29.4963, 60.8629),
    City("bandar_abbas", "Bandar Abbas", "بندرعباس", 27.1865, 56.2808),
    City("hamadan", "Hamadan", "همدان", 34.7992, 48.5146),
    City("ardabil", "Ardabil", "اردبیل", 38.2498, 48.2933),
    City("sari", "Sari", "ساری", 36.5633, 53.0601),
    City("gorgan", "Gorgan", "گرگان", 36.8427, 54.4439),
    City("bushehr", "Bushehr", "بوشهر", 28.9234, 50.8203),
    City("kabul", "Kabul", "کابل", 34.5553, 69.2075),
    City("dubai", "Dubai", "دبی", 25.2048, 55.2708),
    City("istanbul", "Istanbul", "استانبول", 41.0082, 28.9784),
    City("ankara", "Ankara", "آنکارا", 39.9334, 32.8597),
    City("baku", "Baku", "باکو", 40.4093, 49.8671),
    City("baghdad", "Baghdad", "بغداد", 33.3152, 44.3661),
    City("riyadh", "Riyadh", "ریاض", 24.7136, 46.6753),
    City("cairo", "Cairo", "قاهره", 30.0444, 31.2357),
    City("moscow", "Moscow", "مسکو", 55.7558, 37.6173),
    City("london", "London", "لندن", 51.5072, -0.1276),
    City("paris", "Paris", "پاریس", 48.8566, 2.3522),
    City("berlin", "Berlin", "برلین", 52.5200, 13.4050),
    City("rome", "Rome", "رم", 41.9028, 12.4964),
    City("madrid", "Madrid", "مادرید", 40.4168, -3.7038),
    City("stockholm", "Stockholm", "استکهلم", 59.3293, 18.0686),
    City("amsterdam", "Amsterdam", "آمستردام", 52.3676, 4.9041),
    City("toronto", "Toronto", "تورنتو", 43.6532, -79.3832),
    City("vancouver", "Vancouver", "ونکوور", 49.2827, -123.1207),
    City("new_york", "New York", "نیویورک", 40.7128, -74.0060),
    City("chicago", "Chicago", "شیکاگو", 41.8781, -87.6298),
    City("los_angeles", "Los Angeles", "لس‌آنجلس", 34.0522, -118.2437),
    City("mexico_city", "Mexico City", "مکزیکو سیتی", 19.4326, -99.1332),
    City("sao_paulo", "São Paulo", "سائوپائولو", -23.5505, -46.6333),
    City("delhi", "New Delhi", "دهلی نو", 28.6139, 77.2090),
    City("karachi", "Karachi", "کراچی", 24.8607, 67.0011),
    City("dhaka", "Dhaka", "داکا", 23.8103, 90.4125),
    City("bangkok", "Bangkok", "بانکوک", 13.7563, 100.5018),
    City("singapore", "Singapore", "سنگاپور", 1.3521, 103.8198),
    City("beijing", "Beijing", "پکن", 39.9042, 116.4074),
    City("tokyo", "Tokyo", "توکیو", 35.6762, 139.6503),
    City("seoul", "Seoul", "سئول", 37.5665, 126.9780),
    City("sydney", "Sydney", "سیدنی", -33.8688, 151.2093),
    City("johannesburg", "Johannesburg", "ژوهانسبورگ", -26.2041, 28.0473),
)

DEFAULT_CITY = "tehran"
_BY_KEY = {c.key: c for c in CITIES}


def city_by_key(key: str) -> City:
    return _BY_KEY.get(key) or _BY_KEY[DEFAULT_CITY]


def city_name(city: City, language: str) -> str:
    return city.fa if language == "fa" else city.en
