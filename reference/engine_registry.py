"""Bounded human registry lookup and unsaved canonical construction.

No research, approval, candidate mutation, automatic registration or publication.
Versioned import plans/executors must not silently attach an unpinned Engine FK.
"""
from django.core.exceptions import ValidationError
from reference.models import Engine, VehicleDefinition, normalize_engine_code, normalize_internal_variant_key
from reference.powertrain import FIELDS, decimal_string, record_powertrain, validate_powertrain


class EngineRegistryError(ValidationError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message, code=code)


UNSET_VARIANT = object()


def resolve_engine(manufacturer, engine_code, *, internal_variant_key=UNSET_VARIANT,
                   engine_pk=None, engine_uuid=None, incoming_powertrain=None):
    """Exact pins take precedence; omitted keys require a unique complete code."""
    engine_code = normalize_engine_code(engine_code)
    manufacturer_pk = getattr(manufacturer, 'pk', manufacturer)
    key = (normalize_internal_variant_key(internal_variant_key)
           if internal_variant_key is not UNSET_VARIANT else UNSET_VARIANT)
    if engine_pk is not None or engine_uuid is not None:
        engines = Engine.objects.all()
        if engine_pk is not None:
            engines = engines.filter(pk=engine_pk)
        if engine_uuid is not None:
            engines = engines.filter(uuid=engine_uuid)
        engine = engines.first()  # Unique PK/UUID, never a code-only choice.
        if engine is None:
            raise EngineRegistryError("ENGINE_NOT_REGISTERED", "Pinned Engine is unavailable.")
        if (engine.manufacturer_id != manufacturer_pk or engine.engine_code != engine_code
                or (key is not UNSET_VARIANT and engine.internal_variant_key != key)):
            raise EngineRegistryError("ENGINE_REGISTRY_CONFLICT", "Pinned Engine identity differs from the supplied identity.")
    else:
        engines = Engine.objects.filter(manufacturer_id=manufacturer_pk, engine_code=engine_code)
        if key is not UNSET_VARIANT:
            engines = engines.filter(internal_variant_key=key)
        matches = list(engines[:2])
        if not matches:
            raise EngineRegistryError("ENGINE_NOT_REGISTERED", f"Engine {engine_code} is not registered for this manufacturer/key.")
        if len(matches) != 1:
            raise EngineRegistryError("ENGINE_REGISTRY_AMBIGUOUS", f"Engine {engine_code} has multiple registered variants; an exact reviewed reference is required.")
        engine = matches[0]
    return validate_engine_properties(engine, incoming_powertrain=incoming_powertrain)


def validate_engine_properties(engine, *, incoming_powertrain=None):
    """Validate claims against an already selected instance without losing its pin."""
    engine_code = engine.engine_code
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


def prepare_registered_vehicle(manufacturer, engine_code, *, internal_variant_key=UNSET_VARIANT,
                               engine_pk=None, engine_uuid=None, incoming_powertrain=None, **vehicle_fields):
    """Return an unsaved vehicle; caller still needs its normal plan/authorization path.

    This is not a Candidate v3 adapter or an import executor. Existing versioned
    plans cannot pin registry identity/state, so they are intentionally unchanged.
    """
    if {'engine', 'engine_id', 'pk', 'id'} & vehicle_fields.keys():
        raise ValidationError("Resolve an Engine using manufacturer and code for new construction.")
    explicit = {key: vehicle_fields.pop(key) for key in FIELDS if key in vehicle_fields}
    engine = resolve_engine(manufacturer, engine_code, internal_variant_key=internal_variant_key,
                            engine_pk=engine_pk, engine_uuid=engine_uuid, incoming_powertrain=incoming_powertrain)
    # Check separately: neither input dictionary can overwrite the other's conflict.
    if explicit:
        validate_engine_properties(engine, incoming_powertrain=explicit)
    vehicle_fields.setdefault('engine_name', engine.name)
    vehicle = VehicleDefinition(engine=engine, **vehicle_fields, **record_powertrain(engine))
    vehicle._validate_registry_engine()
    return vehicle
