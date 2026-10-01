"""Point-of-sale application helpers."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, SIGNAL_SALES_UPDATED
from .domain.container import SalePack
from .domain.models import CommunifarmState
from .domain.sale import (
    DEFAULT_CURRENCY,
    Sale,
    SaleCleanupEvent,
    SaleLineItem,
    assert_can_sell_pack,
    build_cleanup_checklist,
    require_confirm,
    validate_label,
    validate_money,
    validate_payment_method,
    validate_sale_pack_mass,
)
from .domain.validation import ValidationError
from .storage.batch_repository import BatchRepository
from .storage.container_repository import ContainerRepository
from .storage.sale_repository import SaleRepository

_LOGGER = logging.getLogger(__name__)


def _bucket(hass: HomeAssistant, entry_id: str) -> dict:
    return hass.data[DOMAIN][entry_id]


async def async_record_sale(
    hass: HomeAssistant,
    entry_id: str,
    *,
    venue_label: str,
    buyer_label: str,
    payment_method: str,
    line_amount: float,
    confirm: bool,
    sale_pack_id: str | None = None,
    harvest_id: str | None = None,
    mass_g: float | None = None,
    product_label: str | None = None,
    size_label: str | None = None,
    notes: str | None = None,
    currency: str = DEFAULT_CURRENCY,
) -> Sale:
    """Record a sale after payment — prepacked pack or weigh-at-sale."""
    try:
        require_confirm(confirm)
        venue = validate_label(venue_label, field="venue_label")
        buyer = validate_label(buyer_label, field="buyer_label")
        method = validate_payment_method(payment_method)
        amount = validate_money(line_amount, field="line_amount")
    except ValidationError as err:
        raise HomeAssistantError(str(err)) from err

    bucket = _bucket(hass, entry_id)
    state: CommunifarmState = bucket["state"]
    batch_repo: BatchRepository = bucket["batch_repository"]
    container_repo: ContainerRepository = bucket["container_repository"]
    sale_repo: SaleRepository = bucket["sale_repository"]

    now = datetime.now(tz=UTC).isoformat()
    pack: SalePack | None = None
    harvest = None

    try:
        if sale_pack_id:
            pack = await container_repo.async_get_sale_pack(sale_pack_id)
            if pack is None:
                raise ValidationError(f"sale_pack {sale_pack_id} not found")
            assert_can_sell_pack(status=pack.status, pack_id=pack.id)
            harvest = await batch_repo.async_get_harvest(pack.harvest_id)
            if harvest is None:
                raise ValidationError(
                    f"harvest {pack.harvest_id} not found for sale_pack"
                )
            sold_mass = pack.mass_g
        else:
            if not harvest_id:
                harvests = await batch_repo.async_list_harvests(state.batch.id)
                if not harvests:
                    raise ValidationError(
                        "no harvest_id and active batch has no harvest_events — "
                        "harvest first or pass harvest_id"
                    )
                harvest = harvests[-1]
            else:
                harvest = await batch_repo.async_get_harvest(harvest_id)
                if harvest is None:
                    raise ValidationError(f"harvest {harvest_id} not found")
            if mass_g is None:
                mass_g = float(bucket.get("sale_mass_g", 100.0) or 100.0)
            sold_mass = validate_sale_pack_mass(mass_g)
            pack = SalePack(
                harvest_id=harvest.id,
                mass_g=sold_mass,
                size_label=size_label,
                zone_id=None,
                status="open",
                created_at=now,
                notes="weigh-at-sale",
            )
            await container_repo.async_insert_sale_pack(pack)
    except ValidationError as err:
        raise HomeAssistantError(str(err)) from err

    assert pack is not None and harvest is not None
    label = validate_label(
        product_label
        or size_label
        or pack.size_label
        or f"harvest flush {harvest.flush_number}",
        field="product_label",
    )
    unit_price = round(amount / sold_mass, 4) if sold_mass else None

    sale = Sale(
        venue_label=venue,
        buyer_label=buyer,
        payment_method=method,
        currency=currency or DEFAULT_CURRENCY,
        total_amount=amount,
        sold_at=now,
        created_at=now,
        notes=notes,
    )
    line = SaleLineItem(
        sale_id=sale.id,
        sale_pack_id=pack.id,
        batch_id=harvest.batch_id,
        harvest_id=harvest.id,
        product_label=label,
        mass_g=sold_mass,
        unit_price=unit_price,
        line_amount=amount,
        created_at=now,
    )
    await sale_repo.async_insert_sale(sale, [line])
    await container_repo.async_mark_sale_pack_sold(pack.id, sale.id)

    bucket["sale_venue_label"] = venue
    bucket["sale_buyer_label"] = buyer
    bucket["last_sale_id"] = sale.id

    async_dispatcher_send(hass, SIGNAL_SALES_UPDATED, entry_id)
    _LOGGER.info(
        "Sale %s venue=%s buyer=%s pay=%s total=%s pack=%s batch=%s",
        sale.id,
        venue,
        buyer,
        method,
        amount,
        pack.id,
        harvest.batch_id,
    )
    return sale


async def async_record_sale_cleanup(
    hass: HomeAssistant,
    entry_id: str,
    *,
    sale_id: str | None = None,
    sale_day: str | None = None,
    cleaned: bool = True,
    put_away: bool = True,
    ready_next: bool = True,
    notes: str | None = None,
) -> SaleCleanupEvent:
    """Append a post-sale clean / put-away event."""
    bucket = _bucket(hass, entry_id)
    sale_repo: SaleRepository = bucket["sale_repository"]
    now = datetime.now(tz=UTC)
    now_iso = now.isoformat()
    resolved_sale = sale_id or bucket.get("last_sale_id")
    day = sale_day or now.date().isoformat()
    checklist = build_cleanup_checklist(
        cleaned=cleaned, put_away=put_away, ready_next=ready_next
    )
    event = SaleCleanupEvent(
        sale_id=resolved_sale,
        sale_day=day,
        checklist_json=json.dumps(checklist, sort_keys=True),
        notes=notes,
        recorded_at=now_iso,
        created_at=now_iso,
    )
    await sale_repo.async_insert_cleanup(event)
    async_dispatcher_send(hass, SIGNAL_SALES_UPDATED, entry_id)
    _LOGGER.info("Sale cleanup %s sale_id=%s day=%s", event.id, resolved_sale, day)
    return event


async def async_sales_summary(hass: HomeAssistant, entry_id: str) -> dict:
    """Build operator-facing sales snapshot for the POS sensor."""
    bucket = _bucket(hass, entry_id)
    sale_repo: SaleRepository = bucket["sale_repository"]
    container_repo: ContainerRepository = bucket["container_repository"]
    sales = await sale_repo.async_list_sales(limit=10)
    open_packs = await container_repo.async_list_open_sale_packs()
    cleanups = await sale_repo.async_list_cleanups(limit=5)
    last = sales[0] if sales else None
    lines: list[SaleLineItem] = []
    if last:
        lines = await sale_repo.async_list_lines_for_sale(last.id)
    return {
        "sale_count": len(sales),
        "open_pack_count": len(open_packs),
        "last_sale": last.to_dict() if last else None,
        "last_lines": [line.to_dict() for line in lines],
        "recent_sales": [s.to_dict() for s in sales],
        "open_packs": [p.to_dict() for p in open_packs[:10]],
        "recent_cleanups": [c.to_dict() for c in cleanups],
        "progress_text": sales_summary_markdown(
            sales=sales,
            open_packs=open_packs,
            last_lines=lines,
            cleanups=cleanups,
        ),
    }


def sales_summary_markdown(
    *,
    sales: list[Sale],
    open_packs: list[SalePack],
    last_lines: list[SaleLineItem],
    cleanups: list[SaleCleanupEvent],
) -> str:
    if not sales:
        open_n = len(open_packs)
        return (
            f"_No sales yet._ Open packs ready: **{open_n}**.\n\n"
            "Set venue/buyer/payment/mass/amount, then **Confirm sale**."
        )
    last = sales[0]
    line_bits = ", ".join(
        f"{line.product_label} {line.mass_g:g}g (${line.line_amount:g})"
        for line in last_lines
    ) or "—"
    cleanup_note = (
        f"Last cleanup: `{cleanups[0].sale_day}`"
        if cleanups
        else "No cleanup recorded yet."
    )
    return (
        f"**Last sale** `{last.id}`\n"
        f"| Field | Value |\n"
        f"| --- | --- |\n"
        f"| Venue | {last.venue_label} |\n"
        f"| Buyer | {last.buyer_label} |\n"
        f"| Pay | {last.payment_method} |\n"
        f"| Total | ${last.total_amount:g} {last.currency} |\n"
        f"| Lines | {line_bits} |\n\n"
        f"Recent sales: **{len(sales)}** · Open packs: **{len(open_packs)}**\n\n"
        f"{cleanup_note}"
    )
