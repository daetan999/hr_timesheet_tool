"""Feast feature definitions (illustrative blueprint).

Entity and feature-view shapes for the three engineered feature families.
Source tables and connection configuration are placeholders.
"""
from datetime import timedelta

from feast import Entity, FeatureView, Field
from feast.infra.offline_stores.snowflake_source import SnowflakeSource
from feast.types import Float32, Int64

property_entity = Entity(name="property_id", description="Anonymized property identifier")
room_class = Entity(name="room_class_id", description="Room class within a property")
hvac_asset = Entity(name="hvac_asset_id", description="Chiller/boiler asset identifier")

demand_lag_source = SnowflakeSource(
    table="<offline_store>.<feature_schema>.F_DEMAND_LAG",  # sanitized placeholder
    timestamp_field="event_ts",
)

f_demand_lag = FeatureView(
    name="f_demand_lag",
    entities=[property_entity, room_class],
    ttl=timedelta(days=2),
    schema=[
        Field(name="adr_t1", dtype=Float32),
        Field(name="adr_t7", dtype=Float32),
        Field(name="adr_t14", dtype=Float32),
        Field(name="adr_t30", dtype=Float32),
        Field(name="occupancy_t1", dtype=Float32),
        Field(name="occupancy_t7", dtype=Float32),
        Field(name="otb_velocity", dtype=Float32),  # first derivative of on-the-book bookings
    ],
    source=demand_lag_source,
    online=True,  # Redis: <15 ms p99 retrieval SLA
)

f_climate_index = FeatureView(
    name="f_climate_index",
    entities=[property_entity],
    ttl=timedelta(days=1),
    schema=[
        Field(name="cooling_degree_days", dtype=Float32),  # vs 18C base
        Field(name="heating_degree_days", dtype=Float32),
    ],
    source=SnowflakeSource(
        table="<offline_store>.<feature_schema>.F_CLIMATE_INDEX",
        timestamp_field="event_ts",
    ),
    online=True,
)

f_telemetry_spectral = FeatureView(
    name="f_telemetry_spectral",
    entities=[hvac_asset],
    ttl=timedelta(hours=1),
    schema=[
        Field(name="fft_band_low", dtype=Float32),
        Field(name="fft_band_mid", dtype=Float32),
        Field(name="fft_band_high", dtype=Float32),
        Field(name="peak_frequency_hz", dtype=Float32),
        Field(name="kurtosis", dtype=Float32),
        Field(name="sample_count", dtype=Int64),
    ],
    source=SnowflakeSource(
        table="<offline_store>.<feature_schema>.F_TELEMETRY_SPECTRAL",
        timestamp_field="event_ts",
    ),
    online=True,
)
