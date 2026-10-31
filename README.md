# Bompenger: et KI-verktøy du kan kjøre selv

Finner bomstasjoner, avstand og kjøretid mellom to steder i Norge. Eksempelet fra artikkelen
[Bygg et KI-verktøy](https://nskarv.no/notater/bygg-et-ki-verktoy/) på nskarv.no, del 4 av serien om KI i praksis.

Én Python-fil, ingen pakker å installere, ingen nøkler, ingen konto. To åpne tjenester gjør jobben:

- [Kartverkets stedsnavnsøk](https://ws.geonorge.no/stedsnavn/v1/) og [adressesøk](https://ws.geonorge.no/adresser/v1/) gjør steder og adresser om til koordinater.
- [Statens vegvesens ruteplanlegger](https://www.vegvesen.no/ws/no/vegvesen/ruteplan/routingservice_v3_0/open/routingService/openapi/index.html) finner ruten og bomstasjonene.

## Kjør som kommando

Krever Python 3.10 eller nyere.

```bash
python bompenger.py "Tyristrand kirke" "Sandvika"
```

Tekst med tall («Storgata 1, 3510 Hønefoss») slås opp som adresse. Tekst uten tall slås opp som stedsnavn.
Svaret er JSON med stedene slik Kartverket fant dem, kilometer, minutter og stasjonene med pris:

```json
{
  "fra": "Tyristrand kirke (kirke, Ringerike)",
  "til": "Sandvika (by, Bærum)",
  "en_vei": {
    "km": 53.5,
    "minutter": 50,
    "bomstasjoner": [
      {"navn": "E16 Skaret", "liten_bil_kr": 51.0},
      {"navn": "E16 Avtjerna", "liten_bil_kr": 51.0}
    ],
    "bom_sum_liten_bil_kr": 102.0,
    "vegvesen_sum": {"passeringer": 3, "liten_bil_kr": 204.0}
  },
  "bomfritt_alternativ": null,
  "merknad": "Fullpris liten bil. AutoPASS gir vanligvis 20 % rabatt. Noen stasjoner tar bare betalt i én retning. Avviker vegvesen_sum fra stasjonene, ligger prisen trolig mellom de to."
}
```

`vegvesen_sum` er Vegvesens egen sum for ruten. Den teller ofte én passering mer enn stasjonene i listen, trolig en
stasjon i en bomring som ruteplanleggeren ikke lister per strekning. Vis begge tall; den sanne prisen ligger mellom dem.

## Kjør som MCP-server

Da kan en språkmodell bruke verktøyet. Ingenting mer skal installeres: filen snakker MCP selv, over stdin/stdout.

```bash
python bompenger.py --mcp
```

Programmet venter på en klient. Du starter det normalt ikke selv; klienten gjør det.

**Claude Desktop**: legg dette i `claude_desktop_config.json` (Settings → Developer → Edit Config) og start Claude Desktop på nytt.
Bruk full sti til filen.

```json
{
  "mcpServers": {
    "bompenger": {
      "command": "python",
      "args": ["/full/sti/til/bompenger.py", "--mcp"]
    }
  }
}
```

**Claude Code**:

```bash
claude mcp add bompenger -- python /full/sti/til/bompenger.py --mcp
```

**AnythingLLM**: samme oppsett i `anythingllm_mcp_servers.json` under `storage/plugins/`, med `command` og `args` som over.

Spør så: «Hva koster bompengene fra Tyristrand kirke til Sandvika?»

MCP-delen er rundt 40 linjer og dekker de fire metodene en klient bruker: `initialize`, `ping`, `tools/list` og `tools/call`.
Testet 31. oktober 2026 med den offisielle MCP-klienten (Python SDK 2.3.0).

## Bruk som skill i Claude, uten kode

`SKILL.md` er oppskriften for Claude. Den beskriver hvilke adresser som skal hentes, hvilke felt som skal leses,
hvordan stedsnavn velges og hvordan svaret skal se ut. Claude kan hente nettsider selv, så den trenger ikke programmet.

- **I en samtale:** dra `SKILL.md` inn i chatvinduet og spør: «Hva koster bompengene fra Tyristrand kirke til Sandvika?»
  Websøk må være slått på.
- **Som fast skill i Claude:** pakk mappen `bompenger/` med `SKILL.md` i en zip-fil og last den opp under
  Settings → Capabilities → Skills.
- **I Claude Code:** legg `SKILL.md` i `.claude/skills/bompenger/` i prosjektet, eller i `~/.claude/skills/bompenger/`.

Finnes MCP-verktøyet eller `bompenger.py` fra før, sier skillen at de skal brukes først.

## ChatGPT: egendefinert GPT med Actions

ChatGPTs nettleserverktøy åpner lenker du gir den, men nekter å åpne nettadresser modellen selv har satt sammen med nye verdier. Det er et sikkerhetstiltak mot lekkasje gjennom lenker, og det stopper skillen i vanlig ChatGPT-chat. Løsningen i ChatGPT er en egendefinert GPT med Actions, som kaller tjenestene direkte:

1. Åpne ChatGPT → Utforsk GPT-er → Opprett (krever Plus, Team eller Enterprise).
2. Lim inn innholdet i `SYSTEMPROMPT.md` som instruksjoner.
3. Under Actions, velg «Opprett ny action», lim inn innholdet i `actions/kartverket.yaml`, autentisering «None».
4. Opprett en action til med `actions/vegvesen.yaml`, autentisering «None».
5. Lagre, og spør: «Hva koster bompengene fra Tyristrand kirke til Sandvika?»

Actions-filene beskriver fire kall: `finnStedsnavn` og `finnAdresse` hos Kartverket, `avstandOgBomsum` (lite svar) og `bomstasjonerPaaRuten` (stort svar) hos Vegvesen. GPT-en bygger parameterne selv, så ingen nettadresser settes sammen i chatten.

## Systemprompt for en agent

`SYSTEMPROMPT.md` er en ferdig systemprompt for en agent som bare gjør dette: hva den gjør ved start, en arbeidsflyt
i fem steg (samle inn, slå opp, kontroller stedene, svar, tilby neste steg), reglene og et eksempel. Filen er bare
prompten, uten forklaring, så den kan limes rett inn.

- **Som systemprompt:** i AnythingLLM, som instruksjoner i et Claude-prosjekt eller en egendefinert GPT, eller i en
  Ollama-modell. Gi agenten verktøyet `finn_bompenger` eller skillen.
- **Som første melding i en samtale:** lim inn hele teksten. Prompten sier at modellen skal bli agenten med en gang,
  ikke vurdere teksten. Har den ingen verktøy, åpner den SKILL.md fra dette repoet selv, hvis den kan åpne nettadresser.
  Kan den ikke det, ber den om å få SKILL.md limt inn og venter.

## Modell, temperatur og effort

Disse tre velges utenfor prompten, i verktøyet som kjører modellen. En systemprompt kan ikke endre dem; den kan bare be modellen svare kort og uten å gjette.

| Innstilling | Hvor den settes | Passer for denne agenten |
| --- | --- | --- |
| Modell | Modellvelgeren i Claude eller ChatGPT; arbeidsområdets innstillinger i AnythingLLM; `FROM` i en Ollama-modellfil; `model` i et API-kall | En modell som kan kalle verktøy. Lokalt holder en modell på rundt 27B parametere, som Qwen 3.8 27B. I skyen holder den minste modellen med verktøystøtte. |
| Temperatur | Ikke tilgjengelig i Claude- eller ChatGPT-chat; arbeidsområdets innstillinger i AnythingLLM; `PARAMETER temperature` i Ollama; `temperature` i et API-kall | Lav, 0,2 til 0,6. Oppgaven er fast, og verktøykallene skal bli like hver gang. |
| Effort (tenking) | Tenkevelgeren i Claude og ChatGPT; tenkemodus i Ollama for modeller som har det; parameter for tenking i et API-kall | Lav. Agenten følger en oppskrift, og oppslagene gjør jobben. Høy effort gir bare mer tid og flere tokens. |

## Når noe går galt

Verktøyet gjetter ikke. Det sier fra, og modellen får meldingen:

| Situasjon | Melding |
| --- | --- |
| Stedet finnes ikke hos Kartverket | `Fant ikke «…» hos Kartverket. Be om gateadresse med postnummer, eller et stedsnavn.` |
| Ingen bomstasjoner på ruten | Vanlig svar med tom liste og sum 0 |
| Vegvesen finner ingen rute, for eksempel til Longyearbyen | `Statens vegvesen fant ingen kjørerute mellom adressene.` |
| Tjenesten svarer med en feilkode | `www.vegvesen.no svarte med HTTP 503 Service Unavailable` |
| Tjenesten svarer ikke innen 20 sekunder | `Fikk ikke svar fra www.vegvesen.no: …` |

Mange steder deler navn. Kartverket gir 622 treff på «Sandvika», og en elv i Aurskog-Høland står før byen i Bærum.
Verktøyet foretrekker byer og tettsteder, og svaret viser alltid hva som ble valgt (`Sandvika (by, Bærum)`),
så bruker og modell kan se at det er riktig sted. Er det ikke det, oppgi en gateadresse med postnummer.

## Vilkår

- Kartverkets stedsnavn- og adressesøk er åpne under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Oppgi Kartverket som kilde.
- Statens vegvesens ruteplanlegger er oppført på [data.norge.no](https://data.norge.no/en/datasets/087d6143-3d56-32f9-ae43-0dc992c75469/route-planning-for-cars) under NLOD 2.0, med krav om å oppgi Statens vegvesen som kilde og en grense på 2 500 forespørsler per dag. Oppføringen ber også om brukernavn og passord. Den åpne adressen (`/open/`) svarte uten innlogging da dette ble testet 31. oktober 2026. Sjekk vilkårene selv før du bruker tjenesten mye.
- Prisene er Vegvesens takster for liten bil uten rabatt. Bruk dem som anslag, ikke som faktura.
- De to stedene sendes til Kartverket og Statens vegvesen. Ingenting annet forlater maskinen din, og ingenting lagres.

Statens vegvesen ber om at bruken kan identifiseres. Bytt gjerne `USER_AGENT` i filen til ditt eget navn.

Koden er fri å bruke under [MIT-lisensen](LICENSE).
