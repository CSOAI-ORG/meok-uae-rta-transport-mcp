#!/usr/bin/env python3
"""
MEOK UAE Federal Transport Authority + Emirate RTA Compliance MCP
==================================================================

By MEOK AI Labs · https://haulage.app · MIT
<!-- mcp-name: io.github.CSOAI-ORG/meok-uae-rta-transport-mcp -->

WHAT THIS DOES
--------------
The UAE is the MENA region's logistics super-hub: ~70% of GCC re-export traffic
moves through Jebel Ali, Khalifa Port, and Sharjah container terminals; ~AED 4
billion of road-freight tonnage crosses the seven Emirates daily; and the
Federal Authority for Land & Maritime Transport (FALMT) plus seven Emirate-level
regulators (Dubai RTA, Abu Dhabi ITC, Sharjah RTA, Ajman, Fujairah, RAK, UAQ)
each enforce overlapping compliance regimes.

For an operator (Aramex, DP World subsidiaries, Almajdouie, Ali & Sons, plus
~600 RTA-licensed haulage companies in Dubai alone), a single fine cascade
can cost AED 100,000 - 500,000:

  - UAE Federal Decree-Law No. (38) of 2022 — Working Time (driver hours)
  - Heat-stress mid-day work ban Jun-Sep 12:30-15:00 (MoHRE Decree 401/2015)
  - Salik road-tolling violations + RTA inspection fines
  - Tasjeel / Shamil annual vehicle inspection lapse → vehicle impound
  - GCC Standardisation Organisation (GSO) dangerous goods rules
  - Tawteen (Emiratisation) 2% quota for transport — May 2024+ fines
  - GCC cross-border transit (UAE↔Oman/Saudi/Bahrain/Qatar/Kuwait) carnet/manifest

This MCP gives the Transport Manager + Emiratisation officer + Safety officer
the callable toolkit to PREVENT each of those fine cascades:

TOOLS (7)
---------
- check_uae_federal_drivers_hours(driver_log)        → Federal Decree-Law 38/2022 + heat ban
- check_emirate_specific_rules(emirate, operator)    → 7-Emirate regulator routing
- check_uae_vehicle_inspection(vrn, last_inspection) → Tasjeel/Shamil + Salik tag
- check_adr_gcc_dangerous_goods(consignment)         → GSO + Dubai Civil Defence
- check_emiratisation_quota(operator)                → Tawteen 2% for transport (May 2024+)
- prepare_rta_audit_pack(operator_data)              → RTA Dubai inspection prep
- check_gcc_cross_border(consignment, ...)           → UAE↔OMN/SAU/BHR/QAT/KWT transit

WHY YOU PAY
-----------
One avoided RTA inspection bust = AED 5,000 - 50,000 saved (fine + impound +
vehicle revenue loss). One avoided Tawteen non-compliance = AED 6,000/month per
missing Emirati hire. AED 199/mo Starter is a rounding error vs the risk.

PRICING
-------
Free MIT self-host · AED 199/mo Starter · AED 599/mo Pro · AED 3,999/mo Fleet.

REGULATORY BASIS
----------------
UAE Federal Decree-Law No. (38) of 2022 — Working Time + Rest
UAE Federal Traffic Law No. (21) of 1995 (as amended by Federal Law 12 of 2007)
MoHRE Ministerial Decree No. 401 of 2015 — Mid-Day Work Ban (Jun-Sep)
Dubai RTA Public Transport Agency regulations + RTA Code 2023
Abu Dhabi Integrated Transport Centre (ITC) commercial vehicle code
Sharjah Roads & Transport Authority Decree 12/2018
GCC Standardisation Organisation (GSO) Technical Regulations
GSO TR 2024:2017 — Dangerous Goods Transport
Federal Decree-Law No. (33) of 2021 / Tawteen (Emiratisation) Federal Decree
UAE Cabinet Resolution No. (18) of 2022 — Emiratisation Targets
GCC Customs Union Common Customs Law (2003) — cross-border movement
"""

from __future__ import annotations
import urllib.request as _meter_urlreq
import urllib.error as _meter_urlerr
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone, date, timedelta
from typing import Optional
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("meok-uae-rta-transport")
_HMAC_SECRET = os.environ.get("MEOK_HMAC_SECRET", "")


# ──────────────────────────────────────────────────────────────────────
# Regulatory tables — UAE Federal Decree-Law No. (38) of 2022
# ──────────────────────────────────────────────────────────────────────

# UAE Federal Working Time (private sector — applies to non-Free-Zone fleet drivers)
UAE_FEDERAL_HOS_LIMITS = {
    "max_daily_working_hr": 8,                # standard daily working hours
    "max_daily_working_hr_with_overtime": 10, # may extend by 2h with overtime
    "max_weekly_working_hr": 48,              # 6 days × 8h standard ceiling
    "max_overtime_per_day_hr": 2,
    "max_continuous_driving_hr": 5,           # mandatory break after 5h
    "mandatory_break_min": 30,
    "min_daily_rest_hr": 11,                  # 11 consecutive hours of rest in 24h
    "min_weekly_rest_hr": 24,                 # 1 full day off per week
    "ramadan_max_daily_working_hr": 6,        # Ramadan reduction (Muslim employees, all sectors)
}

# Heat-stress mid-day work ban — MoHRE Decree 401/2015
HEAT_BAN_RULES = {
    "ban_months": ["June", "July", "August", "September"],
    "ban_start_time_local": "12:30",
    "ban_end_time_local": "15:00",
    "applies_to": "Outdoor work — including loading, unloading, refuelling, "
                  "yard manoeuvres. In-cab moving driving is permitted; "
                  "driver MUST not perform outdoor duties during ban window.",
    "fine_per_worker_aed": 5000,              # MoHRE fine per worker per breach
    "fine_max_per_inspection_aed": 50000,
    "regulation": "MoHRE Ministerial Decree No. 401 of 2015",
}

