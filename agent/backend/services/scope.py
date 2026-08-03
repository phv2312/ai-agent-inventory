from agent.backend.repos.protocols import ReferenceRepository


async def resolve_scope_reference_ids(
    reference_repo: ReferenceRepository,
    *,
    collection_ids: list[str],
    reference_ids: list[str],
    message: str,
) -> tuple[list[str], list[str]]:
    from agent.backend.services.mentions import parse_doc_names

    scope_ids: set[str] = set()
    warnings: list[str] = []

    if collection_ids:
        scope_ids.update(
            await reference_repo.list_completed_ids_for_collections(collection_ids)
        )
    if reference_ids:
        scope_ids.update(await reference_repo.list_completed_ids(reference_ids))

    doc_names = parse_doc_names(message)
    if doc_names:
        resolved = await reference_repo.resolve_doc_names(
            doc_names,
            collection_ids or None,
        )
        found = {r.doc_name for r in resolved}
        for name in doc_names:
            if name not in found:
                warnings.append(f"@mention doc_name not found or not indexed: {name}")
        scope_ids.update(r.id for r in resolved)

    return sorted(scope_ids), warnings
