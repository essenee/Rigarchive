"""Manufacturer-neutral equipment scope assessment; no persistence or exceptions.

Inputs are reviewed evidence findings, not keyword guesses or caller authority.
An eligible result preserves classification; it does not authorize canonical writes.
"""


def assess_equipment_scope(
    classification, *, brochure_listed, evidence_refs, applicability,
    brochure_reference=None, manufacturer_identifies_package=False, contents=None,
):
    """Assess ordinary ingestion scope without conflating options/accessories.

    Non-brochure optional equipment and exceptional reclassification require a
    separately authorized human workflow. This function cannot approve either.
    Accessories absent from the applicable brochure are categorically excluded.
    Vehicle identity/technical assertions are outside this equipment-only filter.
    """
    kinds = {"standard_equipment", "factory_package", "factory_option", "accessory"}
    if classification not in kinds:
        raise ValueError("Unknown equipment classification; review required.")
    if type(brochure_listed) is not bool:
        raise ValueError("Brochure inclusion must be an explicit evidence finding.")
    if not isinstance(evidence_refs, (list, tuple)) or not all(
        isinstance(ref, str) and ref.strip() for ref in evidence_refs
    ):
        raise ValueError("Document-qualified assertion references are required.")

    def result(disposition, reason):
        return {"classification": classification, "disposition": disposition,
                "reason": reason, "evidence_refs": list(evidence_refs),
                "brochure_reference": brochure_reference, "applicability": applicability}

    if classification == "accessory" and not brochure_listed:
        return result("excluded", "Accessory absent from applicable brochure; separate catalogues/releases cannot expand scope.")
    if not evidence_refs or not applicability:
        return result("review_required", "Missing source provenance or applicability.")
    if brochure_listed and not brochure_reference:
        return result("review_required", "Applicable brochure reference is required.")
    if classification != "standard_equipment" and not brochure_listed:
        return result("review_required", "Outside ordinary brochure scope; compelling documented human review and explicit authorization required. No automatic exception path.")
    if classification == "factory_package" and (
        manufacturer_identifies_package is not True or not contents
    ):
        return result("review_required", "Brochure must identify a package and document contents and applicability.")
    return result("eligible", "Within ordinary evidence-supported scope; classification is preserved, not canonical write authorization.")
