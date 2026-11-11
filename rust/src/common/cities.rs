//! Offline city list for the sunrise/sunset schedule.

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct City {
    pub key: &'static str,
    pub en: &'static str,
    pub fa: &'static str,
    pub lat: f64,
    pub lon: f64,
}

const fn city(key: &'static str, en: &'static str, fa: &'static str, lat: f64, lon: f64) -> City {
    City { key, en, fa, lat, lon }
}

pub const DEFAULT_CITY: &str = "tehran";

pub static CITIES: &[City] = &[
    city("tehran", "Tehran", "تهران", 35.6892, 51.3890),
    city("mashhad", "Mashhad", "مشهد", 36.2605, 59.6168),
    city("isfahan", "Isfahan", "اصفهان", 32.6546, 51.6680),
    city("shiraz", "Shiraz", "شیراز", 29.5918, 52.5837),
    city("tabriz", "Tabriz", "تبریز", 38.0962, 46.2738),
    city("karaj", "Karaj", "کرج", 35.8400, 50.9391),
    city("ahvaz", "Ahvaz", "اهواز", 31.3183, 48.6706),
    city("qom", "Qom", "قم", 34.6416, 50.8746),
    city("kermanshah", "Kermanshah", "کرمانشاه", 34.3277, 47.0778),
    city("rasht", "Rasht", "رشت", 37.2808, 49.5832),
    city("urmia", "Urmia", "ارومیه", 37.5527, 45.0761),
    city("yazd", "Yazd", "یزد", 31.8974, 54.3569),
    city("kerman", "Kerman", "کرمان", 30.2839, 57.0834),
    city("zahedan", "Zahedan", "زاهدان", 29.4963, 60.8629),
    city("bandar_abbas", "Bandar Abbas", "بندرعباس", 27.1865, 56.2808),
    city("hamadan", "Hamadan", "همدان", 34.7992, 48.5146),
    city("ardabil", "Ardabil", "اردبیل", 38.2498, 48.2933),
    city("sari", "Sari", "ساری", 36.5633, 53.0601),
    city("gorgan", "Gorgan", "گرگان", 36.8427, 54.4439),
    city("bushehr", "Bushehr", "بوشهر", 28.9234, 50.8203),
    city("kabul", "Kabul", "کابل", 34.5553, 69.2075),
    city("dubai", "Dubai", "دبی", 25.2048, 55.2708),
    city("istanbul", "Istanbul", "استانبول", 41.0082, 28.9784),
    city("ankara", "Ankara", "آنکارا", 39.9334, 32.8597),
    city("baku", "Baku", "باکو", 40.4093, 49.8671),
    city("baghdad", "Baghdad", "بغداد", 33.3152, 44.3661),
    city("riyadh", "Riyadh", "ریاض", 24.7136, 46.6753),
    city("cairo", "Cairo", "قاهره", 30.0444, 31.2357),
    city("moscow", "Moscow", "مسکو", 55.7558, 37.6173),
    city("london", "London", "لندن", 51.5072, -0.1276),
    city("paris", "Paris", "پاریس", 48.8566, 2.3522),
    city("berlin", "Berlin", "برلین", 52.5200, 13.4050),
    city("rome", "Rome", "رم", 41.9028, 12.4964),
    city("madrid", "Madrid", "مادرید", 40.4168, -3.7038),
    city("stockholm", "Stockholm", "استکهلم", 59.3293, 18.0686),
    city("amsterdam", "Amsterdam", "آمستردام", 52.3676, 4.9041),
    city("toronto", "Toronto", "تورنتو", 43.6532, -79.3832),
    city("vancouver", "Vancouver", "ونکوور", 49.2827, -123.1207),
    city("new_york", "New York", "نیویورک", 40.7128, -74.0060),
    city("chicago", "Chicago", "شیکاگو", 41.8781, -87.6298),
    city("los_angeles", "Los Angeles", "لس‌آنجلس", 34.0522, -118.2437),
    city("mexico_city", "Mexico City", "مکزیکو سیتی", 19.4326, -99.1332),
    city("sao_paulo", "São Paulo", "سائوپائولو", -23.5505, -46.6333),
    city("delhi", "New Delhi", "دهلی نو", 28.6139, 77.2090),
    city("karachi", "Karachi", "کراچی", 24.8607, 67.0011),
    city("dhaka", "Dhaka", "داکا", 23.8103, 90.4125),
    city("bangkok", "Bangkok", "بانکوک", 13.7563, 100.5018),
    city("singapore", "Singapore", "سنگاپور", 1.3521, 103.8198),
    city("beijing", "Beijing", "پکن", 39.9042, 116.4074),
    city("tokyo", "Tokyo", "توکیو", 35.6762, 139.6503),
    city("seoul", "Seoul", "سئول", 37.5665, 126.9780),
    city("sydney", "Sydney", "سیدنی", -33.8688, 151.2093),
    city("johannesburg", "Johannesburg", "ژوهانسبورگ", -26.2041, 28.0473),
];

/// Look a city up by key; unknown keys fall back to Tehran.
pub fn city_by_key(key: &str) -> &'static City {
    CITIES.iter().find(|c| c.key == key).or_else(|| CITIES.iter().find(|c| c.key == DEFAULT_CITY)).expect("the default city exists")
}

pub fn city_name(city: &City, language: &str) -> &'static str {
    if language == "fa" {
        city.fa
    } else {
        city.en
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    #[test]
    fn cities_are_unique_and_sane() {
        let keys: HashSet<_> = CITIES.iter().map(|c| c.key).collect();
        assert_eq!(keys.len(), CITIES.len());
        assert!(keys.contains("tehran"));
        assert!(CITIES
            .iter()
            .all(|c| (-90.0..=90.0).contains(&c.lat) && (-180.0..=180.0).contains(&c.lon) && !c.fa.is_empty() && !c.en.is_empty()));
        assert_eq!(city_by_key("nope").key, "tehran");
        assert_eq!(city_name(city_by_key("tehran"), "fa"), "تهران");
        assert_eq!(city_name(city_by_key("tehran"), "en"), "Tehran");
    }

    #[test]
    fn has_the_same_number_of_cities_as_the_python_app() {
        assert_eq!(CITIES.len(), 53);
    }
}