# Emirate-specific transport regulators (lookup keyed by ISO-aligned emirate code)
EMIRATE_REGULATORS = {
    "dubai": {
        "regulator": "Dubai Roads & Transport Authority (RTA)",
        "regulator_short": "Dubai RTA",
        "operator_licence": "RTA Commercial Vehicle Licence",
        "key_codes": ["RTA Code 2023", "Public Transport Agency regulations"],
        "tolling": "Salik (RFID gantry)",
        "salik_required": True,
        "inspection_centre_brand": "Tasjeel (RTA-operated)",
        "key_rules": [
            "Heavy goods vehicles >3.5t banned from Sheikh Zayed Rd 6:30-09:00 / 17:00-20:00",
            "Mandatory GPS fleet-management for >5 vehicle operators",
            "Driver Permit (PSV / HGV) annual renewal",
        ],
        "fine_register": "RTA Public Service Bus / HGV fine schedule",
    },
    "abu_dhabi": {
        "regulator": "Abu Dhabi Integrated Transport Centre (ITC)",
        "regulator_short": "AD ITC",
        "operator_licence": "Abu Dhabi Commercial Vehicle Operating Licence",
        "key_codes": ["ITC Commercial Vehicle Code", "ITC Public Transport Code"],
        "tolling": "DARB (RFID gantry — operational from 2021)",
        "salik_required": False,             # different gantry system
        "inspection_centre_brand": "Shamil / ADNOC inspection centres",
        "key_rules": [
            "GCAA (General Civil Aviation Authority) airport-zone restrictions",
            "ADNOC permit required for petrochemical-zone hauls",
            "Vehicles >5t restricted from Corniche peak hours",
        ],
        "fine_register": "ITC fine schedule",
    },
    "sharjah": {
        "regulator": "Sharjah Roads & Transport Authority (SRTA)",
        "regulator_short": "Sharjah RTA",
        "operator_licence": "Sharjah Commercial Transport Licence",
        "key_codes": ["Sharjah RTA Decree 12/2018"],
        "tolling": None,
        "salik_required": True,              # cross-Dubai movements still need Salik
        "inspection_centre_brand": "Tasjeel",
        "key_rules": [
            "HGV ban from Al Ittihad Rd 7:00-9:00 / 18:00-20:00",
            "Mandatory livery for commercial vehicles registered SHJ",
        ],
        "fine_register": "Sharjah RTA fine schedule",
    },
    "ajman": {
        "regulator": "Ajman Transport Authority",
        "regulator_short": "Ajman TA",
        "operator_licence": "Ajman Commercial Transport Permit",
        "key_codes": ["Ajman Transport Authority bylaws"],
        "tolling": None,
        "salik_required": True,
        "inspection_centre_brand": "Tasjeel",
        "key_rules": [
            "Smaller fleet — defers many rules to UAE Federal Traffic Law 21/1995",
        ],
        "fine_register": "Ajman Police fine schedule (transport)",
    },
    "fujairah": {
        "regulator": "Fujairah Municipality Transport Section",
        "regulator_short": "Fujairah Transport",
        "operator_licence": "Fujairah Commercial Transport Permit",
        "key_codes": ["Fujairah Municipality Transport Regulations"],
        "tolling": None,
        "salik_required": True,
        "inspection_centre_brand": "Tasjeel / Fujairah Inspection Centre",
        "key_rules": [
            "Strategic east-coast bunkering / port-of-Fujairah dangerous goods rules",
            "Maritime-adjacent permits via FOIZ (Fujairah Oil Industry Zone)",
        ],
        "fine_register": "Fujairah Police fine schedule",
    },
    "ras_al_khaimah": {
        "regulator": "Ras Al Khaimah Transport Authority",
        "regulator_short": "RAK TA",
        "operator_licence": "RAK Commercial Transport Permit",
        "key_codes": ["RAK Transport Authority bylaws"],
        "tolling": None,
        "salik_required": True,
        "inspection_centre_brand": "Tasjeel",
        "key_rules": [
            "Quarry / cement industry haul permits (RAK is regional aggregates hub)",
        ],
        "fine_register": "RAK Police fine schedule",
    },
    "umm_al_quwain": {
        "regulator": "Umm Al Quwain Transport Section",
        "regulator_short": "UAQ Transport",
        "operator_licence": "UAQ Commercial Transport Permit",
        "key_codes": ["UAQ Transport bylaws"],
        "tolling": None,
        "salik_required": True,
        "inspection_centre_brand": "Tasjeel",
        "key_rules": [
            "Smaller fleet — defers many rules to UAE Federal Traffic Law 21/1995",
        ],
        "fine_register": "UAQ Police fine schedule",
    },
}

# UAE vehicle inspection regime (Tasjeel / Shamil)
INSPECTION_REGIME = {
    "operator_brand_dubai_north": "Tasjeel (RTA-owned operator)",
    "operator_brand_abu_dhabi": "Shamil + ADNOC partners",
    "frequency_commercial_vehicle": "annual (every 12 months from registration)",
    "frequency_passenger_taxi": "every 6 months",
    "salik_tag_required_dubai": True,
    "darb_tag_required_abu_dhabi": True,
    "passing_validity_days": 365,
    "fine_for_lapsed_inspection_aed": 500,
    "vehicle_impound_after_days_overdue": 30,
}

# GCC Standardisation Organisation (GSO) Dangerous Goods
DANGEROUS_GOODS_RULES = {
    "primary_standard": "GSO TR 2024:2017 — Dangerous Goods Transport",
    "adr_alignment": "GSO TR follows UN ADR Class 1-9 framework",
    "ud_dubai_civil_defence_permit": True,
    "ud_classes": {
        "1": "Explosives",
        "2": "Gases (compressed/liquefied/dissolved)",
        "3": "Flammable liquids",
        "4": "Flammable solids / spontaneous combustion / dangerous when wet",
        "5": "Oxidising substances / organic peroxides",
        "6": "Toxic / infectious substances",
        "7": "Radioactive material",
        "8": "Corrosive substances",
        "9": "Miscellaneous dangerous substances",
    },
    "driver_training_required": "GSO ADR-aligned 24h initial + 8h refresher every 2yr",
    "vehicle_marking": "Orange placards with UN number + hazard class",
    "fine_no_dcd_permit_aed": 10000,
    "fine_untrained_driver_aed": 5000,
    "fine_no_placards_aed": 2000,
}

