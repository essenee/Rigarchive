"""Bounded human registry lookup and unsaved canonical construction.

No research, approval, candidate mutation, automatic registration or publication.
Versioned import plans/executors must not silently attach an unpinned Engine FK.
"""
from django.core.exceptions import ValidationError
from reference.models import Engine, VehicleDefinition, normalize_engine_code
from reference.powertrain import FIELDS, decimal_string, record_powertrain, validate_powertrain


class EngineRegistryError(ValidationError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message, code=code)


def resolve_engine(manufacturer, engine_code, *, incoming_powertrain=None):
    """Look up an exact manufacturer/code; only explicit supplied values can conflict."""
    engine_code = normalize_engine_code(engine_code)
    engine = Engine.objects.filter(manufacturer=manufacturer, engine_code=engine_code).first()
    if engine is None:
        raise EngineRegistryError("ENGINE_NOT_REGISTERED", f"Engine {engine_code} is not registered for this manufacturer.")
    values = record_powertrain(engine)
    if incoming_powertrain is not None:
        if not isinstance(incoming_powertrain, dict) or set(incoming_powertrain) - set(FIELDS):
            raise ValidationError("Incoming engine properties must use the existing five tracked fields.")
        for key, incoming in incoming_powertrain.items():
            if incoming is None:
                continue
            if key == 'engine_displacement_liters':
                incoming = decimal_string(incoming)
            if type(incoming) is not type(values[key]) or incoming != values[key]:
                raise EngineRegistryError("ENGINE_REGISTRY_CONFLICT", f"Explicit {key} contradicts registered engine {engine_code}; registered value retained.")
    try:
        validate_powertrain(values, complete=True)
    except ValidationError as exc:
        raise EngineRegistryError("ENGINE_REGISTRY_INCOMPLETE", f"Engine {engine_code} lacks a complete supported construction identity: {exc}") from exc
    return engine


def prepare_registered_vehicle(manufacturer, engine_code, *, incoming_powertrain=None, **vehicle_fields):
    """Return an unsaved vehicle; caller still needs its normal plan/authorization path.

    This is not a Candidate v3 adapter or an import executor. Existing versioned
    plans cannot pin registry identity/state, so they are intentionally unchanged.
    """
    if {'engine', 'engine_id', 'pk', 'id'} & vehicle_fields.keys():
        raise ValidationError("Resolve an Engine using manufacturer and code for new construction.")
    explicit = {key: vehicle_fields.pop(key) for key in FIELDS if key in vehicle_fields}
    engine = resolve_engine(manufacturer, engine_code, incoming_powertrain=incoming_powertrain)
    # Check separately: neither input dictionary can overwrite the other's conflict.
    if explicit:
        resolve_engine(manufacturer, engine_code, incoming_powertrain=explicit)
    vehicle_fields.setdefault('engine_name', engine.name)
    vehicle = VehicleDefinition(engine=engine, **vehicle_fields, **record_powertrain(engine))
    vehicle._validate_registry_engine()
    return vehicle
