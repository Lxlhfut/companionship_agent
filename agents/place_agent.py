import os
import requests
import math


def _safe_str(value, default=""):
    if isinstance(value, list):
        return ", ".join([str(v) for v in value if v]) if value else default
    return str(value) if value is not None else default


def _safe_get_distance(poi, default=999999):
    dist = poi.get("distance", default)
    if isinstance(dist, list):
        dist = dist[0] if dist else default
    try:
        return float(dist)
    except (ValueError, TypeError):
        return float(default)


class PlaceAgent:
    def __init__(self):
        self.api_key = os.getenv("AMAP_API_KEY")
        self.base_url = "https://restapi.amap.com/v3/place/text"
        self.geocode_url = "https://restapi.amap.com/v3/geocode/geo"

    def geocode(self, address, city=None):
        """将地址转换为经纬度坐标"""
        params = {
            "key": self.api_key,
            "address": address
        }
        if city:
            params["city"] = city
        try:
            resp = requests.get(self.geocode_url, params=params, timeout=10)
            data = resp.json()
            if data.get("status") == "1" and data.get("geocodes"):
                location = data["geocodes"][0].get("location")
                if location:
                    lon, lat = location.split(",")
                    return float(lon), float(lat)
        except Exception:
            pass
        return None, None

    def _calc_distance(self, lon1, lat1, lon2, lat2):
        """计算两个经纬度之间的直线距离（米），使用Haversine公式"""
        R = 6371000  # 地球半径，米
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def search_places(self, keywords, city=None, types=None, location=None, page=1, offset=50):
        """原始搜索，返回单页结果和总数"""
        params = {
            "key": self.api_key,
            "keywords": keywords,
            "offset": offset,
            "page": page,
            "extensions": "all"
        }
        if city:
            params["city"] = city
        if types:
            params["types"] = types
        if location:
            params["location"] = location  # "经度,纬度"

        try:
            resp = requests.get(self.base_url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "1":
                return data.get("pois", []), int(data.get("count", 0))
            return [], 0
        except Exception:
            return [], 0

    def search_places_sorted(self, keywords, city=None, place_type=None, ref_lon=None, ref_lat=None, max_count=200):
        """
        增强搜索：最多获取max_count条结果，统一排序后返回。
        若提供ref_lon, ref_lat，则计算每个POI到参照点的距离并附加到结果中。
        """
        type_map = {
            "公园": "110100",
            "医院": "090000",
            "景点": "110000",
            "养老院": "080304",
            "社区中心": "080100",
            "健身广场": "080502"
        }
        types = type_map.get(place_type) if place_type in type_map else None

        # 第一页获取总数
        pois, total = self.search_places(keywords, city, types, None, 1, 50)
        if not pois:
            # 尝试备选关键词
            if place_type == "健身广场":
                pois, total = self.search_places("健身", city, None, None, 1, 50)
                if not pois:
                    pois, total = self.search_places("广场", city, None, None, 1, 50)
            elif place_type == "养老院":
                pois, total = self.search_places("敬老院", city, None, None, 1, 50)
                if not pois:
                    pois, total = self.search_places("福利院", city, None, None, 1, 50)

        if total == 0:
            return [], 0

        # 限制最多获取max_count条
        fetch_count = min(total, max_count)
        all_pois = list(pois)
        page = 2
        while len(all_pois) < fetch_count:
            p, _ = self.search_places(keywords, city, types, None, page, 50)
            if not p:
                break
            all_pois.extend(p)
            page += 1
            # 防止死循环
            if page > 100:
                break

        # 截取至max_count
        all_pois = all_pois[:max_count]

        # 如果有参照点坐标，计算距离并添加到POI中
        if ref_lon is not None and ref_lat is not None:
            for poi in all_pois:
                loc = poi.get("location")
                if loc:
                    try:
                        lon_str, lat_str = loc.split(",")
                        lon = float(lon_str)
                        lat = float(lat_str)
                        dist = self._calc_distance(ref_lon, ref_lat, lon, lat)
                        poi["calculated_distance"] = round(dist)
                    except:
                        poi["calculated_distance"] = 999999
                else:
                    poi["calculated_distance"] = 999999
        else:
            # 无参照点，保留原有distance字段（由高德根据IP或城市中心返回）
            pass

        # 排序
        if place_type == "医院":
            all_pois = self._sort_hospitals(all_pois)
        elif place_type == "公园":
            all_pois = self._sort_parks(all_pois)
        elif place_type == "景点":
            all_pois = self._sort_scenic(all_pois)
        else:
            # 默认按距离排序（使用计算距离或原始distance）
            all_pois = self._sort_by_distance(all_pois)

        return all_pois, len(all_pois)

    def _sort_by_distance(self, pois):
        """按距离排序（优先使用计算距离，否则使用高德返回的distance）"""

        def get_dist(poi):
            if "calculated_distance" in poi:
                return poi["calculated_distance"]
            return _safe_get_distance(poi)

        return sorted(pois, key=get_dist)

    def _sort_hospitals(self, pois):
        level_score = {
            "三级甲等": 100, "三甲": 100, "三级": 90,
            "二级甲等": 80, "二甲": 80, "二级": 70,
            "一级甲等": 60, "一甲": 60, "一级": 50
        }

        def get_score(poi):
            name = _safe_str(poi.get("name", ""))
            addr = _safe_str(poi.get("address", ""))
            info = name + addr
            score = 0
            for key, val in level_score.items():
                if key in info:
                    score = val
                    break
            dist = poi.get("calculated_distance", _safe_get_distance(poi))
            return (-score, dist)

        return sorted(pois, key=get_score)

    def _sort_parks(self, pois):
        def get_key(poi):
            name = _safe_str(poi.get("name", ""))
            is_park = 1 if "公园" in name else 0
            dist = poi.get("calculated_distance", _safe_get_distance(poi))
            return (-is_park, dist)

        return sorted(pois, key=get_key)

    def _sort_scenic(self, pois):
        level_score = {"5A": 100, "4A": 80, "3A": 60, "2A": 40, "A": 20}

        def get_score(poi):
            name = _safe_str(poi.get("name", ""))
            addr = _safe_str(poi.get("address", ""))
            info = name + addr
            score = 0
            for key, val in level_score.items():
                if key in info:
                    score = val
                    break
            dist = poi.get("calculated_distance", _safe_get_distance(poi))
            return (-score, dist)

        return sorted(pois, key=get_score)