#!/usr/bin/env python3
"""Bompenger: bomstasjoner, avstand og kjøretid mellom to steder i Norge.

Eksempelet fra «Bygg et KI-verktøy», del 4 av serien om KI i praksis på nskarv.no.
Bruker to åpne tjenester uten nøkkel: Kartverkets steds- og adressesøk og Statens
vegvesens ruteplanlegger. Krever bare Python 3.10 eller nyere, ingen pakker.

Som kommando:
    python bompenger.py "Tyristrand kirke" "Sandvika"

Som MCP-server for Claude Desktop, Claude Code, AnythingLLM og lignende:
    python bompenger.py --mcp
"""

import inspect
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

ADRESSE_URL = "https://ws.geonorge.no/adresser/v1/sok"
STEDSNAVN_URL = "https://ws.geonorge.no/stedsnavn/v1/navn"
RUTE_URL = (
    "https://www.vegvesen.no/ws/no/vegvesen/ruteplan/routingservice_v3_0"
    "/open/routingservice/api/Route/best"
)
# Vegvesen ber om at bruken kan identifiseres. Bytt gjerne til ditt eget navn.
USER_AGENT = "bompenger-eksempel (nskarv.no)"
TIDSAVBRUDD_SEK = 20
# Stedstyper som foretrekkes når et stedsnavn gir mange treff, i prioritert rekkefølge.
STEDSTYPER = {t: i for i, t in enumerate(["By", "Tettsted", "Tettbebyggelse", "Bygd", "Grend", "Kirke", "Stasjon"])}


def hent_json(url: str, params: dict) -> dict:
    """Én GET-forespørsel som returnerer JSON. Feiler med en lesbar melding."""
    req = urllib.request.Request(
        url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": USER_AGENT}
    )
    try:
        with urllib.request.urlopen(req, timeout=TIDSAVBRUDD_SEK) as svar:
            return json.load(svar)
    except urllib.error.HTTPError as feil:
        vert = urllib.parse.urlsplit(url).netloc
        raise RuntimeError(f"{vert} svarte med HTTP {feil.code} {feil.reason}") from feil
    except urllib.error.URLError as feil:
        vert = urllib.parse.urlsplit(url).netloc
        raise RuntimeError(f"Fikk ikke svar fra {vert}: {getattr(feil, 'reason', feil)}") from feil


def finn_sted(tekst: str) -> tuple[tuple[float, float], str]:
    """Slår opp et sted hos Kartverket. Gir koordinater (EPSG:25833) og navnet slik registeret skriver det.

    Tekst med tall («Storgata 1, 3510 Hønefoss») søkes som adresse. Tekst uten tall
    («Tyristrand kirke», «Sandvika») søkes som stedsnavn, og første treff brukes.
    """
    if any(tegn.isdigit() for tegn in tekst):
        data = hent_json(ADRESSE_URL, {"sok": tekst, "utkoordsys": 25833, "treffPerSide": 1})
        for a in data.get("adresser") or []:
            p = a["representasjonspunkt"]  # Kartverket legger øst i "lon" og nord i "lat" for 25833
            return (p["lon"], p["lat"]), f"{a['adressetekst']}, {a['postnummer']} {a['poststed']}"
    else:
        data = hent_json(STEDSNAVN_URL, {"sok": tekst, "utkoordsys": 25833, "treffPerSide": 10})
        treff = data.get("navn") or []
        if treff:
            # Kartverket sorterer ikke etter relevans: «Sandvika» gir en elv før byen i Bærum.
            # Derfor velges steder folk kjører til først, og svaret viser alltid hva som ble valgt.
            n = min(treff, key=lambda n: (n["navneobjekttype"] not in STEDSTYPER, STEDSTYPER.get(n["navneobjekttype"], 99)))
            p = n["representasjonspunkt"]
            kommune = ", ".join(k["kommunenavn"] for k in n.get("kommuner") or [])
            return (p["øst"], p["nord"]), f"{n['skrivemåte']} ({n['navneobjekttype'].lower()}, {kommune})"
    raise ValueError(
        f"Fant ikke «{tekst}» hos Kartverket. Be om gateadresse med postnummer, eller et stedsnavn."
    )


def _oppsummer(rute: dict) -> dict:
    stat = rute["statistic"]  # Vegvesen sender noen tall som tekst, derfor float()
    stasjoner = [
        {"navn": b.get("navn"), "liten_bil_kr": float(b.get("takstLitenBil") or 0)}
        for f in rute.get("features", [])
        for b in (f.get("properties", {}).get("roadFeatures", {}).get("bomstasjoner") or [])
    ]
    return {
        "km": round(float(stat["totalLength"]) / 1000, 1),
        "minutter": round(float(stat["totalDriveTime"])),
        "bomstasjoner": stasjoner,
        "bom_sum_liten_bil_kr": round(sum(s["liten_bil_kr"] for s in stasjoner), 2),
        # Vegvesens egen sum. Den teller ofte én passering mer enn stasjonene over, trolig en stasjon
        # i en bomring som ikke listes per strekning. Vis begge tall; den sanne prisen ligger mellom dem.
        "vegvesen_sum": {"passeringer": int(float(stat.get("tollCount") or 0)),
                         "liten_bil_kr": float(stat.get("tollSmall") or 0)},
    }