# Tawteen (Emiratisation) — Federal Decree-Law 33/2021 + Cabinet Res 18/2022
TAWTEEN_RULES = {
    "applies_from": "2022-07-01",
    "target_quota_pct_2024": 6,                  # cumulative for 50+ employee firms in private sector
    "target_quota_pct_transport_may_2024_plus": 2,  # baseline transport-sector quota (firms 20-49 staff)
    "increment_per_year_pct": 1,                 # annual increment to 10% by 2026
    "min_emirati_per_50_employees_aed_fine": 96000,  # AED 8000 × 12 months per missing hire
    "monthly_fine_per_missing_hire_aed": 8000,   # raised from 7000 May 2024
    "regulation": "Federal Decree-Law (33) of 2021 + Cabinet Res (18) of 2022; "
                  "Cabinet Resolution amending fines May 2024",
    "applies_to_transport_company_threshold_employees": 20,
}

# GCC Customs Union — cross-border transit
GCC_BORDER_RULES = {
    "common_customs_law": "GCC Common Customs Law of 2003",
    "transit_carnet_required": True,
    "carnet_format": "GCC Common Manifest (TIR-equivalent inside GCC)",
    "passport_minimum_validity_months": 6,
    "vehicle_3rd_party_insurance_gcc_required": True,
    "border_posts": {
        "uae_oman": ["Al Madam / Hatta", "Khatm Al Shikla", "Hili", "Wajaja"],
        "uae_saudi": ["Ghuwaifat / Al Batha"],
        "qatar_currently_open": True,        # post-2021 Al-Ula reconciliation
        "bahrain_via": "King Fahd Causeway (transit via Saudi)",
        "kuwait_via": "transit via Saudi Arabia",
    },
    "embargoed_routes": [],                   # post-2021 GCC normalisation
    "qatar_blockade_lifted": "2021-01-05",
    "dangerous_goods_cross_border_pre_clearance": "GSO ADR + destination country permit",
}

# UAE Federal Traffic Law No. (21) of 1995 — key driver fines
FEDERAL_TRAFFIC_FINES_AED = {
    "driving_without_valid_licence": 5000,
    "driving_without_insurance": 500,
    "exceeding_hours_of_work": 5000,
    "failure_to_carry_inspection_certificate": 500,
    "transporting_dangerous_goods_without_permit": 10000,
    "exceeding_load_limit": 3000,
    "overloading_passengers_commercial": 3000,
    "use_of_phone_while_driving": 800,
    "no_seatbelt_driver": 400,
}

# Infringement weights for the federal-hours tool (severity scoring)
UAE_HOS_INFRINGEMENT_WEIGHTS = {
    "exceeded_8h_daily_working": 5,
    "exceeded_10h_with_overtime": 8,
    "exceeded_48h_weekly": 8,
    "exceeded_5h_continuous_driving": 4,
    "missed_30min_break": 3,
    "insufficient_11h_daily_rest": 6,
    "insufficient_24h_weekly_rest": 6,
    "ramadan_exceeded_6h_muslim": 7,
    "heat_ban_violation_jun_sep_midday": 10,
}


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _sign(payload: dict) -> str:
    if not _HMAC_SECRET:
        return "unsigned-no-key-configured"
    return hmac.new(
        _HMAC_SECRET.encode(),
        json.dumps(payload, sort_keys=True, default=str).encode(),
        hashlib.sha256,
    ).hexdigest()


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _attestation(payload: dict) -> dict:
    return {**payload, "ts": _ts(), "sig": _sign(payload),
            "issuer": "meok-uae-rta-transport-mcp", "version": "1.0.0"}


def _normalise_emirate(e: str) -> str:
    if not e:
        return ""
    return (e or "").lower().strip().replace(" ", "_").replace("-", "_")


def _month_to_name(m: int) -> str:
    return ["January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"][m - 1]


def _time_in_heat_ban_window(t: str) -> bool:
    """Return True if HH:MM is in 12:30 - 15:00 inclusive of start, exclusive of end."""
    if not t or ":" not in t:
        return False
    try:
        hh, mm = [int(x) for x in t.split(":")[:2]]
        minutes = hh * 60 + mm
        return (12 * 60 + 30) <= minutes < (15 * 60)
    except Exception:
        return False


# ──────────────────────────────────────────────────────────────────────
# Tools
# ──────────────────────────────────────────────────────────────────────


def _server_meter_check(api_key: str = "") -> dict:
    """Calls the live /verify endpoint for server-side metering. Fail-open."""
    try:
        data = json.dumps({"api_key": api_key, "tool": ""}).encode()
        req = _meter_urlreq.Request(_METER_URL, data=data,
            headers={"Content-Type": "application/json"}, method="POST")
        with _meter_urlreq.urlopen(req, timeout=2.5) as r:
            d = json.loads(r.read())
            if isinstance(d, dict) and "allowed" in d:
                return d
    except Exception:
        pass
    return {"allowed": True, "tier": "anonymous", "remaining": 200, "upgrade_url": "https://meok.ai/pricing"}


_METER_URL = "https://proofof.ai/verify"


