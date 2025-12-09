# Sõidupäeviku API

Lihtne FastAPI teenus sõidupäeviku haldamiseks, mis toetab admini ja tavakasutaja rolle, sõidukite haldust ning GPS-koordinaatidega sõitude logimist.

## Funktsionaalsus
- **Autentimine**: OAuth2/JWT põhine sisselogimine. Vaikimisi luuakse käivitamisel kasutaja `admin` parooliga `admin123`.
- **Rollid**: Admin näeb kõiki sõidukeid ja sõite ning saab hallata kasutajaid/veokeid. Tavakasutaja näeb ainult endaga seotud sõidukeid ja enda sõite.
- **Sõidukid**: Admin saab luua sõidukeid, määrata odomeetri algnäidu ning siduda neid kasutajatega.
- **Sõidud**: 
  - Manuaalne lisamine koos alg- ja lõpp-odomeetri, GPS-koordinaatide ja töö/erakasutuse märkimisega.
  - Nupupõhine voog: `/trips/start` avab sõidu automaatse alguse ajaga ja vajadusel GPS-koordinaatidega; `/trips/{id}/stop` lõpetab sõidu ning salvestab lõpu odomeetri ja asukoha.
  - Algne odomeeter võetakse vaikimisi viimase lõpetatud sõidu lõpunäitust või sõiduki algseadistusest.
- **Filtrid**: Sõitude päringus saab filtreerida kliendi järgi.

## Kiirstart
1. Paigalda sõltuvused:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Käivita arendusserver:
   ```bash
   uvicorn app.main:app --reload
   ```
3. Ava Swagger UI aadressil `http://localhost:8000/docs` ja logi sisse `admin`/`admin123`.

## API ülevaade
- `POST /auth/login` – tagastab JWT access tokeni.
- `POST /users` – (admin) loob uue kasutaja.
- `POST /vehicles` – (admin) lisab sõiduki.
- `POST /vehicles/{vehicle_id}/assign` – (admin) seob sõiduki kasutajaga.
- `POST /vehicles/{vehicle_id}/odometer` – (admin) uuendab odomeetri algnäitu.
- `GET /vehicles` – tagastab kõik või kasutajaga seotud sõidukid.
- `POST /trips/manual` – lisab manuaalse sõidu.
- `POST /trips/start` / `POST /trips/{id}/stop` – alustab ja lõpetab sõidu nupuvoolus.
- `GET /trips?client=...` – loetleb sõidud, valikuline filtreerimine kliendi järgi.

### Rollipõhine ligipääs
- Admin: kõik sõidukid ja sõidud, halduspunktid kasutajatele ja sõidukitele.
- Tavakasutaja: ainult talle määratud sõidukid, ainult enda loodud sõidud.

### Andmemudelid
- **Vehicle**: nimi, klient, `odometer_start`.
- **Trip**: aeg, odomeetrid, GPS algus/lõpp, `trip_type` (business/personal), klient.

### Märkused
- Ära kasuta tootmises vaikimisi `SECRET_KEY` väärtust; uuenda see `app/auth.py` failis.
- Andmed salvestatakse SQLite faili `app.db`.
