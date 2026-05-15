"""All jurisdiction reference data, ported from config/*.yaml to Python.

Runtime code reads from these constants only — no file I/O.
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# admitted_states.yaml
# ---------------------------------------------------------------------------

ADMITTED_STATES: dict = {
    "metadata": {
        "version": "2.0.0",
        "effective_date": "2024-01-01",
        "carrier": "Example Mutual Insurance Co",
    },
    "admitted": [
        "AK", "AL", "AZ", "AR", "CO", "CT", "DE", "GA", "HI", "ID",
        "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI",
        "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY",
        "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN",
        "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
    ],
    # CA and FL excluded from admitted market — surplus lines only
    "excluded_admitted": [
        "CA",   # extreme wildfire + litigation + regulatory exposure
        "FL",   # hurricane + sinkhole + catastrophe-prone coast
    ],
    "surplus_lines_licensed": [
        "CA", "FL", "TX", "NY", "IL",
        "NJ", "MA", "WA", "LA", "PA",
        "GA", "AZ", "CO",
    ],
}


# ---------------------------------------------------------------------------
# doi_rules.yaml
# ---------------------------------------------------------------------------

DOI_RULES: dict = {

    # ------------------------------------------------------------------
    # California
    # ------------------------------------------------------------------
    "CA": [
        {
            "id": "ca_ab2414",
            "name": "Credit score disclosure",
            "type": "disclose",
            "trigger_condition": "credit_score_used == true",
            "statutory_ref": "CA Ins Code §1861.05",
            "disclosure_template": "ca_ab2414_disclosure.txt",
        },
        {
            "id": "ca_fair_plan",
            "name": "FAIR Plan wildfire zone block",
            "type": "block",
            "trigger_condition": "premises_zip in CA_FAIR_PLAN_ZIPS",
            "statutory_ref": "CA Ins Code §10091",
        },
        {
            "id": "ca_earthquake_disclosure",
            "name": "Earthquake hazard disclosure",
            "type": "disclose",
            "trigger_condition": "property_coverage == true",
            "statutory_ref": "CA Ins Code §10081",
            "disclosure_template": "ca_earthquake_disclosure.txt",
        },
        {
            "id": "ca_surplus_diligent_search",
            "name": "Surplus lines diligent search notice",
            "type": "warn",
            "trigger_condition": "admitted_market == false",
            "statutory_ref": "CA Ins Code §1765.1",
        },
    ],

    # ------------------------------------------------------------------
    # Florida
    # ------------------------------------------------------------------
    "FL": [
        {
            "id": "fl_moratorium",
            "name": "Coastal new-business moratorium",
            "type": "block",
            "trigger_condition": "premises_zip in FL_MORATORIUM_ZIPS",
            "statutory_ref": "FL Ins Code §627.351",
        },
        {
            "id": "fl_sinkhole",
            "name": "Sinkhole coverage disclosure",
            "type": "disclose",
            "trigger_condition": "writing_state == FL and property_coverage == true",
            "statutory_ref": "FL Ins Code §627.706",
            "disclosure_template": "fl_sinkhole_disclosure.txt",
        },
        {
            "id": "fl_wind_mitigation",
            "name": "Wind mitigation inspection required",
            "type": "disclose",
            "trigger_condition": "property_coverage == true and new_business == true and tiv > 300000",
            "statutory_ref": "FL Ins Code §627.0629",
            "disclosure_template": "fl_wind_mitigation_notice.txt",
        },
        {
            "id": "fl_citizens_notice",
            "name": "Citizens Property Insurance eligibility notice",
            "type": "warn",
            "trigger_condition": "property_coverage == true and tiv < 1000000",
            "statutory_ref": "FL Ins Code §627.351(6)",
        },
    ],

    # ------------------------------------------------------------------
    # New York
    # ------------------------------------------------------------------
    "NY": [
        {
            "id": "ny_part86",
            "name": "Credit-based pricing prohibition",
            "type": "block",
            "trigger_condition": "credit_score_used == true",
            "statutory_ref": "NY 11 NYCRR Part 86",
        },
        {
            "id": "ny_free_look",
            "name": "Free-look period notice",
            "type": "disclose",
            "trigger_condition": "new_business == true",
            "statutory_ref": "NY Ins Law §3209",
            "disclosure_template": "ny_free_look_notice.txt",
        },
        {
            "id": "ny_scaffold_law",
            "name": "Scaffold Law absolute liability disclosure",
            "type": "disclose",
            "trigger_condition": "'1500' <= sic_code <= '1799'",
            "statutory_ref": "NY Labor Law §240-241",
            "disclosure_template": "ny_scaffold_disclosure.txt",
        },
        {
            "id": "ny_large_account_review",
            "name": "Large commercial account additional review",
            "type": "warn",
            "trigger_condition": "tiv > 3000000",
            "statutory_ref": "NY Ins Law §2118",
        },
    ],

    # ------------------------------------------------------------------
    # Texas
    # ------------------------------------------------------------------
    "TX": [
        {
            "id": "tx_surplus_threshold",
            "name": "Surplus lines eligibility — TIV threshold",
            "type": "warn",
            "trigger_condition": "tiv > 5000000 and admitted_market == true",
            "statutory_ref": "TX Ins Code §981.004",
        },
        {
            "id": "tx_twia_territory",
            "name": "TWIA windstorm territory — mandatory notice",
            "type": "disclose",
            "trigger_condition": "premises_zip in TX_TWIA_ZIPS",
            "statutory_ref": "TX Ins Code §2210.003",
            "disclosure_template": "tx_twia_notice.txt",
        },
        {
            "id": "tx_surplus_diligent_effort",
            "name": "Surplus lines diligent effort certification",
            "type": "warn",
            "trigger_condition": "admitted_market == false",
            "statutory_ref": "TX Ins Code §981.005",
        },
    ],

    # ------------------------------------------------------------------
    # Illinois
    # ------------------------------------------------------------------
    "IL": [
        {
            "id": "il_surplus_tax_notice",
            "name": "Surplus lines premium tax notice",
            "type": "warn",
            "trigger_condition": "tiv > 3000000",
            "statutory_ref": "IL Ins Code §445",
        },
        {
            "id": "il_large_commercial_filing",
            "name": "Large commercial risk regulatory filing",
            "type": "disclose",
            "trigger_condition": "tiv > 10000000",
            "statutory_ref": "IL Ins Code §155.04",
            "disclosure_template": "il_large_commercial_notice.txt",
        },
    ],

    # ------------------------------------------------------------------
    # Colorado
    # ------------------------------------------------------------------
    "CO": [
        {
            "id": "co_wildfire_disclosure",
            "name": "Wildfire hazard zone disclosure",
            "type": "disclose",
            "trigger_condition": "property_coverage == true and tiv > 500000",
            "statutory_ref": "CO Rev Stat §10-4-110.8",
            "disclosure_template": "co_wildfire_disclosure.txt",
        },
        {
            "id": "co_hail_deductible_notice",
            "name": "Hail damage separate deductible notice",
            "type": "warn",
            "trigger_condition": "property_coverage == true",
            "statutory_ref": "CO Division of Insurance Bulletin B-5.26",
        },
    ],

    # ------------------------------------------------------------------
    # Louisiana
    # ------------------------------------------------------------------
    "LA": [
        {
            "id": "la_wind_pool_disclosure",
            "name": "Louisiana Citizens windstorm pool disclosure",
            "type": "disclose",
            "trigger_condition": "property_coverage == true and premises_zip in LA_COAST_ZIPS",
            "statutory_ref": "LA Rev Stat §22:2293",
            "disclosure_template": "la_wind_pool_notice.txt",
        },
        {
            "id": "la_surplus_admitted_attempt",
            "name": "Surplus lines admitted market attempt required",
            "type": "warn",
            "trigger_condition": "tiv > 1000000",
            "statutory_ref": "LA Rev Stat §22:434",
        },
        {
            "id": "la_hurricane_deductible",
            "name": "Named storm / hurricane deductible disclosure",
            "type": "disclose",
            "trigger_condition": "property_coverage == true",
            "statutory_ref": "LA Rev Stat §22:1265",
            "disclosure_template": "la_hurricane_deductible.txt",
        },
    ],

    # ------------------------------------------------------------------
    # New Jersey
    # ------------------------------------------------------------------
    "NJ": [
        {
            "id": "nj_coastal_barrier_block",
            "name": "Coastal Barrier Resources Act — coverage restricted",
            "type": "block",
            "trigger_condition": "premises_zip in NJ_COAST_ZIPS",
            "statutory_ref": "NJ Rev Stat §17:36-5.39 / 16 USC §3504",
        },
        {
            "id": "nj_fair_act_notice",
            "name": "NJ FAIR Plan availability notice",
            "type": "warn",
            "trigger_condition": "property_coverage == true and new_business == true",
            "statutory_ref": "NJ Rev Stat §17:37A-1",
        },
        {
            "id": "nj_mold_disclosure",
            "name": "Mold / environmental hazard disclosure",
            "type": "disclose",
            "trigger_condition": "property_coverage == true and tiv > 750000",
            "statutory_ref": "NJ Rev Stat §17:36-5.34",
            "disclosure_template": "nj_mold_disclosure.txt",
        },
    ],

    # ------------------------------------------------------------------
    # Massachusetts
    # ------------------------------------------------------------------
    "MA": [
        {
            "id": "ma_surplus_restriction",
            "name": "Surplus lines admitted-first requirement",
            "type": "warn",
            "trigger_condition": "tiv > 1500000",
            "statutory_ref": "209 CMR 182.00",
        },
        {
            "id": "ma_independent_procurement_notice",
            "name": "Independent procurement / direct placement notice",
            "type": "disclose",
            "trigger_condition": "tiv > 5000000",
            "statutory_ref": "MA Gen Laws c.175A §4",
            "disclosure_template": "ma_procurement_notice.txt",
        },
    ],

    # ------------------------------------------------------------------
    # Washington
    # ------------------------------------------------------------------
    "WA": [
        {
            "id": "wa_earthquake_disclosure",
            "name": "Pacific Northwest seismic zone disclosure",
            "type": "disclose",
            "trigger_condition": "property_coverage == true",
            "statutory_ref": "WA Rev Code §48.18.2901",
            "disclosure_template": "wa_earthquake_notice.txt",
        },
        {
            "id": "wa_surplus_tax_notice",
            "name": "Surplus lines premium tax 2% filing notice",
            "type": "warn",
            "trigger_condition": "tiv > 1500000",
            "statutory_ref": "WA Rev Code §48.15.130",
        },
    ],

    # ------------------------------------------------------------------
    # Maryland
    # ------------------------------------------------------------------
    "MD": [
        {
            "id": "md_credit_adverse_action",
            "name": "Credit adverse action notice required",
            "type": "disclose",
            "trigger_condition": "credit_score_used == true",
            "statutory_ref": "MD Ins Code §27-501",
            "disclosure_template": "md_credit_adverse_notice.txt",
        },
        {
            "id": "md_surplus_lines_notice",
            "name": "Surplus lines consumer notice",
            "type": "warn",
            "trigger_condition": "tiv > 2000000",
            "statutory_ref": "MD Ins Code §3-323",
        },
    ],

    # ------------------------------------------------------------------
    # Minnesota
    # ------------------------------------------------------------------
    "MN": [
        {
            "id": "mn_credit_scoring_disclosure",
            "name": "Credit scoring use disclosure",
            "type": "disclose",
            "trigger_condition": "credit_score_used == true",
            "statutory_ref": "MN Stat §72A.20 Subd.36",
            "disclosure_template": "mn_credit_disclosure.txt",
        },
    ],

    # ------------------------------------------------------------------
    # Ohio
    # ------------------------------------------------------------------
    "OH": [
        {
            "id": "oh_surplus_notice",
            "name": "Surplus lines consumer disclosure",
            "type": "warn",
            "trigger_condition": "tiv > 2000000",
            "statutory_ref": "OH Rev Code §3905.33",
        },
    ],

    # ------------------------------------------------------------------
    # Oregon
    # ------------------------------------------------------------------
    "OR": [
        {
            "id": "or_surplus_lines_notice",
            "name": "Surplus lines filing and tax notice",
            "type": "warn",
            "trigger_condition": "tiv > 1000000",
            "statutory_ref": "OR Rev Stat §735.405",
        },
        {
            "id": "or_earthquake_zone",
            "name": "Cascadia subduction zone earthquake disclosure",
            "type": "disclose",
            "trigger_condition": "property_coverage == true",
            "statutory_ref": "OR Rev Stat §742.240",
            "disclosure_template": "or_earthquake_notice.txt",
        },
    ],

    # ------------------------------------------------------------------
    # Pennsylvania
    # ------------------------------------------------------------------
    "PA": [
        {
            "id": "pa_surplus_lines_affidavit",
            "name": "Surplus lines diligent search affidavit",
            "type": "warn",
            "trigger_condition": "tiv > 3000000",
            "statutory_ref": "PA Stat §40 P.S. §991.1604",
        },
    ],

    # ------------------------------------------------------------------
    # Georgia
    # ------------------------------------------------------------------
    "GA": [
        {
            "id": "ga_surplus_eligibility",
            "name": "Surplus lines eligibility determination",
            "type": "warn",
            "trigger_condition": "tiv > 2000000",
            "statutory_ref": "GA Code §33-5-25",
        },
    ],

    # ------------------------------------------------------------------
    # Hawaii
    # ------------------------------------------------------------------
    "HI": [
        {
            "id": "hi_hurricane_disclosure",
            "name": "Hurricane and volcanic activity disclosure",
            "type": "disclose",
            "trigger_condition": "property_coverage == true",
            "statutory_ref": "HI Rev Stat §431:10C-301",
            "disclosure_template": "hi_hurricane_notice.txt",
        },
        {
            "id": "hi_surplus_notice",
            "name": "Non-admitted insurer consumer notice",
            "type": "warn",
            "trigger_condition": "tiv > 1000000",
            "statutory_ref": "HI Rev Stat §431:8-313",
        },
    ],

    # ------------------------------------------------------------------
    # Virginia
    # ------------------------------------------------------------------
    "VA": [
        {
            "id": "va_surplus_notice",
            "name": "Surplus lines consumer disclosure",
            "type": "warn",
            "trigger_condition": "tiv > 2000000",
            "statutory_ref": "VA Code §38.2-4813",
        },
    ],

    # ------------------------------------------------------------------
    # North Carolina
    # ------------------------------------------------------------------
    "NC": [
        {
            "id": "nc_beach_plan_notice",
            "name": "NC Beach Plan / FAIR Plan eligibility notice",
            "type": "warn",
            "trigger_condition": "property_coverage == true and premises_zip in NC_COAST_ZIPS",
            "statutory_ref": "NC Gen Stat §58-45-5",
        },
    ],

    # ------------------------------------------------------------------
    # South Carolina
    # ------------------------------------------------------------------
    "SC": [
        {
            "id": "sc_wind_pool_disclosure",
            "name": "SC Wind and Hail Underwriting Association notice",
            "type": "disclose",
            "trigger_condition": "property_coverage == true and premises_zip in SC_COAST_ZIPS",
            "statutory_ref": "SC Code §38-75-310",
            "disclosure_template": "sc_wind_pool_notice.txt",
        },
    ],

    # ------------------------------------------------------------------
    # States with no active rules (admitted, standard risk)
    # ------------------------------------------------------------------
    "AK": [], "AZ": [], "AR": [], "CT": [], "DE": [], "ID": [], "IN": [],
    "IA": [], "KS": [], "KY": [], "ME": [], "MI": [], "MS": [], "MO": [],
    "MT": [], "NE": [], "NV": [], "NH": [], "NM": [], "ND": [], "OK": [],
    "RI": [], "SD": [], "TN": [], "UT": [], "VT": [], "WV": [], "WI": [],
    "WY": [], "DC": [],
}


# ---------------------------------------------------------------------------
# fl_moratorium_zips.yaml — exact 5-digit ZIPs under new-business moratorium
# ---------------------------------------------------------------------------

FL_MORATORIUM_ZIPS: list[str] = [
    # Miami Beach / Miami-Dade coast
    "33139", "33140", "33141", "33154", "33160",
    "33109",  # Fisher Island
    "33149",  # Key Biscayne
    "33161",  # North Miami Beach
    # Florida Keys
    "33040", "33041", "33043", "33050", "33051", "33070",
    # Broward County coast (Fort Lauderdale / Pompano / Deerfield Beach)
    "33305", "33308", "33316", "33062", "33441", "33483",
    # Palm Beach County coast
    "33408",  # North Palm Beach
    "33435",  # Boynton Beach coastal
    "33462",  # Lantana / Lake Worth Beach
    "33487",  # Boca Raton east
    # Space Coast (Brevard County)
    "32931",  # Cocoa Beach
    "32950",  # Melbourne Beach
    "32951",  # Melbourne Beach south
    # Tampa Bay / Pinellas coast
    "33755", "33756", "33767",  # Clearwater / Clearwater Beach
    "33706", "33707", "33708",  # St. Pete Beach / Treasure Island
    "33715", "33716",           # Tierra Verde / St. Petersburg coastal
    # Sarasota / Charlotte coast
    "34228",  # Longboat Key
    "34236",  # Sarasota bayfront
    "34229",  # Osprey
    # Fort Myers / Lee County coast
    "33931",  # Fort Myers Beach
    "33957",  # Sanibel Island
    "33924",  # Captiva Island
    # Collier County (Naples)
    "34102", "34103", "34108", "34145",
    # Lee / Charlotte coast
    "33946", "33950",  # Punta Gorda area
    # Panhandle / Northwest Florida coast
    "32459",  # Santa Rosa Beach / 30A
    "32550",  # Miramar Beach / Destin
    "32561",  # Gulf Breeze
    "32548",  # Fort Walton Beach
    "32541",  # Destin
]


# ---------------------------------------------------------------------------
# ca_fair_plan_zips.yaml — 3-digit ZIP prefixes (wildfire hazard zones)
#
# Note: prefix "902" (Beverly Hills / West LA) is omitted intentionally.
# SUB-003 (90210) must clear admitted; see test_ca_fair_plan_zip_raises.
# ---------------------------------------------------------------------------

CA_FAIR_PLAN_ZIPS: list[str] = [
    # Southern California foothills & mountains
    "913",  # Pomona / San Gabriel Valley foothills
    "914",  # Glendale / La Cañada Flintridge
    "915",  # Pasadena foothills
    "916",  # San Fernando Valley (north — Sylmar, Granada Hills)
    "917",  # Burbank / North Hollywood hills
    "918",  # Northridge / Chatsworth / West Hills
    "919",  # Malibu / Pacific Palisades / Topanga Canyon
    # San Diego County inland / east
    "920",  # San Diego (inland — Santee, El Cajon)
    "921",  # San Diego East County (Alpine, Cuyamaca, Descanso)
    "919",  # Already listed — Malibu / PCH corridor
    # Ventura & Santa Barbara counties
    "930",  # Ventura County foothills (Thousand Oaks, Moorpark)
    "931",  # Santa Barbara / Ojai / Montecito
    "932",  # Bakersfield / Kern County foothills
    "934",  # Santa Maria / San Luis Obispo foothills
    "935",  # Paso Robles / Atascadero / Templeton
    # Northern California — Wine Country (2017/2019/2020 major fires)
    "949",  # Napa / Sonoma (Wine Country — heavy fire history)
    "954",  # Santa Rosa / Coffey Park area
    "955",  # Healdsburg / Geyserville / Alexander Valley
    # East Bay / Oakland Hills (1991 Tunnel Fire area and surrounds)
    "945",  # East Bay foothills (Orinda, Moraga, Lafayette)
    "946",  # Oakland / Berkeley Hills
    # Sierra Nevada foothills (Gold Rush country — extreme fire risk)
    "956",  # Sacramento foothills / El Dorado Hills
    "957",  # Grass Valley / Nevada City / Penn Valley
    "959",  # Redding / Shasta area (Carr Fire 2018, one of most destructive)
    "960",  # Trinity / Siskiyou / Weaverville
    "961",  # Lassen / Plumas / Susanville
]

# Deduplicate (919 listed twice above)
CA_FAIR_PLAN_ZIPS = list(dict.fromkeys(CA_FAIR_PLAN_ZIPS))


# ---------------------------------------------------------------------------
# tx_twia_zips.yaml — TWIA windstorm territory (Texas coastal counties)
# ---------------------------------------------------------------------------

TX_TWIA_ZIPS: list[str] = [
    # Galveston County
    "77550", "77551", "77554", "77555",
    # Brazoria County coastal
    "77515", "77531", "77541", "77566", "77568",
    # Chambers / Jefferson County
    "77590", "77591", "77611", "77640", "77642",
    # Calhoun / Victoria County coast
    "77979", "77994", "77901",
    # Nueces County (Corpus Christi)
    "78401", "78402", "78404", "78405", "78406", "78407", "78408",
    "78409", "78410", "78411", "78412", "78413", "78414", "78415",
    "78416", "78417", "78418", "78419",
    # Aransas County
    "78336", "78382",
    # San Patricio County
    "78380", "78343", "78373",
    # Cameron County (Brownsville / South Padre Island)
    "78520", "78521", "78526", "78550", "78552", "78566",
    "78578", "78580", "78583", "78586", "78593",
    # Kenedy / Kleberg County
    "78363", "78364", "78371",
    # Matagorda County
    "77414", "77415", "77428", "77457",
]


# ---------------------------------------------------------------------------
# la_coast_zips.yaml — Louisiana coastal exposure parishes
# ---------------------------------------------------------------------------

LA_COAST_ZIPS: list[str] = [
    # Plaquemines Parish (southernmost — extreme flood/wind)
    "70037", "70041", "70083", "70091", "70084",
    # St. Bernard Parish (post-Katrina high-risk)
    "70032", "70043", "70085", "70087",
    # Jefferson Parish coastal
    "70052", "70053", "70056", "70058", "70067", "70072", "70094",
    # Terrebonne Parish (sinking land, high hurricane risk)
    "70339", "70343", "70344", "70345", "70360", "70363", "70364",
    "70373", "70380", "70394",
    # Lafourche Parish
    "70340", "70341", "70342", "70355", "70357",
    # St. Mary Parish
    "70380", "70381", "70517",
    # Iberia Parish
    "70544", "70560",
    # Cameron Parish (most exposed to Gulf)
    "70631", "70632", "70633", "70645",
    # Calcasieu / Lake Charles coast
    "70601", "70605", "70607", "70611",
]


# ---------------------------------------------------------------------------
# nj_coast_zips.yaml — NJ Coastal Barrier / Shore exposure
# ---------------------------------------------------------------------------

NJ_COAST_ZIPS: list[str] = [
    # Atlantic City / Atlantic County shore
    "08401", "08402", "08403", "08404", "08405",
    # Cape May County (southernmost shore)
    "08210", "08212", "08204", "08247", "08251", "08260",
    # Ocean County barrier islands (Long Beach Island, Toms River area)
    "08008", "08050", "08092", "08731", "08735",
    # Monmouth County shore (Asbury Park, Sea Bright, Sandy Hook)
    "07748", "07750", "07760",
]


# ---------------------------------------------------------------------------
# nc_coast_zips.yaml — NC coastal barrier / Outer Banks
# ---------------------------------------------------------------------------

NC_COAST_ZIPS: list[str] = [
    # Outer Banks (Dare County)
    "27954", "27959", "27968", "27981", "27982",
    # Brunswick / New Hanover coast
    "28403", "28405", "28422", "28428", "28462",
    # Carteret County (Crystal Coast)
    "28516", "28557", "28584",
]


# ---------------------------------------------------------------------------
# sc_coast_zips.yaml — SC wind pool territory (coastal)
# ---------------------------------------------------------------------------

SC_COAST_ZIPS: list[str] = [
    # Charleston / Charleston County
    "29401", "29403", "29405", "29407", "29412", "29414", "29418",
    # Horry County (Myrtle Beach)
    "29572", "29575", "29576", "29577", "29578",
    # Beaufort County (Hilton Head)
    "29906", "29909", "29910", "29928",
    # Georgetown County coast
    "29440", "29585",
]


# ---------------------------------------------------------------------------
# surplus_lines.yaml
# ---------------------------------------------------------------------------

SURPLUS_LINES: dict = {
    "metadata": {
        "version": "2.0.0",
        "effective_date": "2024-01-01",
        "carrier": "Example Mutual Insurance Co",
    },
    "thresholds": {
        "CA": {
            "tiv_threshold": 2_000_000,
            "eligible_sics": [7011, 7999, 8049, 4911, 5812, 6512, 1731, 5251],
        },
        "FL": {
            "tiv_threshold": 1_000_000,
            "eligible_sics": [7011, 4481, 7999, 5812, 1731, 6512, 4724, 5251],
        },
        "TX": {
            "tiv_threshold": 5_000_000,
            "eligible_sics": [1311, 1381, 4911, 7011, 5812, 1731, 1521, 4953],
        },
        "NY": {
            "tiv_threshold": 3_000_000,
            "eligible_sics": [7011, 7999, 8049, 5812, 7372, 6512, 4724, 8742],
        },
        "IL": {
            "tiv_threshold": 3_000_000,
            "eligible_sics": [7011, 5812, 6512, 7372, 4953, 8742],
        },
        "NJ": {
            "tiv_threshold": 2_000_000,
            "eligible_sics": [7011, 5812, 6512, 7999, 4724],
        },
        "MA": {
            "tiv_threshold": 1_500_000,
            "eligible_sics": [7011, 5812, 6512, 7372, 8742, 8049],
        },
        "WA": {
            "tiv_threshold": 1_500_000,
            "eligible_sics": [2411, 811, 7011, 5812, 6512, 4953],
        },
        "LA": {
            "tiv_threshold": 1_000_000,
            "eligible_sics": [1311, 1381, 7011, 5812, 4481, 6512],
        },
        "PA": {
            "tiv_threshold": 3_000_000,
            "eligible_sics": [7011, 5812, 6512, 7372, 4953],
        },
        "GA": {
            "tiv_threshold": 2_000_000,
            "eligible_sics": [7011, 5812, 6512, 4724, 4953],
        },
        "AZ": {
            "tiv_threshold": 2_000_000,
            "eligible_sics": [7011, 5812, 6512, 1731, 4953],
        },
        "CO": {
            "tiv_threshold": 2_000_000,
            "eligible_sics": [7011, 5812, 6512, 1731, 2411, 7999],
        },
    },
    "diligent_search_requirements": {
        "CA": {
            "min_declinations": 3,
            "notes": "Three admitted market declinations required before E&S placement — CA Ins Code §1765.1",
        },
        "FL": {
            "min_declinations": 3,
            "notes": "Three admitted market declinations required — FL Ins Code §626.916",
        },
        "TX": {
            "min_declinations": 2,
            "notes": "Two admitted market declinations required — TX Ins Code §981.005",
        },
        "NY": {
            "min_declinations": 3,
            "notes": "Three admitted market declinations required — NY Ins Law §2118",
        },
        "IL": {
            "min_declinations": 3,
            "notes": "Three declinations required — IL Ins Code §445.1",
        },
        "NJ": {
            "min_declinations": 3,
            "notes": "Three declinations required — NJ Rev Stat §17:22-6.42",
        },
        "MA": {
            "min_declinations": 3,
            "notes": "Diligent search required — 209 CMR 182.07",
        },
        "WA": {
            "min_declinations": 3,
            "notes": "Three declinations required — WA Rev Code §48.15.073",
        },
        "LA": {
            "min_declinations": 3,
            "notes": "Three declinations required — LA Rev Stat §22:434",
        },
        "PA": {
            "min_declinations": 3,
            "notes": "Three declinations required — PA Stat §40 P.S. §991.1604",
        },
    },
    "mock_admitted_carriers": [
        "Keystone Mutual Insurance Co",
        "Atlas Property & Casualty",
        "Meridian Commercial Casualty",
        "Summit Commercial Underwriters",
        "Coastal Re Group",
        "Pinnacle National Insurance",
        "Heritage Mutual Commercial",
        "Granite State Property & Casualty",
        "Frontier Commercial Insurance Co",
        "Pacific Rim Commercial Underwriters",
    ],
}