@mcp.tool()
def check_uae_federal_drivers_hours(
    driver_name: str = "",
    daily_segments: Optional[list] = None,
    week_starting: str = "",
    is_muslim_in_ramadan: bool = False,
    heat_ban_outdoor_segments: Optional[list] = None,
) -> dict:
    """Audit a UAE-based commercial driver against UAE Federal Decree-Law No. (38)
    of 2022 (Working Time) + MoHRE mid-day heat-ban Decree 401/2015.

    Args:
      daily_segments: list of dicts per day, like
        {"date": "2026-06-18", "driving_hr": 9, "working_hr": 11,
         "longest_continuous_drive_hr": 6, "break_min": 20,
         "daily_rest_hr": 10, "weekly_rest_hr": 24, "month": 6}
      is_muslim_in_ramadan: if True, applies the 6h Ramadan working ceiling
      heat_ban_outdoor_segments: list of dicts of outdoor activity in ban months,
        like {"date": "2026-07-15", "start_time_local": "13:00",
              "end_time_local": "14:00", "activity": "loading"}

    Returns infringement list + severity total + heat-ban breaches.
    """
    daily_segments = daily_segments or []
    heat_ban_outdoor_segments = heat_ban_outdoor_segments or []
    infringements = []

    weekly_working = sum(d.get("working_hr", d.get("driving_hr", 0)) for d in daily_segments)
    if weekly_working > UAE_FEDERAL_HOS_LIMITS["max_weekly_working_hr"]:
        infringements.append({
            "code": "exceeded_48h_weekly",
            "actual_hr": round(weekly_working, 2),
            "limit_hr": UAE_FEDERAL_HOS_LIMITS["max_weekly_working_hr"],
            "severity": UAE_HOS_INFRINGEMENT_WEIGHTS["exceeded_48h_weekly"],
        })

    for d in daily_segments:
        working_hr = d.get("working_hr", d.get("driving_hr", 0))
        longest_drive = d.get("longest_continuous_drive_hr", 0)
        break_min = d.get("break_min", 30)
        daily_rest = d.get("daily_rest_hr", 24)
        weekly_rest = d.get("weekly_rest_hr", 24)

        # Standard 8h ceiling (without overtime declared)
        if working_hr > UAE_FEDERAL_HOS_LIMITS["max_daily_working_hr_with_overtime"]:
            infringements.append({
                "code": "exceeded_10h_with_overtime", "date": d.get("date"),
                "actual_hr": working_hr,
                "limit_hr": UAE_FEDERAL_HOS_LIMITS["max_daily_working_hr_with_overtime"],
                "severity": UAE_HOS_INFRINGEMENT_WEIGHTS["exceeded_10h_with_overtime"],
            })
        elif working_hr > UAE_FEDERAL_HOS_LIMITS["max_daily_working_hr"]:
            infringements.append({
                "code": "exceeded_8h_daily_working", "date": d.get("date"),
                "actual_hr": working_hr,
                "limit_hr": UAE_FEDERAL_HOS_LIMITS["max_daily_working_hr"],
                "severity": UAE_HOS_INFRINGEMENT_WEIGHTS["exceeded_8h_daily_working"],
            })

        # 5h continuous driving — mandatory break
        if longest_drive > UAE_FEDERAL_HOS_LIMITS["max_continuous_driving_hr"]:
            infringements.append({
                "code": "exceeded_5h_continuous_driving", "date": d.get("date"),
                "actual_hr": longest_drive,
                "limit_hr": UAE_FEDERAL_HOS_LIMITS["max_continuous_driving_hr"],
                "severity": UAE_HOS_INFRINGEMENT_WEIGHTS["exceeded_5h_continuous_driving"],
            })

        # 30-minute break after 5h continuous driving
        if longest_drive >= UAE_FEDERAL_HOS_LIMITS["max_continuous_driving_hr"] and \
                break_min < UAE_FEDERAL_HOS_LIMITS["mandatory_break_min"]:
            infringements.append({
                "code": "missed_30min_break", "date": d.get("date"),
                "actual_break_min": break_min,
                "severity": UAE_HOS_INFRINGEMENT_WEIGHTS["missed_30min_break"],
            })

        # 11h daily rest
        if daily_rest < UAE_FEDERAL_HOS_LIMITS["min_daily_rest_hr"]:
            infringements.append({
                "code": "insufficient_11h_daily_rest", "date": d.get("date"),
                "actual_hr": daily_rest,
                "limit_hr": UAE_FEDERAL_HOS_LIMITS["min_daily_rest_hr"],
                "severity": UAE_HOS_INFRINGEMENT_WEIGHTS["insufficient_11h_daily_rest"],
            })

        # 24h weekly rest
        if weekly_rest < UAE_FEDERAL_HOS_LIMITS["min_weekly_rest_hr"]:
            infringements.append({
                "code": "insufficient_24h_weekly_rest", "date": d.get("date"),
                "actual_hr": weekly_rest,
                "limit_hr": UAE_FEDERAL_HOS_LIMITS["min_weekly_rest_hr"],
                "severity": UAE_HOS_INFRINGEMENT_WEIGHTS["insufficient_24h_weekly_rest"],
            })

        # Ramadan ceiling — reduced 6h for Muslim employees (all sectors)
        if is_muslim_in_ramadan and working_hr > UAE_FEDERAL_HOS_LIMITS["ramadan_max_daily_working_hr"]:
            infringements.append({
                "code": "ramadan_exceeded_6h_muslim", "date": d.get("date"),
                "actual_hr": working_hr,
                "limit_hr": UAE_FEDERAL_HOS_LIMITS["ramadan_max_daily_working_hr"],
                "severity": UAE_HOS_INFRINGEMENT_WEIGHTS["ramadan_exceeded_6h_muslim"],
            })

    # Heat-ban breaches (Jun-Sep, outdoor activity in 12:30-15:00 window)
    heat_breaches = []
    for seg in heat_ban_outdoor_segments:
        seg_month_name = ""
        try:
            seg_month_name = _month_to_name(int((seg.get("date", "0000-00-00") or "0000-00-00").split("-")[1]))
        except Exception:
            pass
        if seg_month_name in HEAT_BAN_RULES["ban_months"]:
            if _time_in_heat_ban_window(seg.get("start_time_local", "")) or \
                    _time_in_heat_ban_window(seg.get("end_time_local", "")):
                heat_breaches.append({
                    "code": "heat_ban_violation_jun_sep_midday",
                    "date": seg.get("date"),
                    "activity": seg.get("activity"),
                    "start_time_local": seg.get("start_time_local"),
                    "end_time_local": seg.get("end_time_local"),
                    "severity": UAE_HOS_INFRINGEMENT_WEIGHTS["heat_ban_violation_jun_sep_midday"],
                    "fine_aed_per_worker": HEAT_BAN_RULES["fine_per_worker_aed"],
                })

    infringements.extend(heat_breaches)

    payload = {
        "tool": "check_uae_federal_drivers_hours",
        "driver_name": driver_name,
        "week_starting": week_starting,
        "weekly_working_hr": round(weekly_working, 2),
        "weekly_limit_hr": UAE_FEDERAL_HOS_LIMITS["max_weekly_working_hr"],
        "is_muslim_in_ramadan": is_muslim_in_ramadan,
        "infringement_count": len(infringements),
        "infringements": infringements,
        "severity_total": sum(i.get("severity", 0) for i in infringements),
        "heat_ban_breach_count": len(heat_breaches),
        "heat_ban_rules": HEAT_BAN_RULES,
        "regulation": "UAE Federal Decree-Law No. (38) of 2022 — Working Time + "
                      "MoHRE Ministerial Decree 401/2015 (mid-day heat ban)",
    }
    return _attestation(payload)


