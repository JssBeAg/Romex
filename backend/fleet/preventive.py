"""
When is each unit due for each preventive plan? It is worked out every time from the last
maintenance that fulfilled the plan on that unit, so there is nothing to keep up to date:

    next kilometer = km of that service + "every km" of the plan
    next date      = date of that service + "every days" of the plan

and it is compared with how many kilometers the unit has now and with today. The status:

    Vencido        a limit was reached or passed (km or days, whichever comes first)
    Próximo        less than 10% of the interval is left
    Al corriente   still far from the limits
    Sin historial  no maintenance has fulfilled the plan on this unit yet
"""

import datetime

from django.db.models import Max

from .models import Checklist, Maintenance, MaintenancePlan, Unit

OVERDUE = "vencido"
UPCOMING = "proximo"
NO_HISTORY = "sin_historial"
OK = "al_corriente"

STATUS_LABELS = {
    OVERDUE: "Vencido",
    UPCOMING: "Próximo",
    NO_HISTORY: "Sin historial",
    OK: "Al corriente",
}
# Most urgent first
RANK = {OVERDUE: 0, UPCOMING: 1, NO_HISTORY: 2, OK: 3}

WARNING_FRACTION = 0.10


def current_mileages(unit_ids=None):
    """
    {unit id: kilometers it has now}: the highest of the odometer saved in the unit, the
    last checklist and the last maintenance (the odometer only goes up).
    """
    units = Unit.objects.all() if unit_ids is None else Unit.objects.filter(pk__in=unit_ids)
    result = dict(units.values_list("pk", "mileage"))
    for model, field in ((Checklist, "recorded_mileage"), (Maintenance, "service_mileage")):
        rows = (
            model.objects.filter(unit_id__in=result)
            .order_by()
            .values("unit_id")
            .annotate(top=Max(field))
        )
        for row in rows:
            result[row["unit_id"]] = max(result[row["unit_id"]], row["top"])
    return result


def applies_to(plan, unit):
    return plan.unit_model_id is None or plan.unit_model_id == unit.unit_model_id


def due_for(plan, unit, last, mileage, today):
    """One row: how the unit stands for the plan. `last` is the last maintenance for it, or None."""
    row = {
        "unit": {"id": unit.pk, "label": f"{unit.economic_number}"},
        "plan": {
            "id": plan.pk,
            "name": plan.name,
            "every_km": plan.every_km,
            "every_days": plan.every_days,
        },
        "current_mileage": mileage,
        "last": None,
        "next_km": None,
        "remaining_km": None,
        "next_date": None,
        "remaining_days": None,
    }
    if last is None:
        row.update(status=NO_HISTORY, message="Aún no se ha registrado este servicio en la unidad.")
        return row

    row["last"] = {"id": last.pk, "date": last.date.isoformat(), "mileage": last.service_mileage}
    statuses, parts = [], []
    if plan.every_km:
        row["next_km"] = last.service_mileage + plan.every_km
        row["remaining_km"] = row["next_km"] - mileage
        left = row["remaining_km"]
        if left <= 0:
            statuses.append(OVERDUE)
            parts.append(f"Se pasó por {-left:,} km")
        else:
            statuses.append(UPCOMING if left <= plan.every_km * WARNING_FRACTION else OK)
            parts.append(f"Faltan {left:,} km")
    if plan.every_days:
        row["next_date"] = (last.date + datetime.timedelta(days=plan.every_days)).isoformat()
        row["remaining_days"] = (last.date + datetime.timedelta(days=plan.every_days) - today).days
        left = row["remaining_days"]
        if left <= 0:
            statuses.append(OVERDUE)
            parts.append(f"Se pasó por {-left} días" if left < 0 else "Vence hoy")
        else:
            statuses.append(UPCOMING if left <= plan.every_days * WARNING_FRACTION else OK)
            parts.append(f"Faltan {left} días")
    # The worst of the two limits decides
    row["status"] = min(statuses, key=lambda s: RANK[s])
    row["message"] = ". ".join(parts) + "."
    return row


def due_rows(unit_ids=None, plan_ids=None, today=None):
    """Every (unit, active plan that applies to it), most urgent first."""
    today = today or datetime.date.today()
    # (an inactive unit takes no more services)
    units = Unit.objects.filter(is_active=True).select_related("unit_model__brand").order_by("economic_number")
    if unit_ids is not None:
        units = units.filter(pk__in=unit_ids)
    units = list(units)
    plans = MaintenancePlan.objects.filter(is_active=True)
    if plan_ids is not None:
        plans = plans.filter(pk__in=plan_ids)
    mileages = current_mileages([u.pk for u in units])

    rows = []
    for plan in plans:
        # The last maintenance of each unit for this plan (newest first, the first one of each unit)
        last_by_unit = {}
        for m in Maintenance.objects.filter(plan=plan, unit__in=units).order_by("-date", "-id"):
            last_by_unit.setdefault(m.unit_id, m)
        for unit in units:
            if applies_to(plan, unit):
                rows.append(due_for(plan, unit, last_by_unit.get(unit.pk), mileages[unit.pk], today))

    def urgency(row):
        # Within a status: the one closest to its limit first
        remaining = [r for r in (row["remaining_km"], row["remaining_days"]) if r is not None]
        return (RANK[row["status"]], min(remaining) if remaining else 0, row["unit"]["label"])

    rows.sort(key=urgency)
    for row in rows:
        row["status_label"] = STATUS_LABELS[row["status"]]
    return rows


def summary(rows):
    counts = {OVERDUE: 0, UPCOMING: 0, NO_HISTORY: 0, OK: 0}
    for row in rows:
        counts[row["status"]] += 1
    return {
        "overdue": counts[OVERDUE],
        "upcoming": counts[UPCOMING],
        "no_history": counts[NO_HISTORY],
        "ok": counts[OK],
    }
