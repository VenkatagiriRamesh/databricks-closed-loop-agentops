"""Promotion by alias move. Prompt changes go live inside the copilot's prompt TTL, no redeploy."""
from __future__ import annotations

from collections.abc import Callable

from agentops.release.state import IllegalTransition, ReleaseStore


class NoPreviousVersion(RuntimeError):
    pass


def _alias_version(get: Callable, name: str, alias: str) -> str | None:
    try:
        v = get(name, alias)
    except Exception:  # noqa: BLE001 - alias not set yet
        return None
    return str(v.version) if v is not None else None


def promote(store: ReleaseStore, cid: str, client, actor: str,
            deploy_fn: Callable[[str], None] | None = None) -> None:
    cand = store.get(cid)
    if cand['state'] != 'awaiting_approval':
        raise IllegalTransition(f'cannot promote from {cand["state"]}')
    if not store.is_approved(cid):
        raise IllegalTransition('no approval on record')
    name, payload = cand['model_name'], cand['payload']
    with store.promotion_lock(name):
        if cand['change_kind'] == 'prompt':
            prev = _alias_version(client.get_prompt_version_by_alias, name, 'production')
            if prev is not None:
                client.set_prompt_alias(name, 'previous_production', int(prev))
            client.set_prompt_alias(name, 'production', int(payload['version']))
        else:
            prev = _alias_version(client.get_model_version_by_alias, name, 'champion')
            if prev is not None:
                client.set_registered_model_alias(name, 'previous_champion', prev)
            client.set_registered_model_alias(name, 'champion', str(payload['version']))
            if deploy_fn is not None:
                deploy_fn(name)
        store.update_payload(cid, previous_version=prev)
        store.transition(cid, 'promoted', actor, f'promoted version {payload["version"]}')


def rollback(store: ReleaseStore, cid: str, client, actor: str,
             deploy_fn: Callable[[str], None] | None = None) -> None:
    cand = store.get(cid)
    if cand['state'] != 'promoted':
        raise IllegalTransition(f'cannot roll back from {cand["state"]}')
    prev = cand['payload'].get('previous_version')
    if prev is None:
        raise NoPreviousVersion(f'candidate {cid} had no previous version to restore')
    name = cand['model_name']
    with store.promotion_lock(name):
        if cand['change_kind'] == 'prompt':
            client.set_prompt_alias(name, 'production', int(prev))
        else:
            client.set_registered_model_alias(name, 'champion', str(prev))
            if deploy_fn is not None:
                deploy_fn(name)
        store.transition(cid, 'rolled_back', actor, f'restored version {prev}')