@mcp.tool()
def check_emirate_specific_rules(
    emirate: str = "",
    operator_name: str = "",
    fleet_size: int = 0,
    operates_dangerous_goods: bool = False,
    crosses_dubai: bool = False,
) -> dict:
    """Return the Emirate-level regulator + operator-licence + key rules for the
    requested emirate. Useful for routing an operator to the right authority.

    Args:
      emirate: one of 'dubai', 'abu_dhabi', 'sharjah', 'ajman', 'fujairah',
               'ras_al_khaimah', 'umm_al_quwain' (case-insensitive, also
               accepts 'Abu Dhabi', 'Ras Al Khaimah', etc.).
      crosses_dubai: if True, will append the Dubai Salik requirement even if
                     home emirate already has its own tolling system.
    """
    key = _normalise_emirate(emirate)
    aliases = {
        "ad": "abu_dhabi", "auh": "abu_dhabi",
        "dxb": "dubai",
        "shj": "sharjah",
        "ajm": "ajman",
        "fuj": "fujairah",
        "rak": "ras_al_khaimah",
        "uaq": "umm_al_quwain",
    }
    key = aliases.get(key, key)

    reg = EMIRATE_REGULATORS.get(key)
    if not reg:
        return _attestation({
            "tool": "check_emirate_specific_rules",
            "emirate_requested": emirate,
            "status": "UNKNOWN_EMIRATE",
            "valid_emirates": sorted(EMIRATE_REGULATORS.keys()),
            "advisory": "Pass one of: dubai, abu_dhabi, sharjah, ajman, "
                        "fujairah, ras_al_khaimah, umm_al_quwain.",
        })

    obligations = list(reg["key_rules"])
    tolling_obligations = []
    if reg.get("salik_required"):
        tolling_obligations.append("Salik tag required for Dubai gantries")
    if reg.get("tolling") == "DARB (RFID gantry — operational from 2021)":
        tolling_obligations.append("DARB tag required for Abu Dhabi gantries")
    if crosses_dubai and not reg.get("salik_required"):
        tolling_obligations.append(
            "Salik tag REQUIRED — operations cross Dubai despite being home-registered elsewhere")

    if operates_dangerous_goods:
        obligations.append("Dubai Civil Defence permit + GSO TR 2024 ADR-aligned routing")
    if fleet_size >= 5 and key == "dubai":
        obligations.append("Mandatory RTA-approved GPS fleet-management (fleet ≥5)")

    return _attestation({
        "tool": "check_emirate_specific_rules",
        "emirate": key,
        "operator_name": operator_name,
        "fleet_size": fleet_size,
        "regulator": reg["regulator"],
        "regulator_short": reg["regulator_short"],
        "operator_licence_name": reg["operator_licence"],
        "applicable_codes": reg["key_codes"],
        "tolling_system": reg["tolling"],
        "tolling_obligations": tolling_obligations,
        "inspection_centre_brand": reg["inspection_centre_brand"],
        "key_obligations": obligations,
        "fine_register": reg["fine_register"],
        "regulation": "UAE Federal Traffic Law 21/1995 + Emirate-level transport authority "
                      "rules — see emirate-specific code.",
    })


@mcp.tool()
def check_uae_vehicle_inspection(
    vrn: str = "",
    last_inspection_date: str = "",
    registration_emirate: str = "dubai",
    is_commercial_vehicle: bool = True,
    is_passenger_taxi: bool = False,
    salik_tag_present: bool = True,
    darb_tag_present: bool = False,
    inspection_certificate_carried: bool = True,
) -> dict:
    """Verify a UAE commercial vehicle's Tasjeel/Shamil annual inspection status
    and Salik / DARB tolling-tag fit.

    Args:
      last_inspection_date: 'YYYY-MM-DD' format
      registration_emirate: 'dubai', 'abu_dhabi', etc.
      is_passenger_taxi: 6-month re-inspection cadence overrides 12-month
    """
    today = date.today()
    last_dt = None
    days_since = None
    if last_inspection_date:
        try:
            last_dt = datetime.strptime(last_inspection_date, "%Y-%m-%d").date()
            days_since = (today - last_dt).days
        except Exception:
            pass

    if is_passenger_taxi:
        validity_days = 182  # ~6 months
    else:
        validity_days = INSPECTION_REGIME["passing_validity_days"]

    overdue_days = 0
    status = "UNKNOWN"
    if days_since is None:
        status = "NO_INSPECTION_DATE_PROVIDED"
    elif days_since <= validity_days:
        status = "VALID"
    else:
        overdue_days = days_since - validity_days
        if overdue_days >= INSPECTION_REGIME["vehicle_impound_after_days_overdue"]:
            status = "OVERDUE_IMPOUND_RISK"
        else:
            status = "OVERDUE"

    em = _normalise_emirate(registration_emirate)
    em_reg = EMIRATE_REGULATORS.get(em, EMIRATE_REGULATORS["dubai"])
    tolling_issues = []
    if em == "dubai" or em_reg.get("salik_required"):
        if not salik_tag_present:
            tolling_issues.append("Salik tag missing — required for Dubai gantries")
    if em == "abu_dhabi":
        if not darb_tag_present:
            tolling_issues.append("DARB tag missing — required for Abu Dhabi gantries")

    fine_advisory = []
    if status in ("OVERDUE", "OVERDUE_IMPOUND_RISK"):
        fine_advisory.append(
            f"Lapsed-inspection fine: AED {INSPECTION_REGIME['fine_for_lapsed_inspection_aed']}")
    if status == "OVERDUE_IMPOUND_RISK":
        fine_advisory.append("Vehicle is liable to be impounded — book Tasjeel slot immediately")
    if not inspection_certificate_carried:
        fine_advisory.append(
            f"Failure to carry inspection certificate: AED "
            f"{FEDERAL_TRAFFIC_FINES_AED['failure_to_carry_inspection_certificate']}")
    if tolling_issues:
        fine_advisory.append(
            "Tolling: untagged commercial vehicle attracts gantry-violation fines per pass")

    return _attestation({
        "tool": "check_uae_vehicle_inspection",
        "vrn": vrn,
        "registration_emirate": em,
        "last_inspection_date": last_inspection_date,
        "days_since_inspection": days_since,
        "validity_days": validity_days,
        "overdue_days": overdue_days,
        "status": status,
        "is_passenger_taxi": is_passenger_taxi,
        "inspection_centre_brand": em_reg["inspection_centre_brand"],
        "salik_tag_present": salik_tag_present,
        "darb_tag_present": darb_tag_present,
        "inspection_certificate_carried": inspection_certificate_carried,
        "tolling_issues": tolling_issues,
        "fine_advisory": fine_advisory,
        "regulation": "UAE Federal Traffic Law 21/1995 + Tasjeel/Shamil annual "
                      "inspection regime; Salik (Dubai) / DARB (Abu Dhabi) tolling.",
    })


