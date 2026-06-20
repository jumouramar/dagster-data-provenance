class TransformWeatherDaily:
    def transform(self, hourly: dict) -> list[dict]:
        by_date: dict[str, dict] = {}
        for i, ts in enumerate(hourly["time"]):
            date = ts[:10]
            if date not in by_date:
                by_date[date] = {
                    "temperature_2m": [],
                    "relativehumidity_2m": [],
                    "windspeed_10m": [],
                    "precipitation": [],
                }
            by_date[date]["temperature_2m"].append(hourly["temperature_2m"][i])
            by_date[date]["relativehumidity_2m"].append(hourly["relativehumidity_2m"][i])
            by_date[date]["windspeed_10m"].append(hourly["windspeed_10m"][i])
            by_date[date]["precipitation"].append(hourly["precipitation"][i])

        return [
            {
                "date": date,
                "temp_max_c":          self._max(vals["temperature_2m"]),
                "temp_min_c":          self._min(vals["temperature_2m"]),
                "temp_mean_c":         self._mean(vals["temperature_2m"]),
                "humidity_min":        self._min(vals["relativehumidity_2m"]),
                "humidity_mean":       self._mean(vals["relativehumidity_2m"]),
                "humidity_max":        self._max(vals["relativehumidity_2m"]),
                "wind_mean_kmh":       self._mean(vals["windspeed_10m"]),
                "wind_max_kmh":        self._max(vals["windspeed_10m"]),
                "precipitation_mm":    round(sum(v for v in vals["precipitation"] if v is not None), 2),
                "precipitation_hours": sum(1 for v in vals["precipitation"] if v and v > 0),
            }
            for date, vals in by_date.items()
        ]

    def _mean(self, values: list) -> float | None:
        valid = [v for v in values if v is not None]
        return round(sum(valid) / len(valid), 2) if valid else None

    def _max(self, values: list) -> float | None:
        valid = [v for v in values if v is not None]
        return round(max(valid), 2) if valid else None

    def _min(self, values: list) -> float | None:
        valid = [v for v in values if v is not None]
        return round(min(valid), 2) if valid else None
