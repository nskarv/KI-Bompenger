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

## Hvert oppslag trenger sin egen nettadresse

Henteverktøyet i en samtale kan gjenbruke en side det alt har hentet, selv om spørringen etter «?» er ny. Da får du forrige svar igjen: søker du «Sandvika» og får «Tyristrand kirke», er det dette som har skjedd. Tjenesten feiler ikke. Bruk derfor en ny variant av adressen for hvert oppslag i samtalen. Alle variantene gir samme svar fra tjenesten:

- Kartverket stedsnavn: `https://ws.geonorge.no/stedsnavn/v1/navn`, så `https://api.kartverket.no/stedsnavn/v1/navn`, så `https://ws.geonorge.no/stedsnavn/v1/n%61vn`, så `https://api.kartverket.no/stedsnavn/v1/n%61vn`. Trenger du flere, bytt ut en annen bokstav i stien med prosentkoden: `na%76n`, `%6Eavn`, `nav%6E`.
- Kartverket adresser: samme to verter, og `s%6Fk`, `%73ok`, `so%6B` i stedet for `sok` i stien.
- Statens vegvesen: bytt mellom `Route/best`, `route/best`, `Route/Best`, `ROUTE/best`, `route/BEST`, eller legg til en skråstrek: `Route/best/`.

Regel: viser svaret samme sted eller samme rute som et tidligere oppslag i samtalen, selv om du søkte på noe annet, gjenta oppslaget med neste variant. Si ikke at tjenesten feiler før en ny variant også har gitt feil svar.

## Steg 1: finn koordinater hos Kartverket

Gjør dette for både fra-stedet og til-stedet, med hver sin variant av adressen (se over): fra-stedet på ws.geonorge.no, til-stedet på api.kartverket.no.

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

## Steg 2: finn ruten hos Statens vegvesen

```
https://www.vegvesen.no/ws/no/vegvesen/ruteplan/routingservice_v3_0/open/routingservice/api/Route/best?Stops=<øst1>,<nord1>;<øst2>,<nord2>&Format=json
```

Rekkefølgen er øst,nord for fra-stedet, semikolon, øst,nord for til-stedet. Eksempel for Tyristrand kirke til Sandvika:

```
...Route/best?Stops=227433.45,6671118.76;249716.17,6647823.44&Format=json
```

Svaret er stort. Du trenger bare dette fra `routes[0]`:

- `statistic.totalLength`: meter. Del på 1000 og rund av til én desimal for kilometer.
- `statistic.totalDriveTime`: minutter, rund av til helt tall.
- Alle `bomstasjoner` under `features[].properties.roadFeatures`. De ligger spredt på flere delstrekninger. For hver stasjon: `navn` og `takstLitenBil` (pris i kroner, ofte som tekst, for eksempel "51").

Ikke bruk `statistic.tollCount` eller `statistic.tollSmall`. De stemmer ikke med stasjonene på ruten. Summer stasjonene du fant selv.

Finnes `routes[1]` uten bomstasjoner, nevn den som bomfritt alternativ med km og minutter.

Svarer Vegvesen med feil 404, finnes det ingen kjørerute mellom stedene (for eksempel til Svalbard). Si det. Svarer tjenesten ikke, si at Vegvesens ruteplanlegger ikke svarte nå, og foreslå å prøve igjen.

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