@mcp.tool()
def check_adr_gcc_dangerous_goods(
    consignment_ref: str = "",
    un_number: str = "",
    hazard_class: str = "",
    quantity_kg: float = 0,
    route_emirate_chain: Optional[list] = None,
    dubai_civil_defence_permit_held: bool = False,
    driver_adr_trained: bool = False,
    driver_adr_refresher_within_2yr: bool = False,
    placards_displayed: bool = False,
    vehicle_emergency_kit: bool = False,
) -> dict:
    """Audit a dangerous goods consignment against GSO TR 2024:2017 (GCC ADR
    alignment) + Dubai Civil Defence rules.

    Args:
      hazard_class: one of '1'-'9' per UN ADR / GSO classification
      route_emirate_chain: ordered list of emirates traversed
    """
    route_emirate_chain = route_emirate_chain or []
    hazard_class = str(hazard_class).strip()
    class_label = DANGEROUS_GOODS_RULES["ud_classes"].get(
        hazard_class, "Unknown / non-classified")

    issues = []
    fines_exposure_aed = 0
    crosses_dubai = any(_normalise_emirate(e) == "dubai" for e in route_emirate_chain)

    if crosses_dubai and not dubai_civil_defence_permit_held:
        issues.append("Dubai Civil Defence permit NOT held — required for any DG transit in Dubai")
        fines_exposure_aed += DANGEROUS_GOODS_RULES["fine_no_dcd_permit_aed"]

    if not driver_adr_trained:
        issues.append("Driver lacks GSO ADR-aligned 24h initial training")
        fines_exposure_aed += DANGEROUS_GOODS_RULES["fine_untrained_driver_aed"]
    elif not driver_adr_refresher_within_2yr:
        issues.append("Driver ADR refresher (8h every 2 years) overdue")
        fines_exposure_aed += DANGEROUS_GOODS_RULES["fine_untrained_driver_aed"]

    if not placards_displayed:
        issues.append("Orange placards (UN number + class) not displayed on vehicle")
        fines_exposure_aed += DANGEROUS_GOODS_RULES["fine_no_placards_aed"]

    if not vehicle_emergency_kit:
        issues.append("Vehicle emergency kit (extinguishers, eye-wash, spill kit) missing")

    # Class-specific advisories
    advisories = []
    if hazard_class == "1":
        advisories.append("Class 1 Explosives — armed escort + UAE MoI permit required.")
    if hazard_class == "7":
        advisories.append("Class 7 Radioactive — FANR (Federal Authority for Nuclear Regulation) "
                          "consignment permit required.")
    if hazard_class == "2":
        advisories.append("Class 2 Gases — pressure-vessel certification + Dubai Civil Defence approval.")

    compliance_status = "COMPLIANT" if not issues else "NON_COMPLIANT"

    return _attestation({
        "tool": "check_adr_gcc_dangerous_goods",
        "consignment_ref": consignment_ref,
        "un_number": un_number,
        "hazard_class": hazard_class,
        "hazard_class_label": class_label,
        "quantity_kg": quantity_kg,
        "route_emirate_chain": [_normalise_emirate(e) for e in route_emirate_chain],
        "crosses_dubai": crosses_dubai,
        "issues": issues,
        "issue_count": len(issues),
        "advisories": advisories,
        "fines_exposure_aed": fines_exposure_aed,
        "compliance_status": compliance_status,
        "rules_reference": DANGEROUS_GOODS_RULES,
        "regulation": "GSO TR 2024:2017 (GCC Dangerous Goods Transport) + "
                      "Dubai Civil Defence Code + UAE Federal Traffic Law 21/1995.",
    })


