from dagster import asset


def _mean(values: list) -> float | None:
    valid = [v for v in values if v is not None]
    return round(sum(valid) / len(valid), 2) if valid else None


def _safe_max(values: list) -> float | None:
    valid = [v for v in values if v is not None]
    return round(max(valid), 2) if valid else None


def _safe_min(values: list) -> float | None:
    valid = [v for v in values if v is not None]
    return round(min(valid), 2) if valid else None


@asset(group_name="weather_rj")
def transform_weather_rj(context, validate_weather_rj: dict) -> dict:
    """Aggregates hourly data into daily stats for Rio de Janeiro."""
    hourly = validate_weather_rj["payload"]["hourly"]

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

    daily = []
    for date, vals in by_date.items():
        row = {
            "date": date,
            "temp_max_c": _safe_max(vals["temperature_2m"]),
            "temp_min_c": _safe_min(vals["temperature_2m"]),
            "temp_mean_c": _mean(vals["temperature_2m"]),
            "humidity_mean": _mean(vals["relativehumidity_2m"]),
            "wind_max_kmh": _safe_max(vals["windspeed_10m"]),
            "precipitation_mm": round(
                sum(v for v in vals["precipitation"] if v is not None), 2
            ),
        }
        daily.append(row)
        context.log.info(
            f"{date}: temp {row['temp_min_c']}–{row['temp_max_c']}°C, "
            f"humidity {row['humidity_mean']}%, wind max {row['wind_max_kmh']} km/h"
        )

    return {"raw": validate_weather_rj, "daily": daily}
