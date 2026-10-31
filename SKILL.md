---
name: bompenger
description: Finner bomstasjoner, avstand og kjøretid mellom to steder i Norge med Kartverkets og Statens vegvesens åpne API-er. Bruk når noen spør hva bompengene eller kjøringen koster mellom to steder, eller hvilke bomstasjoner en rute har. Virker med web fetch alene, eller med MCP-verktøyet finn_bompenger eller filen bompenger.py når de finnes.
---

# Bompenger

Du svarer på hva det koster å kjøre mellom to steder i Norge: bomstasjoner, pris, avstand og kjøretid én vei. Du gjetter aldri priser. Alt kommer fra Kartverket og Statens vegvesen, og du viser alltid hvilke steder som ble slått opp.

## Velg fremgangsmåte

Bruk den første som er tilgjengelig:

1. **MCP-verktøyet `finn_bompenger`** er koblet til: kall det med `fra` og `til`, og gå til «Svarformat».
2. **Du kan kjøre kommandoer** og har filen `bompenger.py`: kjør `python bompenger.py "<fra>" "<til>"`, og gå til «Svarformat». Filen ligger på https://github.com/nskarv/KI-Bompenger.
3. **Du kan hente nettsider (web fetch):** følg stegene under. Begge tjenestene er åpne og trenger ingen nøkkel.

## Bruk de vanlige adressene først

Bruk alltid adressene slik de står i steg 1 og 2, uten endringer. De virker i de fleste verktøy.

Ett unntak: enkelte henteverktøy gjenbruker en side de alt har hentet, selv om spørringen etter «?» er ny. Da får du forrige svar igjen: søker du «Sandvika» og får «Tyristrand kirke», er det dette som har skjedd. Tjenesten feiler ikke. Bare da bytter du vertsnavn for neste oppslag, og ellers ingenting:

- Kartverket: `ws.geonorge.no` og `api.kartverket.no` svarer likt. Trenger du en tredje variant, skriv vertsnavnet med store bokstaver, for eksempel `WS.GEONORGE.NO`.
- Statens vegvesen: `Route/best` og `route/best` svarer likt.

Ikke endre stien på andre måter. Prosentkodede bokstaver i stien, ekstra skråstreker eller andre påfunn blir avvist av enkelte verktøy.

## Steg 1: finn koordinater hos Kartverket

Gjør dette for både fra-stedet og til-stedet.

**Tekst med tall** (gateadresse med husnummer eller postnummer, for eksempel «Storgata 1, 3510 Hønefoss») søkes som adresse:

```
https://ws.geonorge.no/adresser/v1/sok?sok=<tekst>&utkoordsys=25833&treffPerSide=1
```

Les `adresser[0]`. Koordinatene står i `representasjonspunkt`: **øst i feltet `lon`, nord i feltet `lat`** (ja, navnene er byttet om når utkoordsys er 25833). Stedet skrives som `adressetekst, postnummer poststed`.

**Tekst uten tall** (stedsnavn, for eksempel «Tyristrand kirke» eller «Sandvika») søkes som stedsnavn:

```
https://ws.geonorge.no/stedsnavn/v1/navn?sok=<tekst>&utkoordsys=25833&treffPerSide=10
```

Les listen `navn`. Kartverket sorterer ikke etter hva folk mener: «Sandvika» gir 622 treff, og en elv står før byen i Bærum. Velg derfor treffet etter `navneobjekttype` i denne rekkefølgen: By, Tettsted, Tettbebyggelse, Bygd, Grend, Kirke, Stasjon. Finnes ingen av dem, ta det første treffet. Koordinatene står i `representasjonspunkt.øst` og `representasjonspunkt.nord`. Stedet skrives som `skrivemåte (navneobjekttype, kommunenavn)`, for eksempel «Sandvika (by, Bærum)».

Null treff: ikke gjett. Be brukeren om en gateadresse med postnummer, eller et annet stedsnavn.

Svarer adressesøket `{"message":{"utm_source":["Unknown field."]}}` eller en lignende melding om et ukjent felt, har henteverktøyet ditt lagt til en sporingsparameter på adressen (ChatGPT legger til `utm_source=chatgpt.com`). Adressesøket avviser alle ukjente felt. Stedsnavnsøket og Vegvesen godtar dem, så bruk stedsnavnsøket til å finne gaten i stedet, i to oppslag:

1. Finn kommunen fra poststedet: `https://ws.geonorge.no/stedsnavn/v1/navn?sok=<poststed>&utkoordsys=25833&treffPerSide=5`, for eksempel `sok=Billingstad`. Les `kommuner[0].kommunenavn` i det første treffet som er en by, et tettsted eller en tettbebyggelse (Billingstad gir Asker).
2. Finn gaten i den kommunen: `https://ws.geonorge.no/stedsnavn/v1/navn?sok=<gatenavn>&kommunenavn=<kommune>&utkoordsys=25833&treffPerSide=5`, for eksempel `sok=Nesbruveien&kommunenavn=Asker`. Treffet har `navneobjekttype` «Adressenavn» og et `representasjonspunkt` midt på gaten. Bruk det, uten husnummer.