@mcp.tool()
def check_emiratisation_quota(
    operator_name: str = "",
    total_employees: int = 0,
    emirati_employees: int = 0,
    is_transport_company: bool = True,
    is_free_zone_entity: bool = False,
    audit_period_year: int = 2026,
) -> dict:
    """Audit an operator against Tawteen Emiratisation quota (Federal Decree-Law
    33/2021 + Cabinet Resolution 18/2022 + May 2024 raised fines).

    Args:
      total_employees: total UAE-based payroll headcount
      emirati_employees: UAE-national employees on payroll
      is_free_zone_entity: free-zone entities generally exempt (e.g., JAFZA,
                           Abu Dhabi Global Market, DIFC)
      audit_period_year: target year for quota calculation
    """
    if is_free_zone_entity:
        return _attestation({
            "tool": "check_emiratisation_quota",
            "operator_name": operator_name,
            "is_free_zone_entity": True,
            "status": "EXEMPT_FREE_ZONE",
            "advisory": ("Free-zone entities are generally outside the Tawteen "
                         "mainland quota. Confirm with the specific free-zone authority "
                         "as some have voluntary targets."),
            "regulation": TAWTEEN_RULES["regulation"],
        })

    if total_employees < TAWTEEN_RULES["applies_to_transport_company_threshold_employees"]:
        return _attestation({
            "tool": "check_emiratisation_quota",
            "operator_name": operator_name,
            "total_employees": total_employees,
            "status": "BELOW_QUOTA_THRESHOLD",
            "advisory": (f"Company has {total_employees} employees, below the "
                         f"{TAWTEEN_RULES['applies_to_transport_company_threshold_employees']}"
                         f"-employee threshold for transport-sector Tawteen quota."),
            "regulation": TAWTEEN_RULES["regulation"],
        })

    # 2% baseline transport-sector quota May 2024+, increment of +1pp per year
    # to reach ~6% by 2026 for ≥50 staff firms
    if total_employees >= 50:
        # Federal headline: 2% per year cumulative since 2022 → 6% by 2024,
        # incremented to 7% in 2025 and 8% in 2026 per Cabinet Resolution
        quota_pct = TAWTEEN_RULES["target_quota_pct_2024"] + max(0, (audit_period_year - 2024))
    else:
        quota_pct = TAWTEEN_RULES["target_quota_pct_transport_may_2024_plus"]

    required_emirati = int(((quota_pct / 100.0) * total_employees) + 0.999)  # ceiling
    deficit = max(0, required_emirati - emirati_employees)
    current_pct = (emirati_employees / total_employees * 100.0) if total_employees else 0

    if deficit == 0:
        status = "COMPLIANT"
        fine_annual_aed = 0
        advisory = f"Compliant: {emirati_employees}/{required_emirati} required (>= {quota_pct}%)."
    else:
        status = "NON_COMPLIANT"
        fine_annual_aed = deficit * TAWTEEN_RULES["monthly_fine_per_missing_hire_aed"] * 12
        advisory = (
            f"NON-COMPLIANT: short by {deficit} Emirati hire(s). "
            f"Monthly fine AED {TAWTEEN_RULES['monthly_fine_per_missing_hire_aed']:,} × "
            f"{deficit} = AED {deficit * TAWTEEN_RULES['monthly_fine_per_missing_hire_aed']:,}/month "
            f"(AED {fine_annual_aed:,}/year exposure)."
        )

    return _attestation({
        "tool": "check_emiratisation_quota",
        "operator_name": operator_name,
        "is_transport_company": is_transport_company,
        "audit_period_year": audit_period_year,
        "total_employees": total_employees,
        "emirati_employees": emirati_employees,
        "current_pct": round(current_pct, 2),
        "required_quota_pct": quota_pct,
        "required_emirati": required_emirati,
        "deficit": deficit,
        "status": status,
        "monthly_fine_per_missing_hire_aed": TAWTEEN_RULES["monthly_fine_per_missing_hire_aed"],
        "annual_fine_exposure_aed": fine_annual_aed,
        "advisory": advisory,
        "regulation": TAWTEEN_RULES["regulation"],
    })


@mcp.tool()
def prepare_rta_audit_pack(
    operator_name: str = "",
    rta_trade_licence_no: str = "",
    primary_emirate: str = "dubai",
    fleet_size: int = 0,
    months_to_inspection: int = 3,
    has_dangerous_goods_operations: bool = False,
) -> dict:
    """Produce the Dubai RTA (or other Emirate authority) commercial-fleet
    inspection-prep evidence pack.

    Args:
      primary_emirate: home regulator for the operator
      months_to_inspection: time remaining before scheduled inspection
    """
    em = _normalise_emirate(primary_emirate)
    em_reg = EMIRATE_REGULATORS.get(em, EMIRATE_REGULATORS["dubai"])

    evidence_checklist = [
        f"{em_reg['operator_licence']} (trade-licence no.) — current copy",
        "Mainland or free-zone establishment card + commercial trade licence",
        "Vehicle list — all VRNs + Tasjeel/Shamil last-inspection dates",
        "Driver register — UAE driving licence, PSV/HGV permit, work permit",
        "MoHRE labour-contract copies for each driver",
        "Driver UAE Federal Decree-Law 38/2022 hours-of-work logs (12 months back)",
        "Heat-ban (Jun-Sep) outdoor-work risk assessment + mid-day stand-down policy",
        "Tasjeel / Shamil annual inspection certificates (current)",
        "Salik / DARB tolling-tag register for each vehicle",
        "Third-party motor insurance certificates — all vehicles",
        "Vehicle GPS / fleet-management data export (RTA-approved provider)",
        "Defect-rectification log — DVIRs equivalent (per Federal Traffic Law)",
        "Accident register with insurance + Najm reports (3 years)",
        "Tawteen Emiratisation register + MoHRE quota report",
        "WPS (Wage Protection System) compliance evidence — driver wages paid on time",
    ]
    if has_dangerous_goods_operations:
        evidence_checklist.extend([
            "Dubai Civil Defence Dangerous Goods permit",
            "Driver GSO ADR training certificates (24h initial + 8h refresher)",
            "Vehicle DG fit-out — placards, kits, fire-extinguisher service log",
            "FANR / EAD (Environment Agency Abu Dhabi) consignment permits if applicable",
        ])

    automatic_failure_items = [
        "Operating a commercial vehicle without a valid UAE Federal Traffic licence",
        "Vehicle with lapsed Tasjeel/Shamil inspection certificate (impound exposure)",
        "Driver without a valid PSV/HGV permit for the vehicle category",
        "Heat-ban breach during Jun-Sep 12:30-15:00 outdoor activity",
        "Tawteen quota deficit with no MoHRE rectification plan filed",
        "WPS late wage payment >30 days (MoHRE labour-file freeze)",
        "Operating a fleet ≥5 vehicles without RTA-approved GPS (Dubai only)",
    ]

    readiness_status = "ON_TRACK"
    if months_to_inspection <= 1:
        readiness_status = "URGENT_LESS_THAN_30_DAYS"
    elif months_to_inspection <= 2:
        readiness_status = "TIGHT_BOOK_GAP_AUDIT"
    elif months_to_inspection >= 6:
        readiness_status = "EARLY_BUILD_PROGRAMME"

    return _attestation({
        "tool": "prepare_rta_audit_pack",
        "operator_name": operator_name,
        "rta_trade_licence_no": rta_trade_licence_no,
        "primary_emirate": em,
        "regulator": em_reg["regulator"],
        "fleet_size": fleet_size,
        "months_to_inspection": months_to_inspection,
        "readiness_status": readiness_status,
        "has_dangerous_goods_operations": has_dangerous_goods_operations,
        "evidence_checklist": evidence_checklist,
        "evidence_item_count": len(evidence_checklist),
        "automatic_failure_items": automatic_failure_items,
        "applicable_codes": em_reg["key_codes"],
        "fine_register": em_reg["fine_register"],
        "regulation": "UAE Federal Traffic Law 21/1995 + Emirate-level transport "
                      "authority codes + UAE Federal Decree-Law 38/2022 (Working Time).",
        "next_action": (
            "URGENT: less than 30 days — staff a one-week gap audit now."
            if readiness_status == "URGENT_LESS_THAN_30_DAYS" else
            ("Book a gap audit this week."
             if readiness_status == "TIGHT_BOOK_GAP_AUDIT" else
             "Phase the evidence build over the runway.")
        ),
    })


