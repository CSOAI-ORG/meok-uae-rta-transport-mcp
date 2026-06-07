<!-- mcp-name: io.github.CSOAI-ORG/meok-uae-rta-transport-mcp -->
[![MCP Scorecard: 84/100](https://img.shields.io/badge/proofof.ai-84%2F100-5b21b6)](https://proofof.ai/scorecard/meok-uae-rta-transport-mcp.html)

# meok-uae-rta-transport-mcp

> UAE Federal Transport Authority + Emirate-level RTA compliance callable toolkit. Federal Decree-Law 38/2022 (driver hours) + mid-day heat ban + Tasjeel/Shamil inspection + GSO dangerous goods + Tawteen Emiratisation + GCC cross-border transit. By **MEOK AI Labs**.

## Why this exists

The UAE is MENA's logistics super-hub: Jebel Ali + Khalifa Port + Sharjah container terminals move ~70% of GCC re-export traffic, and ~AED 4 billion of road-freight tonnage crosses the seven Emirates daily. Yet operators (Aramex, DP World subsidiaries, Almajdouie, Ali & Sons, ~600 RTA-licensed haulage companies in Dubai alone) must comply with:

- **Federal** Decree-Law No. (38) of 2022 (Working Time, driver hours, rest)
- **MoHRE** Decree 401/2015 (mid-day heat ban Jun-Sep 12:30-15:00 outdoor)
- **Emirate** regulators × 7 (Dubai RTA, Abu Dhabi ITC, Sharjah RTA, Ajman, Fujairah, RAK, Umm Al Quwain)
- **Tasjeel / Shamil** annual vehicle inspection regime
- **GSO TR 2024:2017** dangerous goods + Dubai Civil Defence permit
- **Tawteen** Federal Decree-Law 33/2021 + Cabinet Res 18/2022 (Emiratisation)
- **GCC Customs Union** common manifest for UAE↔Oman/Saudi/Bahrain/Qatar/Kuwait

This MCP gives the Transport Manager + Emiratisation officer + Safety officer the callable toolkit to **prevent** each of those fine cascades.

This is the **MENA region equivalent** of [`meok-tacho-audit-mcp`](https://pypi.org/project/meok-tacho-audit-mcp/) (UK) and [`meok-fmcsa-hours-of-service-mcp`](https://pypi.org/project/meok-fmcsa-hours-of-service-mcp/) (US) — extends MEOK to MENA.

## Install

```bash
pip install meok-uae-rta-transport-mcp
```

## Claude Desktop config

```json
{
  "mcpServers": {
    "uae-rta": {
      "command": "meok-uae-rta-transport-mcp"
    }
  }
}
```

## Tools (7)

| Tool | Use case |
|------|----------|
| `check_uae_federal_drivers_hours` | Federal Decree-Law 38/2022 + heat ban (Jun-Sep 12:30-15:00) |
| `check_emirate_specific_rules` | Dubai RTA / Abu Dhabi ITC / Sharjah RTA / Ajman / Fujairah / RAK / UAQ routing |
| `check_uae_vehicle_inspection` | Tasjeel/Shamil annual inspection + Salik/DARB tolling tag |
| `check_adr_gcc_dangerous_goods` | GSO TR 2024 + Dubai Civil Defence DG permit |
| `check_emiratisation_quota` | Tawteen 2% transport sector + AED 8,000/missing-hire/month fine model |
| `prepare_rta_audit_pack` | RTA / Emirate-authority inspection-prep evidence checklist |
| `check_gcc_cross_border` | UAE↔Oman/Saudi/Bahrain/Qatar/Kuwait transit + GCC Common Manifest |

## Pricing

- **Free** — MIT self-host
- **Starter** — AED 199/mo
- **Pro** — AED 599/mo (multi-driver + multi-emirate)
- **Fleet** — AED 3,999/mo (50+ vehicles, GCC cross-border, audit-export)

[Subscribe Pro → AED 599/mo](https://www.csoai.org/checkout)

## Regulatory basis

- UAE Federal Decree-Law No. (38) of 2022 — Working Time + Rest
- UAE Federal Traffic Law No. (21) of 1995 (as amended Fed Law 12/2007)
- MoHRE Ministerial Decree No. 401 of 2015 — Mid-Day Work Ban
- Dubai RTA Public Transport Agency Regulations + RTA Code 2023
- Abu Dhabi ITC Commercial Vehicle Code
- Sharjah RTA Decree 12/2018
- GCC Standardisation Organisation Technical Regulation 2024:2017 — Dangerous Goods
- Federal Decree-Law No. (33) of 2021 + Cabinet Res (18) of 2022 — Tawteen / Emiratisation
- GCC Common Customs Law of 2003 — cross-border movement

## Licence

MIT — see `LICENSE`. The free Starter tier of the hosted SaaS provides additional regulatory lookups + automated weekly fleet audits.


<!-- GEO-FOOTER:v1 -->

---

### Part of the MEOK constellation

This MCP is one node in a connected ecosystem built by **MEOK AI LABS** around a single
sovereign AI core — governed agents with a hash-chained audit trail, mapped to the CSOAI
compliance charter.

- 🌐 The whole map: **<https://meok.ai/constellation>**
- 🛡️ AI governance & certification: **<https://councilof.ai>** · **<https://csoai.org>**
- ✅ Verify any signed report: **<https://meok.ai/verify>**