Si i svaret at adressesøket ikke var tilgjengelig, og at du brukte gaten uten husnummer, som kan avvike med opptil et par kilometer fra selve adressen. Tilby brukeren å åpne adressesøket selv i nettleseren og lime inn JSON-svaret hvis nøyaktig adresse er viktig. Ikke gjett koordinater, og ikke bytt til andre tjenester.

Kontroller koordinatene før du går videre. I UTM 33 er de store tall i meter: øst rundt 200 000 til 300 000 og nord rundt 6 600 000 til 6 700 000 på Østlandet, og nord alltid over 6 400 000 i Norge. Ser du tall som 59,9 og 10,5, er det grader: da manglet `utkoordsys=25833` i adressen. Hent på nytt med parameteren.

## Steg 2: finn ruten hos Statens vegvesen

```
https://www.vegvesen.no/ws/no/vegvesen/ruteplan/routingservice_v3_0/open/routingservice/api/Route/best?Stops=<øst1>,<nord1>;<øst2>,<nord2>&Format=json
```

Rekkefølgen er øst,nord for fra-stedet, semikolon, øst,nord for til-stedet. Eksempel for Tyristrand kirke til Sandvika:

```
...Route/best?Stops=227433.45,6671118.76;249716.17,6647823.44&Format=json
```

Bare komma mellom øst og nord, og bare semikolon mellom de to punktene, gir en gyldig adresse. Mellomrom, `|` eller to `Stops`-parametere gir feil 400. Avviser henteverktøyet ditt adressen på grunn av semikolonet, skriv `%3B` i stedet for `;` og `%2C` i stedet for `,`. Vegvesen godtar begge former.

Svaret er stort. Du trenger bare dette fra `routes[0]`:

- `statistic.totalLength`: meter. Del på 1000 og rund av til én desimal for kilometer.
- `statistic.totalDriveTime`: minutter, rund av til helt tall.
- Alle `bomstasjoner` under `features[].properties.roadFeatures`. De ligger spredt på flere delstrekninger. For hver stasjon: `navn` og `takstLitenBil` (pris i kroner, ofte som tekst, for eksempel "51").

Ikke bruk `statistic.tollCount` eller `statistic.tollSmall`. De stemmer ikke med stasjonene på ruten. Summer stasjonene du fant selv.

Finnes `routes[1]` uten bomstasjoner, nevn den som bomfritt alternativ med km og minutter.

Får du en feil fra Vegvesen, les meldingen i svaret. Den er JSON med `code` og `message`:

- `code` 9200 til 9209, «posisjonen er for langt unna gyldig vegnett»: et punkt ligger utenfor vegnettet. Det betyr nesten alltid at `Stops` er feil bygget, ikke at ruten mangler. Sjekk at rekkefølgen er øst,nord (ikke nord,øst), at tallene er UTM-meter og ikke grader, og at begge punktene står der med semikolon mellom. Rett opp og hent på nytt. Først når punktene er riktige og meldingen likevel kommer, finnes det ingen kjørerute (for eksempel til Svalbard). Si det da.
- Henteverktøyet ditt melder «klientfeil» eller lignende uten noen JSON-melding, selv om adressen er riktig bygget: da er det verktøyet som ikke får hentet siden, ikke Vegvesen som avviser ruten. Enkelte henteverktøy spør tjenesten med HEAD før GET, og Vegvesens ruteplanlegger svarer 405 på HEAD. Ikke prøv flere ganger, og ikke bruk andre tjenester. Gi brukeren hele adressen du bygde, be dem åpne den i nettleseren sin og lime inn svaret, og les det innlimte svaret som i steg 2. Nettleseren viser JSON-en direkte.
- Ikke noe svar i det hele tatt: si at Vegvesens ruteplanlegger ikke svarte nå, og foreslå å prøve igjen.

Når et oppslag feiler, si alltid til brukeren hvilken nettadresse du åpnet og hva svaret var. Da kan feilen rettes.

## Svarformat

Kort og konkret, på norsk, slik:

> Fra **Tyristrand kirke (kirke, Ringerike)** til **Sandvika (by, Bærum)**: 53,5 km, rundt 50 minutter én vei.
> Bomstasjoner: E16 Skaret 51 kr, E16 Avtjerna 51 kr. Til sammen 102 kr i fullpris for liten bil.
> AutoPASS gir vanligvis 20 % rabatt, og noen stasjoner tar bare betalt i én retning. Tur-retur er tallene det dobbelte, med forbehold om énveis innkreving.

Regler:

- Vis alltid stedene slik Kartverket fant dem. Ser det ut som feil sted, spør før du regner videre.
- Priser er fullpris for liten bil. Si det, og ikke regn inn rabatt uten at brukeren ber om det.
- Tallene gjelder én vei. Si det tydelig.
- Oppgi Kartverket og Statens vegvesen som kilder når det passer.

## Begrensninger

- Vegvesens åpne tjeneste er oppført med en grense på 2 500 forespørsler per dag. Ikke slå opp i løkke.
- Takstene er anslag for planlegging, ikke en faktura.
- Stedsnavnsøket kjenner ikke butikker og bedrifter («IKEA», «Sandvika Storsenter»). Be om gateadresse i slike tilfeller.