def finn_bompenger(fra: str, til: str) -> dict:
    """Bomstasjoner, avstand og kjøretid én vei mellom to steder i Norge.

    Bruk når noen spør hva bompengene eller kjøringen koster mellom to steder.
    Stedene kan være gateadresser med postnummer eller stedsnavn, for eksempel
    «Tyristrand kirke» og «Sandvika». Svaret viser hva som ble slått opp, så sjekk
    at det er riktig sted. Prisene er fullpris for liten bil. AutoPASS gir
    vanligvis 20 % rabatt, og noen stasjoner tar bare betalt i én retning.
    """
    (ax, ay), fra_adresse = finn_sted(fra)
    (bx, by), til_adresse = finn_sted(til)
    try:
        data = hent_json(RUTE_URL, {"Stops": f"{ax},{ay};{bx},{by}", "Format": "json"})
    except RuntimeError as feil:
        if "HTTP 404" in str(feil):  # slik svarer Vegvesen når veinettet ikke henger sammen
            raise RuntimeError("Statens vegvesen fant ingen kjørerute mellom adressene.") from feil
        raise
    ruter = data.get("routes") or []
    if not ruter:
        raise RuntimeError("Statens vegvesen fant ingen kjørerute mellom adressene.")
    beste = _oppsummer(ruter[0])
    bomfritt = next((r for r in map(_oppsummer, ruter[1:]) if not r["bomstasjoner"]), None)
    return {
        "fra": fra_adresse,
        "til": til_adresse,
        "en_vei": beste,
        "bomfritt_alternativ": bomfritt if beste["bomstasjoner"] else None,
        "merknad": "Fullpris liten bil. AutoPASS gir vanligvis 20 % rabatt. Noen stasjoner tar bare betalt i én retning. "
                   "Avviker vegvesen_sum fra stasjonene, ligger prisen trolig mellom de to.",
    }


VERKTOY = {
    "name": "finn_bompenger",
    "description": inspect.cleandoc(finn_bompenger.__doc__),
    "inputSchema": {
        "type": "object",
        "properties": {
            "fra": {"type": "string", "description": "Stedsnavn eller gateadresse med postnummer, for eksempel «Tyristrand kirke»"},
            "til": {"type": "string", "description": "Stedsnavn eller gateadresse med postnummer, for eksempel «Sandvika»"},
        },
        "required": ["fra", "til"],
    },
}


def svar_paa(melding: dict) -> dict | None:
    """Behandler én MCP-melding (JSON-RPC 2.0). Returnerer svaret, eller None for varsler."""
    metode, params, mid = melding.get("method"), melding.get("params") or {}, melding.get("id")
    if mid is None:  # varsel, for eksempel notifications/initialized: ingen respons
        return None
    if metode == "initialize":
        resultat = {
            "protocolVersion": params.get("protocolVersion", "2025-06-18"),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "bompenger", "version": "1.0"},
        }
    elif metode == "ping":
        resultat = {}
    elif metode == "tools/list":
        resultat = {"tools": [VERKTOY]}
    elif metode == "tools/call" and params.get("name") == VERKTOY["name"]:
        try:
            tekst = json.dumps(finn_bompenger(**(params.get("arguments") or {})), ensure_ascii=False)
            resultat = {"content": [{"type": "text", "text": tekst}], "isError": False}
        except (ValueError, RuntimeError, TypeError) as feil:
            # Meldingen går tilbake til modellen som en feil, så den kan spørre brukeren i stedet for å gjette.
            resultat = {"content": [{"type": "text", "text": str(feil)}], "isError": True}
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Ukjent metode: {metode}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": resultat}


def kjor_mcp() -> None:
    """Kjører som MCP-server over stdio: én JSON-melding per linje inn, én per linje ut.

    Klienten (Claude Desktop, Claude Code, AnythingLLM) starter programmet selv.
    Hele protokollen som trengs her er fire metoder, derfor ingen biblioteker.
    """
    for linje in sys.stdin:
        if not linje.strip():
            continue
        svar = svar_paa(json.loads(linje))
        if svar is not None:
            sys.stdout.write(json.dumps(svar, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    if sys.argv[1:] == ["--mcp"]:
        kjor_mcp()
    elif len(sys.argv) == 3:
        try:
            print(json.dumps(finn_bompenger(sys.argv[1], sys.argv[2]), ensure_ascii=False, indent=2))
        except (ValueError, RuntimeError) as feil:
            print(f"Feil: {feil}", file=sys.stderr)
            sys.exit(1)
    else:
        print(__doc__)
        sys.exit(2)
