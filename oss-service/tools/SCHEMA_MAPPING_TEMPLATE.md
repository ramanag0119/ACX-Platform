# OSS → HMS contract mapping (fill from discovery)

Produced by `tools/discover_schema.py` against the OSS DB, then completed by
hand. Each HMS contract field (left) is mapped to its OSS source (right). Where
the OSS schema has no equivalent, record `NONE` and how the field is derived or
defaulted — never invent a value.

> Status: **PENDING** — run discovery once `OSS_DATABASE_URL` is provided and
> access is authorised. Until this doc is filled, adapters raise
> `AdapterNotMapped` (503).

## devices  (contract: `app/schemas/device.py::DeviceRead`)
| HMS contract field | OSS table.column | Transform / notes |
|---|---|---|
| id | ? | |
| device_uid | ? | |
| device_name | ? | |
| device_type / device_type_name / device_short_code | ? | lookup/join |
| facility_id / amenity_id | ? | id-only cross-ref to hms_db |
| building/floor (id+name) | ? | resolved via amenity→property_chain? or NONE |
| health_status / device_config_status | ? | enum label mapping |
| current/expected firmware + firmware_up_to_date | ? | derived |
| created_on / updated_on | ? | |

## device_types  (`DeviceTypeRead`)
| id / name / device_short_code | ? | |

## device-stats / device-params / current-stats / other-readings  (`app/schemas/telemetry.py`)
| … | ? | note EAV vs columnar shape differences |

## alerts / incidents / value-alerts  (`app/schemas/alert.py`)
| … | ? | two alert entities; incident→alert direction |

## energy-stats  (`app/schemas/energy.py::EnergyStatRead`)
| device_name / facility_id / amenity_id / hour / energy_consumed | ? | hour epoch + derived hour_timestamp |

## Open questions for the DB owner
- Confirm the OSS tables that correspond to each HMS resource.
- Confirm how OSS rows reference HMS `amenity_id` / `facility_id` (same UUIDs?).
- Confirm timestamp columns and time zone handling.