@mcp.tool()
def check_gcc_cross_border(
    consignment_ref: str = "",
    origin_emirate: str = "",
    destination_country: str = "",
    cargo_description: str = "",
    is_dangerous_goods: bool = False,
    driver_passport_valid_months: int = 12,
    gcc_third_party_insurance: bool = True,
    gcc_common_manifest_filed: bool = False,
    destination_country_permit_held: bool = False,
) -> dict:
    """Audit a GCC cross-border consignment leaving the UAE (or transiting
    via UAE) against the GCC Common Customs Law of 2003 + destination-country
    permits.

    Args:
      origin_emirate: e.g. 'dubai', 'sharjah'
      destination_country: 'oman', 'saudi_arabia', 'bahrain', 'qatar', 'kuwait'
    """
    dest = (destination_country or "").lower().replace(" ", "_").replace("-", "_")
    dest_aliases = {
        "ksa": "saudi_arabia", "saudi": "saudi_arabia", "sa": "saudi_arabia",
        "om": "oman", "omn": "oman",
        "bh": "bahrain", "bhr": "bahrain",
        "qa": "qatar", "qat": "qatar",
        "kw": "kuwait", "kwt": "kuwait",
    }
    dest = dest_aliases.get(dest, dest)

    valid_destinations = {"oman", "saudi_arabia", "bahrain", "qatar", "kuwait"}
    if dest not in valid_destinations:
        return _attestation({
            "tool": "check_gcc_cross_border",
            "consignment_ref": consignment_ref,
            "status": "UNKNOWN_DESTINATION",
            "valid_destinations": sorted(valid_destinations),
            "advisory": "Pass destination_country = oman | saudi_arabia | bahrain | qatar | kuwait.",
        })

    issues = []
    advisories = []

    if driver_passport_valid_months < GCC_BORDER_RULES["passport_minimum_validity_months"]:
        issues.append(
            f"Driver passport validity {driver_passport_valid_months}mo < "
            f"{GCC_BORDER_RULES['passport_minimum_validity_months']}mo minimum")

    if not gcc_third_party_insurance:
        issues.append("Vehicle missing GCC-valid third-party insurance — entry will be refused at border")

    if not gcc_common_manifest_filed:
        issues.append("GCC Common Manifest not filed — required for transit under "
                      "GCC Common Customs Law 2003")

    # Destination-specific
    if dest == "saudi_arabia":
        advisories.append("Saudi Customs requires Saudi-VAT TIN if commercial; "
                          "ZATCA e-invoicing recommended.")
        if not destination_country_permit_held:
            issues.append("Saudi commercial-haul permit (Awamer / TGA) not held")

    if dest == "qatar":
        advisories.append("Qatar route open since 2021 Al-Ula reconciliation; "
                          "Salwa border post operational.")

    if dest == "oman":
        advisories.append("Oman MoTC (Ministry of Transport & Communications) "
                          "permit + Oman-side third-party insurance highly recommended.")

    if dest in ("bahrain", "kuwait"):
        advisories.append("Transit via Saudi Arabia — Saudi transit permit may be required.")

    if is_dangerous_goods:
        advisories.append(GCC_BORDER_RULES["dangerous_goods_cross_border_pre_clearance"])
        if not destination_country_permit_held:
            issues.append("Destination-country dangerous-goods permit not held")

    # Border-post suggestion
    suggested_border = None
    if dest == "oman":
        suggested_border = GCC_BORDER_RULES["border_posts"]["uae_oman"]
    elif dest == "saudi_arabia":
        suggested_border = GCC_BORDER_RULES["border_posts"]["uae_saudi"]
    elif dest == "qatar":
        suggested_border = ["Via Saudi Arabia (Salwa)"]
    elif dest == "bahrain":
        suggested_border = ["Via Saudi Arabia (King Fahd Causeway)"]
    elif dest == "kuwait":
        suggested_border = ["Via Saudi Arabia"]

    status = "COMPLIANT" if not issues else "NON_COMPLIANT"

    return _attestation({
        "tool": "check_gcc_cross_border",
        "consignment_ref": consignment_ref,
        "origin_emirate": _normalise_emirate(origin_emirate),
        "destination_country": dest,
        "cargo_description": cargo_description,
        "is_dangerous_goods": is_dangerous_goods,
        "issues": issues,
        "issue_count": len(issues),
        "advisories": advisories,
        "status": status,
        "suggested_border_posts": suggested_border,
        "rules_reference": {
            "common_customs_law": GCC_BORDER_RULES["common_customs_law"],
            "transit_carnet_required": GCC_BORDER_RULES["transit_carnet_required"],
            "carnet_format": GCC_BORDER_RULES["carnet_format"],
            "qatar_blockade_lifted": GCC_BORDER_RULES["qatar_blockade_lifted"],
        },
        "regulation": "GCC Common Customs Law of 2003 + destination-country "
                      "transport-ministry permits.",
    })


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()


# ── MEOK monetization layer (Stripe upgrade · PAYG · pricing) ──────────
# Free tier is zero-config. Upgrade to Pro (unlimited) or pay-as-you-go per call.
import os as _meok_os
MEOK_STRIPE_UPGRADE = "https://buy.stripe.com/5kQ6oJ0xS3ce8sl7ew8k91j"  # Pro (unlimited)
MEOK_PAYG_KEY = _meok_os.environ.get("MEOK_PAYG_KEY", "")  # set to enable PAYG (x402 / ~GBP0.05 per call)
MEOK_PRICING = "https://meok.ai/pricing"


def meok_upsell(tier: str = "free") -> dict:
    """Monetization options for free-tier callers: Pro upgrade, PAYG, or pricing page."""
    if tier != "free":
        return {}
    return {"upgrade_url": MEOK_STRIPE_UPGRADE,
            "payg_enabled": bool(MEOK_PAYG_KEY),
            "pricing": MEOK_PRICING}
